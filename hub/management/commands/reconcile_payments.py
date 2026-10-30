from django.core.management.base import BaseCommand
from hub.models import Payment
from hub.payments.services import verify_payment

class Command(BaseCommand):
    help = "Revérifie les paiements en attente auprès de SingPay, sans créer de nouveau débit."
    def add_arguments(self, parser): parser.add_argument("--limit", type=int, default=30)
    def handle(self, *args, **options):
        for payment in Payment.objects.filter(status=Payment.Status.PENDING).order_by("created_at")[:max(0, min(options["limit"], 500))]:
            self.stdout.write(f"{payment.reference} : {verify_payment(payment)}")
