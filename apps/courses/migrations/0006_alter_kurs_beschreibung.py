from django.db import migrations
import django_quill.fields


class Migration(migrations.Migration):
    dependencies = [
        ("courses", "0005_lektion_video_thumbnail"),
    ]

    operations = [
        migrations.AlterField(
            model_name="kurs",
            name="beschreibung",
            field=django_quill.fields.QuillField(blank=True),
        ),
    ]
