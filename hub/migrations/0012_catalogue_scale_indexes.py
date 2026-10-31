from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("hub", "0011_application_status_created_index"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="application",
            index=models.Index(fields=["status", "category", "created_at"], name="hub_app_status_cat_created"),
        ),
        migrations.AddIndex(
            model_name="review",
            index=models.Index(fields=["application", "is_visible"], name="hub_review_app_visible"),
        ),
    ]
