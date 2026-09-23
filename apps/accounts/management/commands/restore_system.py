import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection


class Command(BaseCommand):
    help = "Stellt ein SQLite-Backup nach ausdruecklicher Bestaetigung wieder her."

    def add_arguments(self, parser):
        parser.add_argument("backup", help="Backup-Verzeichnis mit manifest.json.")
        parser.add_argument("--confirm", action="store_true", help="Destruktive Wiederherstellung bestaetigen.")
        parser.add_argument("--skip-media", action="store_true", help="Medienarchiv nicht wiederherstellen.")

    def handle(self, *args, **options):
        if not options["confirm"]:
            raise CommandError("Wiederherstellung ist destruktiv. Erneut mit --confirm ausfuehren.")
        if connection.vendor != "sqlite":
            raise CommandError("Automatische Wiederherstellung ist derzeit nur fuer SQLite implementiert; fuer PostgreSQL/MySQL bitte die nativen Restore-Werkzeuge verwenden.")
        backup = Path(options["backup"]).resolve()
        manifest_path = backup / "manifest.json"
        database_backup = backup / "database.sqlite3"
        if not manifest_path.exists() or not database_backup.exists():
            raise CommandError("Backup ist unvollstaendig: manifest.json und database.sqlite3 werden benoetigt.")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        expected = manifest.get("files", {}).get("database.sqlite3", {}).get("sha256")
        actual = hashlib.sha256(database_backup.read_bytes()).hexdigest()
        if expected and expected != actual:
            raise CommandError("Pruefsumme der Datenbankkopie stimmt nicht mit dem Manifest ueberein.")

        destination = Path(connection.settings_dict["NAME"]).resolve()
        safety_copy = destination.with_name(f"{destination.name}.before-restore-{datetime.now():%Y%m%d-%H%M%S}")
        if destination.exists():
            shutil.copy2(destination, safety_copy)
        shutil.copy2(database_backup, destination)

        media_archive = backup / "media.zip"
        if media_archive.exists() and not options["skip_media"]:
            media_root = Path(settings.MEDIA_ROOT)
            safety_media = media_root.with_name(f"{media_root.name}.before-restore-{datetime.now():%Y%m%d-%H%M%S}")
            if media_root.exists():
                shutil.copytree(media_root, safety_media)
            shutil.unpack_archive(str(media_archive), str(media_root), "zip")
        self.stdout.write(self.style.SUCCESS(f"SQLite-Backup wiederhergestellt: {destination}"))
        self.stdout.write(f"Sicherheitskopie: {safety_copy if safety_copy.exists() else 'nicht vorhanden'}")
