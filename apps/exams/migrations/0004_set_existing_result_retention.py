from datetime import timedelta

from django.db import migrations


def set_existing_result_retention(apps, schema_editor):
    PruefungsVersuch = apps.get_model("exams", "PruefungsVersuch")
    for versuch in PruefungsVersuch.objects.filter(einsehbar_bis__isnull=True).exclude(status="LAUFEND"):
        reference = versuch.abgeschlossen_am or versuch.gestartet_am
        versuch.einsehbar_bis = reference + timedelta(days=365)
        versuch.save(update_fields=["einsehbar_bis"])


class Migration(migrations.Migration):
    dependencies = [("exams", "0003_pruefungsversuch_einsehbar_bis_and_more")]

    operations = [migrations.RunPython(set_existing_result_retention, migrations.RunPython.noop)]
