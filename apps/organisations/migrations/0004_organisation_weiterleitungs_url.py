from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("organisations", "0003_alter_organisationemailkonfiguration_smtp_password"),
    ]

    operations = [
        migrations.AddField(
            model_name="organisation",
            name="weiterleitungs_url",
            field=models.URLField(blank=True, help_text="Optionale externe oder alte URL, die auf die Mandanten-Startseite weiterleitet.", verbose_name="Weiterleitungs-URL"),
        ),
    ]
