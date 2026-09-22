from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("exams", "0004_set_existing_result_retention")]

    operations = [
        migrations.CreateModel(
            name="PruefungsAnmeldung",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("angemeldet_am", models.DateTimeField(auto_now_add=True)),
                ("nutzer", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="pruefungsanmeldungen", to=settings.AUTH_USER_MODEL)),
                ("pruefung", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="anmeldungen", to="exams.pruefung")),
            ],
            options={"ordering": ["-angemeldet_am"], "verbose_name": "Prüfungsanmeldung", "verbose_name_plural": "Prüfungsanmeldungen"},
        ),
        migrations.AddConstraint(model_name="pruefungsanmeldung", constraint=models.UniqueConstraint(fields=("nutzer", "pruefung"), name="unique_user_exam_registration")),
    ]
