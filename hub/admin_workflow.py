from django.contrib import messages
from django.contrib.admin.models import LogEntry
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q, Exists, OuterRef, Count
from django.shortcuts import get_object_or_404, redirect
from django.http import Http404
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils import timezone
from .models import Application, Payment, Category, SubmissionNotice
from .payments.manual import confirm_manual_payment
from django import forms

class ManualPaymentForm(forms.Form):
    receipt = forms.CharField(label="Référence du reçu / transaction", max_length=160)
    amount = forms.IntegerField(label="Montant reçu (FCFA)", min_value=1)
    note = forms.CharField(label="Justification du contrôle", max_length=2000, widget=forms.Textarea(attrs={"rows": 3}))
    confirmed = forms.BooleanField(label="Je confirme avoir contrôlé la réception effective des fonds.")

from .payments.services import verify_payment

PAGE_SIZES = {"12", "24", "25", "48", "50", "100"}
DEFAULT_PAGE_SIZE = 50
BULK_LIMIT = 2000


def _submission_queryset(request):
    apps = Application.objects.select_related("submitted_by", "category").defer("description", "about", "moderation_note")
    stage = request.GET.get("stage", "")
    query = request.GET.get("q", "").strip()[:120]
    if query:
        apps = apps.filter(
            Q(name__icontains=query) | Q(submitted_by__username__icontains=query) | Q(submitted_by__email__icontains=query)
            | Q(payments__reference__icontains=query) | Q(payments__manual_reference__icontains=query)
        ).distinct()
    category = request.GET.get("category", "")
    if category.isdecimal():
        apps = apps.filter(category_id=category)
    ordering = request.GET.get("sort", "newest")
    apps = apps.order_by({"newest": "-created_at", "oldest": "created_at", "name": "name"}.get(ordering, "-created_at"), "pk")
    apps = apps.annotate(payment_ok=Exists(Payment.objects.filter(
        application=OuterRef("pk"), status="success", amount=OuterRef("fee_amount"), currency="XAF", verified_at__isnull=False, valid_until__gt=timezone.now()
    )))
    if stage == "pending":
        apps = apps.filter(payments__status="pending").distinct()
    elif stage in Application.Status.values:
        apps = apps.filter(status=stage)
    raw_size = request.GET.get("size", str(DEFAULT_PAGE_SIZE))
    size = int(raw_size) if raw_size in PAGE_SIZES else DEFAULT_PAGE_SIZE
    return apps, query, stage, category, ordering, size


def _apply_bulk(self, request, apps):
    if not self.has_change_permission(request):
        raise PermissionDenied
    action = request.POST.get("action", "")
    if action not in ("publish", "corrections", "archive"):
        self.message_user(request, "Choisissez une action à appliquer.", messages.ERROR)
        return
    if request.POST.get("select_across") == "1":
        total = apps.count()
        if total > BULK_LIMIT:
            self.message_user(request, f"Ce filtre contient {total} dossiers. Affinez-le pour en traiter au plus {BULK_LIMIT} à la fois.", messages.ERROR)
            return
        targets = Application.objects.filter(pk__in=apps.values("pk"))
    else:
        raw_ids = request.POST.getlist("selected")
        if len(raw_ids) > 200 or not raw_ids:
            self.message_user(request, "Sélectionnez les dossiers de la page, ou tout le filtre.", messages.ERROR)
            return
        ids = [int(value) for value in raw_ids if value.isdecimal() and len(value) <= 18]
        targets = Application.objects.filter(pk__in=apps.filter(pk__in=ids).values("pk"))
    if action == "archive":
        count = targets.update(status=Application.Status.ARCHIVED, reviewed_by=request.user, reviewed_at=timezone.now())
        self.message_user(request, f"{count} dossier(s) archivé(s).", messages.SUCCESS)
        return
    if action == "corrections":
        count = targets.update(
            status=Application.Status.REJECTED, reviewed_by=request.user, reviewed_at=timezone.now(),
            moderation_note="Merci de corriger votre fiche avant de la soumettre à nouveau. Contactez l'administration pour les précisions et le suivi du paiement.",
        )
        self.message_user(request, f"Corrections demandées pour {count} dossier(s).", messages.SUCCESS)
        return
    published, refused = 0, []
    for item in targets.iterator(chunk_size=200):
        try:
            with transaction.atomic():
                locked = Application.objects.select_for_update().get(pk=item.pk)
                locked.approve(request.user)
            published += 1
        except ValidationError:
            refused.append(item.name)
    self.message_user(request, f"{published} dossier(s) publié(s).", messages.SUCCESS if published else messages.WARNING)
    if refused:
        preview = ", ".join(refused[:5])
        extra = f" et {len(refused) - 5} autre(s)" if len(refused) > 5 else ""
        self.message_user(request, f"Paiement non confirmé, publication refusée : {preview}{extra}.", messages.ERROR)


