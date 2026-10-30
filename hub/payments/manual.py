import uuid
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction, IntegrityError
from django.db.models import Q
from django.utils import timezone
from django.contrib.admin.models import LogEntry, CHANGE
from django.contrib.contenttypes.models import ContentType
from hub.models import Application, Payment


def confirm_manual_payment(app_id, actor, receipt, amount, note, confirmed):
    if not actor.has_perm('hub.change_payment'):
        raise PermissionDenied
    receipt, note = receipt.strip().upper(), note.strip()
    if not confirmed or not receipt or not note or len(receipt) > 160 or len(note) > 2000:
        raise ValidationError('Renseignez la référence, le motif et la confirmation de réception.')
    try:
        with transaction.atomic():
            app = Application.objects.select_for_update().get(pk=app_id)
            if app.is_admin_added or app.paid:
                raise ValidationError('Ce dossier est déjà réglé ou ne nécessite aucun paiement.')
            if app.status == Application.Status.ARCHIVED:
                raise ValidationError('Un dossier archivé ne peut pas être validé.')
            if amount != app.fee_amount:
                raise ValidationError(f'Le montant reçu doit correspondre aux {app.fee_amount} FCFA du dossier.')
            if Payment.objects.filter(Q(manual_reference__iexact=receipt) | Q(provider_transaction_id__iexact=receipt)).exclude(application=app).exists():
                raise ValidationError('Cette référence est déjà utilisée pour un autre dossier.')
            payment = app.payments.select_for_update().filter(status=Payment.Status.PENDING).first()
            if payment is None:
                payment = Payment(application=app, user=app.submitted_by or actor,
                                  reference='HUB-MANUAL-' + uuid.uuid4().hex.upper())
            payment.amount, payment.currency = amount, 'XAF'
            payment.status, payment.verified_at = Payment.Status.SUCCESS, timezone.now()
            payment.manual_reference, payment.manual_note = receipt, note
            payment.manual_confirmed_by = actor
            payment.verification_message = 'Réception des fonds confirmée manuellement par un administrateur.'
            payment.save()
            if app.status == Application.Status.DRAFT:
                app.status = Application.Status.REVIEW
                app.save(update_fields=['status', 'updated_at'])
            for item in (payment, app):
                LogEntry.objects.log_actions(user_id=actor.pk,
                    queryset=type(item).objects.filter(pk=item.pk), action_flag=CHANGE,
                    change_message=f'Validation manuelle : {amount} FCFA ; référence {receipt} ; {note}')
            return payment
    except IntegrityError as exc:
        raise ValidationError('Cette référence est déjà utilisée. Rechargez le dossier avant de réessayer.') from exc
