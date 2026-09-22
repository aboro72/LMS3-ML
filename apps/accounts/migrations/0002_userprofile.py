import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0001_initial"),
        ("organisations", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="UserProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("rolle", models.CharField(choices=[("superadmin", "Super-Admin"), ("org_admin", "Org-Admin"), ("trainer", "Trainer"), ("examiner", "Pruefer"), ("learner", "Lernender")], max_length=20)),
                ("eingeladen_am", models.DateTimeField(auto_now_add=True)),
                ("aktiv", models.BooleanField(default=True)),
                ("nutzer", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="profile", to=settings.AUTH_USER_MODEL)),
                ("organisation", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="organisations.organisation")),
            ],
            options={
                "verbose_name": "Benutzerprofil",
                "verbose_name_plural": "Benutzerprofile",
            },
        ),
        migrations.AddConstraint(
            model_name="userprofile",
            constraint=models.UniqueConstraint(fields=("nutzer", "organisation", "rolle"), name="unique_user_organisation_role"),
        ),
    ]