def workflow(self, request, object_id=None):
    if not self.has_view_permission(request):
        raise PermissionDenied
    return_params = request.GET.copy()
    return_params.pop('history_page', None)
    context = {'return_params': return_params.urlencode(), **self.admin_site.each_context(request), 'title': 'Suivi des soumissions',
               'opts': self.model._meta, 'can_edit': self.has_change_permission(request),
               'can_pay': request.user.has_perm('hub.change_payment')}
    if object_id is None:
        apps, query, stage, category, ordering, size = _submission_queryset(request)
        if request.method == 'POST':
            _apply_bulk(self, request, apps)
            return redirect(request.get_full_path())
        if request.method != 'GET':
            raise PermissionDenied
        counts = Application.objects.aggregate(
            all=Count('pk'),
            pending=Count('pk', filter=Q(payments__status='pending'), distinct=True),
            review=Count('pk', filter=Q(status='review')),
            draft=Count('pk', filter=Q(status='draft')),
            rejected=Count('pk', filter=Q(status='rejected')),
            published=Count('pk', filter=Q(status='published')),
            archived=Count('pk', filter=Q(status='archived')),
        )
        params = request.GET.copy()
        params.pop('page', None)
        stage_params = params.copy()
        stage_params.pop('stage', None)
        context.update(page=Paginator(apps, size).get_page(request.GET.get('page')), query=query, stage=stage, counts=counts,
                       params=params.urlencode(), stage_params=stage_params.urlencode(), categories=Category.objects.all(), category=category, ordering=ordering, size=size,
                       stages=[('', 'Toutes', counts['all']), ('pending', 'Paiement en attente', counts['pending']), ('review', 'À valider', counts['review']),
                               ('draft', 'À finaliser', counts['draft']), ('rejected', 'À corriger', counts['rejected']), ('published', 'Publiées', counts['published']), ('archived', 'Archivées', counts['archived'])])
        return TemplateResponse(request, 'admin/hub/workflow.html', context)
    app = get_object_or_404(Application.objects.select_related('submitted_by', 'category', 'reviewed_by'), pk=object_id)
    if not self.has_view_permission(request, app):
        raise PermissionDenied
    manual_form = ManualPaymentForm(initial={'amount': app.fee_amount})
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'manual':
            if not context['can_pay']:
                raise PermissionDenied
            manual_form = ManualPaymentForm(request.POST)
            if manual_form.is_valid():
                try:
                    confirm_manual_payment(app.pk, request.user, **manual_form.cleaned_data)
                    self.message_user(request, 'Paiement validé manuellement. Le dossier peut maintenant être publié.', messages.SUCCESS)
                    return redirect(reverse('admin:hub_application_workflow_detail', args=[app.pk]) + ('?' + return_params.urlencode() if return_params else ''))
                except ValidationError as error:
                    manual_form.add_error(None, error)
        elif action == 'verify':
            if not context['can_pay']:
                raise PermissionDenied
            payment_id = request.POST.get('payment_id', '')
            if not payment_id.isdecimal() or len(payment_id) > 18:
                raise Http404
            payment = get_object_or_404(Payment, pk=payment_id, application=app)
            result = verify_payment(payment)
            payment.refresh_from_db()
            payment_admin = self.admin_site._registry[Payment]
            payment_admin.log_change(request, payment, 'Vérification administrative : ' + result)
            self.log_change(request, app, 'Paiement ' + payment.reference + ' : ' + result)
            self.message_user(request, result, messages.SUCCESS if payment.status == Payment.Status.SUCCESS else messages.WARNING)
        elif action in ('publish', 'corrections', 'archive'):
            if not self.has_change_permission(request, app):
                raise PermissionDenied
            note = request.POST.get('note', '').strip()
            try:
                with transaction.atomic():
                    app = Application.objects.select_for_update().get(pk=app.pk)
                    if action == 'publish':
                        if app.status not in (Application.Status.REVIEW, Application.Status.REJECTED, Application.Status.DRAFT):
                            raise ValidationError('Ce dossier ne peut plus être publié depuis cette étape.')
                        app.approve(request.user)
                        message = 'Application validée et publiée.'
                    else:
                        if not note or len(note) > 2000:
                            raise ValidationError('Précisez un motif de 1 à 2 000 caractères pour le créateur.')
                        app.status = Application.Status.REJECTED if action == 'corrections' else Application.Status.ARCHIVED
                        app.moderation_note = note
                        app.reviewed_by, app.reviewed_at = request.user, timezone.now()
                        app.save(update_fields=['status', 'moderation_note', 'reviewed_by', 'reviewed_at', 'updated_at'])
                        message = ('Corrections demandées. ' if action == 'corrections' else 'Application archivée. ') + note
                    self.log_change(request, app, message)
                self.message_user(request, message, messages.SUCCESS)
            except ValidationError as error:
                self.message_user(request, ' '.join(error.messages), messages.ERROR)
        else:
            self.message_user(request, 'Action inconnue.', messages.ERROR)
        if action != 'manual':
            return redirect(reverse('admin:hub_application_workflow_detail', args=[app.pk]) + ('?' + return_params.urlencode() if return_params else ''))
    history = LogEntry.objects.filter(content_type=ContentType.objects.get_for_model(Application), object_id=str(app.pk)).select_related('user').order_by('-action_time', '-pk')
    history = Paginator(history, 20).get_page(request.GET.get('history_page'))
    context.update(app=app, payments=app.payments.all() if request.user.has_perm('hub.view_payment') or context['can_pay'] else None,
                   history=history, paid=app.can_publish, manual_form=manual_form)
    return TemplateResponse(request, 'admin/hub/workflow_detail.html', context)


