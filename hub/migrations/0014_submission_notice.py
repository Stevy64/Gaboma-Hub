import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("hub", "0013_annual_subscription_and_hero_slides"),
    ]

    operations = [
        migrations.CreateModel(
            name="SubmissionNotice",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="confirmée le")),
                ("seen_at", models.DateTimeField(blank=True, null=True, verbose_name="lue le")),
                ("application", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="notices", to="hub.application", verbose_name="application")),
            ],
            options={
                "verbose_name": "notification de publication",
                "verbose_name_plural": "notifications de publication",
                "ordering": ["-created_at"],
                "indexes": [models.Index(fields=["seen_at", "created_at"], name="hub_notice_seen_created")],
            },
        ),
    ]
