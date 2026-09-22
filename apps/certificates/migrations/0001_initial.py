import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("courses", "0003_begleitmaterial_uebungsfrage_uebungsantwort"),
        ("exams", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Zertifikat",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("ausgestellt_am", models.DateTimeField(auto_now_add=True)),
                ("ist_widerrufen", models.BooleanField(default=False)),
                (
                    "nutzer",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="zertifikate",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "pruefungsversuch",
                    models.OneToOneField(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="zertifikat",
                        to="exams.pruefungsversuch",
                    ),
                ),
                (
                    "einschreibung",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="zertifikate",
                        to="courses.einschreibung",
                    ),
                ),
            ],
            options={
                "verbose_name": "Zertifikat",
                "verbose_name_plural": "Zertifikate",
                "ordering": ["-ausgestellt_am"],
            },
        ),
    ]