def publication_notices(modeladmin, request):
    if not request.user.has_perm('hub.view_application'):
        raise PermissionDenied
    if request.method == 'POST':
        if not request.user.has_perm('hub.change_application'):
            raise PermissionDenied
        updated = SubmissionNotice.objects.filter(seen_at__isnull=True).update(seen_at=timezone.now())
        messages.success(request, 'Notifications marquées comme lues.' if updated else 'Aucune notification en attente.')
        return redirect('admin:hub_application_notices')
    rows = list(SubmissionNotice.objects.select_related('application', 'application__category', 'application__submitted_by').order_by('-created_at')[:80])
    paid_at = {}
    payments = Payment.objects.filter(
        application_id__in=[row.application_id for row in rows],
        status=Payment.Status.SUCCESS,
        verified_at__isnull=False,
    ).order_by('-verified_at')
    for payment in payments:
        paid_at.setdefault(payment.application_id, payment)
    for row in rows:
        row.payment = paid_at.get(row.application_id)
    context = {
        **modeladmin.admin_site.each_context(request),
        'title': 'Nouvelles publications',
        'notices': rows,
        'unread': SubmissionNotice.objects.filter(seen_at__isnull=True).count(),
    }
    return TemplateResponse(request, 'admin/hub/notices.html', context)
