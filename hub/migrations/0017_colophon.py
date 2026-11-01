from django.db import migrations, models


def refresh_colophon(apps, schema_editor):
    Appearance = apps.get_model("hub", "HubAppearance")
    Appearance.objects.filter(footer_colophon="Des idées locales. Des horizons ouverts.").update(
        footer_colophon="Des idées locales. Par des talents locaux."
    )


class Migration(migrations.Migration):

    dependencies = [
        ("hub", "0016_base_price_and_slogan"),
    ]

    operations = [
        migrations.AlterField(
            model_name="hubappearance",
            name="footer_colophon",
            field=models.CharField(blank=True, default="Des idées locales. Par des talents locaux.", max_length=160, verbose_name="signature du pied de page"),
        ),
        migrations.RunPython(refresh_colophon, migrations.RunPython.noop),
    ]
