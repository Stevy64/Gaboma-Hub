import hub.images
from datetime import timedelta

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import migrations, models


def grant_one_year(apps, schema_editor):
    Payment = apps.get_model("hub", "Payment")
    for payment in Payment.objects.filter(status="success", verified_at__isnull=False, valid_until__isnull=True).iterator():
        payment.valid_until = payment.verified_at + timedelta(days=365)
        payment.save(update_fields=["valid_until"])


class Migration(migrations.Migration):

    dependencies = [
        ("hub", "0012_catalogue_scale_indexes"),
    ]

    operations = [
        migrations.AddField(
            model_name="hubappearance",
            name="logo",
            field=models.ImageField(blank=True, upload_to=hub.images.editorial_image_path, verbose_name="logo du Hub"),
        ),
        migrations.AlterField(
            model_name="hubappearance",
            name="submission_fee",
            field=models.PositiveIntegerField(default=2500, help_text="Montant d'une année de référencement. Il s'applique aux nouvelles souscriptions et aux renouvellements. Un paiement déjà confirmé reste valable un an, pour le montant encaissé.", validators=[MinValueValidator(1), MaxValueValidator(1000000)], verbose_name="abonnement annuel (FCFA)"),
        ),
        migrations.AddField(
            model_name="payment",
            name="valid_until",
            field=models.DateTimeField(blank=True, null=True, verbose_name="valable jusqu'au"),
        ),
        migrations.RunPython(grant_one_year, migrations.RunPython.noop),
        migrations.CreateModel(
            name="HeroSlide",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("image", models.ImageField(upload_to=hub.images.editorial_image_path, verbose_name="image")),
                ("alt", models.CharField(blank=True, max_length=120, verbose_name="légende")),
                ("order", models.PositiveSmallIntegerField(default=0, verbose_name="ordre")),
                ("is_active", models.BooleanField(default=True, verbose_name="affichée dans le carrousel")),
                ("appearance", models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="slides", to="hub.hubappearance", verbose_name="paramètres")),
            ],
            options={
                "verbose_name": "image du hero",
                "verbose_name_plural": "images du hero",
                "ordering": ["order", "pk"],
            },
        ),
    ]
