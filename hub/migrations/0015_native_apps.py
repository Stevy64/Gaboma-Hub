from django.db import migrations, models
import hub.images


class Migration(migrations.Migration):

    dependencies = [
        ("hub", "0014_submission_notice"),
    ]

    operations = [
        migrations.AddField(
            model_name="hubappearance",
            name="android_app",
            field=models.FileField(blank=True, help_text="Fichier .apk, 80 Mo maximum. Proposé sur les téléphones Android. Sans fichier, le Hub s'installe comme application web.", upload_to=hub.images.native_package_path, verbose_name="application Android"),
        ),
        migrations.AddField(
            model_name="hubappearance",
            name="ios_app",
            field=models.FileField(blank=True, help_text="Fichier .ipa, 80 Mo maximum. Proposé sur iPhone. Sans fichier, le Hub explique l'ajout à l'écran d'accueil.", upload_to=hub.images.native_package_path, verbose_name="application Apple"),
        ),
    ]
