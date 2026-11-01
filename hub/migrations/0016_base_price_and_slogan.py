from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import migrations, models


def refresh_base_price_and_slogan(apps, schema_editor):
    Appearance = apps.get_model("hub", "HubAppearance")
    Appearance.objects.filter(territory_line="Pensé au Gabon. Pour les Gabonais.").update(territory_line="Vos applications 100% Gaboma")
    Appearance.objects.filter(submission_fee__in=[2000, 2500]).update(submission_fee=5000)


class Migration(migrations.Migration):

    dependencies = [
        ("hub", "0015_native_apps"),
    ]

    operations = [
        migrations.AlterField(
            model_name="hubappearance",
            name="submission_fee",
            field=models.PositiveIntegerField(default=5000, help_text="Montant d'une année de référencement. Il s'applique aux nouvelles souscriptions et aux renouvellements. Un paiement déjà confirmé reste valable un an, pour le montant encaissé.", validators=[MinValueValidator(1), MaxValueValidator(1000000)], verbose_name="abonnement annuel (FCFA)"),
        ),
        migrations.AlterField(
            model_name="hubappearance",
            name="territory_line",
            field=models.CharField(blank=True, default="Vos applications 100% Gaboma", max_length=120, verbose_name="bandeau local"),
        ),
        migrations.RunPython(refresh_base_price_and_slogan, migrations.RunPython.noop),
    ]
