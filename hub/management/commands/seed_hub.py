from django.core.management.base import BaseCommand
from hub.models import Application, Category

class Command(BaseCommand):
    help = "Initialise le catalogue sans créer de compte ni modifier des fiches existantes."
    def handle(self, *args, **options):
        entries = [
            ("gabomamarket", "GabomaMarket", "Commerce", "commerce", "Votre espace GabomaMarket, à retrouver en un instant.", "", "sage", "market"),
            ("zanalyze", "Zanalyze", "Analyses sportives", "analyses", "Retrouvez les analyses de matchs et suivez vos compétitions.", "https://gabomazone.pythonanywhere.com", "purple", "chart"),
            ("fallaman", "Fallaman", "Services & talents", "services", "Trouvez quelqu'un. Trouvez du travail. La mise en relation au Gabon.", "https://fallaman.gabomazone.com", "blue", "fallaman"),
            ("gabomazone-saas", "Gabomazone SaaS", "Gestion & SaaS", "saas", "Un accès direct à votre espace Gabomazone SaaS.", "", "sand", "cube"),
            ("gabomapass", "GabomaPass", "Accès & services", "acces", "Votre application GabomaPass, toujours à portée de main.", "", "forest", "pass"),
            ("gab-event", "Gab Event", "Événements", "evenements", "Créez vos invitations et gérez vos événements en toute simplicité.", "https://steevy64.pythonanywhere.com", "sand", "event"),
        ]
        added = 0
        for index, (slug, name, label, category_slug, description, url, color, icon) in enumerate(entries):
            category, _ = Category.objects.get_or_create(slug=category_slug, defaults={"name": label, "order": index})
            _, created = Application.objects.get_or_create(slug=slug, defaults={"name": name, "category": category, "description": description,
                "website_url": url, "color": color, "icon": icon, "is_admin_added": True, "status": Application.Status.PUBLISHED})
            added += int(created)
        Category.objects.get_or_create(slug="productivite", defaults={"name": "Productivité", "order": 6})
        Category.objects.get_or_create(slug="autres", defaults={"name": "Autres applications", "order": 7})
        self.stdout.write(self.style.SUCCESS(f"Catalogue prêt : {added} nouvelle(s) application(s). Aucun compte par défaut créé."))
