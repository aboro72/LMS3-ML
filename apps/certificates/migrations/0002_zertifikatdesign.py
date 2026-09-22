import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("certificates", "0001_initial"),
        ("organisations", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="ZertifikatDesign",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("primary_color", models.CharField(default="#12315f", max_length=20, verbose_name="Hauptfarbe")),
                ("secondary_color", models.CharField(default="#f28c28", max_length=20, verbose_name="Akzentfarbe")),
                (
                    "org_display_name",
                    models.CharField(
                        blank=True,
                        help_text="Leer lassen = Organisationsname wird verwendet",
                        max_length=200,
                        verbose_name="Anzeigename im Zertifikat",
                    ),
                ),
                ("footer_text", models.CharField(blank=True, max_length=500, verbose_name="Fußzeilentext")),
                ("signature_line", models.CharField(blank=True, max_length=200, verbose_name="Unterschriftenzeile")),
                ("logo", models.ImageField(blank=True, upload_to="zertifikat_logos/", verbose_name="Logo")),
                (
                    "organisation",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="zertifikat_design",
                        to="organisations.organisation",
                    ),
                ),
            ],
            options={
                "verbose_name": "Zertifikat-Design",
                "verbose_name_plural": "Zertifikat-Designs",
            },
        ),
    ]
