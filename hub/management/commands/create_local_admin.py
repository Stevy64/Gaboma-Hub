from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

class Command(BaseCommand):
    help = "Crée le compte de démonstration admin uniquement en développement."
    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("Compte de démonstration interdit en production.")
        user, _ = get_user_model().objects.get_or_create(username='admin')
        user.set_password('admin')
        user.is_active = user.is_staff = user.is_superuser = True
        user.save()
        self.stdout.write('Compte administrateur local prêt.')
