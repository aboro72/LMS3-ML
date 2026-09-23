import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from django.conf import settings
from django.core import serializers
from django.core.management import BaseCommand, CommandError, call_command
from django.db import connection


class Command(BaseCommand):
    help = "Erstellt ein Backup aus Datenexport, Datenbankkopie (SQLite) und Medienarchiv."

    def add_arguments(self, parser):
        parser.add_argument("output", help="Leeres Zielverzeichnis fuer das Backup.")

    def handle(self, *args, **options):
        target = Path(options["output"]).resolve()
        if target.exists() and any(target.iterdir()):
            raise CommandError("Das Zielverzeichnis muss leer sein.")
        target.mkdir(parents=True, exist_ok=True)
        media_root = Path(settings.MEDIA_ROOT)
        if media_root.exists():
            shutil.make_archive(str(target / "media"), "zip", root_dir=media_root)

        fixture = target / "data.json"
        with fixture.open("w", encoding="utf-8") as handle:
            call_command("dumpdata", natural_foreign=True, natural_primary=True, indent=2, stdout=handle)

        database = connection.settings_dict
        database_copy = None
        if connection.vendor == "sqlite":
            source = Path(database["NAME"])
            if source.exists():
                database_copy = target / "database.sqlite3"
                shutil.copy2(source, database_copy)

        manifest = {
            "format_version": 1,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "database_vendor": connection.vendor,
            "database_copy": database_copy.name if database_copy else None,
            "media_archive": "media.zip" if media_root.exists() else None,
            "field_encryption_key_required": True,
            "files": {},
        }
        for path in target.iterdir():
            if path.is_file():
                manifest["files"][path.name] = {
                    "bytes": path.stat().st_size,
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                }
        (target / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        self.stdout.write(self.style.SUCCESS(f"Backup erstellt: {target}"))
