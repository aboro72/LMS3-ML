import apps.organisations.models
import uuid
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Organisation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=200)),
                ("slug", models.SlugField(unique=True)),
                ("logo", models.ImageField(blank=True, upload_to="logos/")),
                ("kontakt_email", models.EmailField(max_length=254)),
                ("website", models.URLField(blank=True)),
                ("lizenz_typ", models.CharField(choices=[("basic", "Basic"), ("pro", "Pro"), ("enterprise", "Enterprise")], default="basic", max_length=20)),
                ("max_nutzer", models.PositiveIntegerField(default=50)),
                ("max_kurse", models.PositiveIntegerField(default=10)),
                ("aktiv", models.BooleanField(default=True)),
                ("erstellt_am", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "verbose_name": "Organisation",
                "verbose_name_plural": "Organisationen",
                "ordering": ["name"],
            },
        ),
        migrations.CreateModel(
            name="Einladung",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("email", models.EmailField(max_length=254)),
                ("rolle", models.CharField(choices=[("superadmin", "Super-Admin"), ("org_admin", "Org-Admin"), ("trainer", "Trainer"), ("examiner", "Pruefer"), ("learner", "Lernender")], max_length=20)),
                ("token", models.UUIDField(default=uuid.uuid4, unique=True)),
                ("erstellt_am", models.DateTimeField(auto_now_add=True)),
                ("akzeptiert_am", models.DateTimeField(blank=True, null=True)),
                ("abgelaufen_am", models.DateTimeField(default=apps.organisations.models.default_invitation_expiry)),
                ("eingeladen_von", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ("organisation", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="organisations.organisation")),
            ],
            options={
                "verbose_name": "Einladung",
                "verbose_name_plural": "Einladungen",
                "ordering": ["-erstellt_am"],
            },
        ),
    ]
