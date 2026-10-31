from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("hub", "0010_directory_filters_and_site_settings"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="application",
            index=models.Index(fields=["status", "created_at"], name="hub_app_status_created"),
        ),
    ]
