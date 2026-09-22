from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("courses", "0006_alter_kurs_beschreibung"),
    ]

    operations = [
        migrations.AddField(
            model_name="kurs",
            name="angebotstyp",
            field=models.CharField(
                choices=[("KURS", "Kompletter Kurs"), ("ZERTIFIKAT", "Reine Zertifikatsprüfung")],
                default="KURS",
                max_length=12,
            ),
        ),
    ]
