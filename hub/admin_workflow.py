from django.contrib import messages
from django.contrib.admin.models import LogEntry
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q, Exists, OuterRef
from django.shortcuts import get_object_or_404, redirect
from django.http import Http404
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils import timezone
from .models import Application, Payment, Category
from .payments.manual import confirm_manual_payment
from django import forms

class ManualPaymentForm(forms.Form):
    receipt = forms.CharField(label="Référence du reçu / transaction", max_length=160)
    amount = forms.IntegerField(label="Montant reçu (FCFA)", min_value=1)
    note = forms.CharField(label="Justification du contrôle", max_length=2000, widget=forms.Textarea(attrs={"rows": 3}))
    confirmed = forms.BooleanField(label="Je confirme avoir contrôlé la réception effective des fonds.")

from .payments.services import verify_payment


def workflow(self, request, object_id=None):
    if not self.has_view_permission(request):
        raise PermissionDenied
    return_params = request.GET.copy()
    return_params.pop('history_page', None)
    context = {'return_params': return_params.urlencode(), **self.admin_site.each_context(request), 'title': 'Suivi des soumissions',
               'opts': self.model._meta, 'can_edit': self.has_change_permission(request),
               'can_pay': request.user.has_perm('hub.change_payment')}
    if object_id is None:
        if request.method != 'GET':
            raise PermissionDenied
        apps = Application.objects.select_related('submitted_by', 'category').order_by('-created_at')
        stage = request.GET.get('stage', '')
        query = request.GET.get('q', '').strip()[:120]
        if query:
            apps = apps.filter(Q(name__icontains=query) | Q(submitted_by__username__icontains=query) | Q(submitted_by__email__icontains=query) | Q(payments__reference__icontains=query) | Q(payments__manual_reference__icontains=query)).distinct()
        category = request.GET.get('category', '')
        if category.isdecimal(): apps = apps.filter(category_id=category)
        ordering = request.GET.get('sort', 'newest')
        apps = apps.order_by({'newest': '-created_at', 'oldest': 'created_at', 'name': 'name'}.get(ordering, '-created_at'), 'pk')
        size = request.GET.get('size', '12')
        size = int(size) if size in ('12', '24', '48') else 12
        apps = apps.annotate(payment_ok=Exists(Payment.objects.filter(application=OuterRef('pk'), status='success', amount=OuterRef('fee_amount'), currency='XAF', verified_at__isnull=False)))
        if stage == 'pending':
            apps = apps.filter(payments__status='pending').distinct()
        elif stage in Application.Status.values:
            apps = apps.filter(status=stage)
        params = request.GET.copy()
        params.pop('page', None)
        stage_params = params.copy()
        stage_params.pop('stage', None)
        context.update(page=Paginator(apps, size).get_page(request.GET.get('page')), query=query, stage=stage,
                       params=params.urlencode(), stage_params=stage_params.urlencode(), categories=Category.objects.all(), category=category, ordering=ordering, size=size,
                       stages=[('', 'Toutes'), ('pending', 'Paiement en attente'), ('review', 'À valider'),
                               ('draft', 'À finaliser'), ('rejected', 'À corriger'), ('published', 'Publiées'), ('archived', 'Archivées')])
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
