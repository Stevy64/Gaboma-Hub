"""Abonnement annuel par soumission, confirmé auprès de Paiement Mobile uniquement."""
import uuid
from decimal import Decimal, InvalidOperation
from urllib.parse import urlsplit
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.urls import reverse
from django.utils import timezone
from hub.models import Application, HubAppearance, Payment, covering_payments
from .singpay import singpay_service, SUCCESS_STATUSES, FAILURE_STATUSES

class PaymentUnavailable(Exception):
    pass

def checkout_url_is_safe(url):
    try:
        parsed = urlsplit(url)
        return parsed.scheme == "https" and parsed.hostname in settings.SINGPAY_CHECKOUT_HOSTS and not parsed.username and not parsed.password
    except (ValueError, TypeError):
        return False

def start_checkout(application, user):
    if application.submitted_by_id != user.pk or application.is_admin_added:
        raise ValidationError("Cette soumission ne vous appartient pas.")
    if not singpay_service.is_configured:
        raise PaymentUnavailable("Paiement Mobile n'est pas encore configuré. Votre fiche est conservée ; aucun paiement n'a été effectué.")
    with transaction.atomic():
        app = Application.objects.select_for_update().get(pk=application.pk)
        paid = covering_payments(app.pk, app.fee_amount).first()
        if paid: return paid
        current = app.payments.filter(status=Payment.Status.PENDING).first()
        if current: return current
        if app.status == Application.Status.ARCHIVED:
            raise ValidationError("Un dossier archivé ne peut pas être renouvelé.")
        expired = app.payments.filter(status=Payment.Status.SUCCESS).exists()
        if not expired and app.status not in [Application.Status.DRAFT, Application.Status.REJECTED]:
            raise ValidationError("Cette fiche ne peut pas faire l'objet d'un nouveau paiement.")
        if expired:
            price = HubAppearance.current().submission_fee
            if app.fee_amount != price:
                app.fee_amount = price
                app.save(update_fields=["fee_amount", "updated_at"])
        payment = Payment.objects.create(application=app, user=user, amount=app.fee_amount,
            currency="XAF", reference=f"HUB-{uuid.uuid4().hex.upper()}")
    path = reverse("hub:payment-return", kwargs={"public_id": payment.public_id})
    try:
        ok, data = singpay_service.init_payment(amount=payment.amount, order_id=payment.reference,
            return_url=f"{settings.PUBLIC_BASE_URL}{path}")
    except Exception:
        # Un timeout peut cacher une initialisation réussie : ne pas débiter une seconde fois.
        ok, data = False, {}
    url = data.get("payment_url", "") if isinstance(data, dict) else ""
    if not ok or not checkout_url_is_safe(url):
        Payment.objects.filter(pk=payment.pk).update(verification_message="Initialisation incertaine. Vérifier auprès de Paiement Mobile avant toute nouvelle tentative.")
        payment.refresh_from_db()
        return payment
    provider_id = str(data.get("transaction_id") or "").strip() or None
    try:
        with transaction.atomic():
            locked = Payment.objects.select_for_update().get(pk=payment.pk)
            locked.checkout_url = url
            if not locked.provider_transaction_id: locked.provider_transaction_id = provider_id
            locked.save(update_fields=["checkout_url", "provider_transaction_id", "updated_at"])
    except IntegrityError:
        Payment.objects.filter(pk=payment.pk).update(verification_message="Identifiant prestataire déjà utilisé. Vérification administrative requise.")
    payment.refresh_from_db()
    return payment

def exact_amount(raw):
    if raw is None or isinstance(raw, bool): return None
    try:
        value = Decimal(str(raw))
        if not value.is_finite() or value != value.to_integral_value(): return None
        return int(value)
    except (InvalidOperation, ValueError, TypeError, OverflowError):
        return None

def normalize_reference(value):
    value = str(value or "").strip()
    return value[4:] if value.startswith("REF-") else value

def _message(payment, message):
    Payment.objects.filter(pk=payment.pk).update(verification_message=message[:240])
    return message

def verify_payment(payment):
    if payment.status == Payment.Status.SUCCESS: return "Paiement déjà confirmé."
    if not singpay_service.is_configured:
        return _message(payment, "Service Paiement Mobile non configuré ; aucune confirmation effectuée.")
    # Ne jamais accepter l'identifiant fourni dans l'URL du navigateur comme preuve de paiement.
    try:
        ok, remote = singpay_service.find_payment_by_reference(payment.reference)
        if not ok and payment.provider_transaction_id:
            ok, remote = singpay_service.verify_payment(payment.provider_transaction_id)
    except Exception:
        ok, remote = False, {}
    if not ok or not isinstance(remote, dict):
        return _message(payment, "Confirmation indisponible. Réessayez la vérification plus tard.")
    if normalize_reference(remote.get("order_id")) != payment.reference:
        return _message(payment, "Référence Paiement Mobile absente ou différente : paiement non validé.")
    raw = remote.get("raw", {})
    currency = (raw.get("currency") or raw.get("devise")) if isinstance(raw, dict) else None
    if currency and str(currency).upper() != "XAF":
        return _message(payment, "Devise différente de XAF : paiement non validé.")
    wallet = (raw.get("portefeuille") or raw.get("wallet")) if isinstance(raw, dict) else None
    if isinstance(wallet, dict): wallet = wallet.get("id") or wallet.get("_id")
    if wallet and str(wallet) != settings.SINGPAY_MERCHANT_ID:
        return _message(payment, "Portefeuille Paiement Mobile différent : paiement non validé.")
    status = str(remote.get("status") or "").lower()
    if status in SUCCESS_STATUSES:
        if exact_amount(remote.get("amount")) != payment.amount:
            return _message(payment, f"Montant absent ou différent des {payment.amount} FCFA attendus : paiement non validé.")
        provider_id = str(remote.get("transaction_id") or payment.provider_transaction_id or "").strip()
        if not provider_id: return _message(payment, "Identifiant Paiement Mobile manquant : paiement non validé.")
        if payment.provider_transaction_id and payment.provider_transaction_id != provider_id:
            return _message(payment, "Identifiant Paiement Mobile différent : paiement non validé.")
        try:
            with transaction.atomic():
                locked = Payment.objects.select_for_update().get(pk=payment.pk)
                if locked.status == Payment.Status.SUCCESS: return "Paiement déjà confirmé."
                locked.status = Payment.Status.SUCCESS
                locked.provider_transaction_id = provider_id
                locked.verified_at = timezone.now()
                locked.verification_message = "Montant et référence confirmés directement auprès de Paiement Mobile."
                locked.save(update_fields=["status", "provider_transaction_id", "verified_at", "verification_message", "updated_at"])
        except IntegrityError:
            return _message(payment, "Identifiant prestataire déjà lié à un autre paiement : vérification administrative requise.")
        payment.refresh_from_db()
        return "Paiement confirmé. Relisez votre fiche puis confirmez-la pour la publier."
    if status in FAILURE_STATUSES:
        Payment.objects.filter(pk=payment.pk).exclude(status=Payment.Status.SUCCESS).update(
            status=Payment.Status.CANCELLED if status in {"cancelled", "canceled"} else Payment.Status.FAILED,
            verification_message="Échec ou annulation confirmé auprès de Paiement Mobile.")
        payment.refresh_from_db()
        return "Paiement Mobile indique que ce paiement n'a pas abouti."
    return _message(payment, "Paiement encore en cours chez Paiement Mobile.")
