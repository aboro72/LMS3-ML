import hashlib
import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection

from apps.accounts.models import User, UserProfile
from apps.certificates.models import Zertifikat
from apps.courses.models import Einschreibung, Kurs, Lernpfad
from apps.exams.models import PruefungsVersuch, Pruefung
from apps.organisations.models import Einladung, Organisation
from apps.payments.models import Rechnung, Zahlung


class Command(BaseCommand):
    help = "Erstellt eine nicht veraendernde Bestandsaufnahme fuer den Einzelsystem-Wechsel."

    def add_arguments(self, parser):
        parser.add_argument("--output", help="Optionaler Pfad fuer einen JSON-Bericht.")

    def handle(self, *args, **options):
        configured = Organisation.objects.filter(
            slug=getattr(settings, "SINGLE_SYSTEM_ORGANISATION_SLUG", "ml-gruppe")
        ).first()
        models = {
            "organisations": Organisation,
            "users": User,
            "profiles": UserProfile,
            "invitations": Einladung,
            "courses": Kurs,
            "enrolments": Einschreibung,
            "learning_paths": Lernpfad,
            "exams": Pruefung,
            "exam_attempts": PruefungsVersuch,
            "certificates": Zertifikat,
            "payments": Zahlung,
            "invoices": Rechnung,
        }
        counts = {name: model.objects.count() for name, model in models.items()}
        orgs = list(Organisation.objects.values("id", "slug", "name", "aktiv", "ist_demo_organisation"))
        media_root = Path(settings.MEDIA_ROOT)
        media_files = []
        media_bytes = 0
        if media_root.exists():
            for path in sorted(p for p in media_root.rglob("*") if p.is_file()):
                digest = hashlib.sha256(path.read_bytes()).hexdigest()
                size = path.stat().st_size
                media_bytes += size
                media_files.append({"path": str(path.relative_to(media_root)), "bytes": size, "sha256": digest})

        report = {
            "format_version": 1,
            "single_system_mode": bool(getattr(settings, "SINGLE_SYSTEM_MODE", False)),
            "configured_organisation": (
                {"id": configured.pk, "slug": configured.slug, "name": configured.name}
                if configured else None
            ),
            "database_engine": connection.settings_dict.get("ENGINE", ""),
            "counts": counts,
            "organisations": orgs,
            "media": {"root": str(media_root), "file_count": len(media_files), "bytes": media_bytes, "files": media_files},
            "warnings": [
                "Zahlungen/Rechnungen bleiben als historische Daten erhalten; neue Zahlungen sind fuer ML deaktiviert.",
                "Eine Produktionsmigration benoetigt vorab ein getestetes Backup und eine ausgewaehlte Quellorganisation.",
            ],
        }
        payload = json.dumps(report, ensure_ascii=False, indent=2)
        output = options.get("output")
        if output:
            try:
                Path(output).write_text(payload + "\n", encoding="utf-8")
            except OSError as exc:
                raise CommandError(f"Bericht konnte nicht geschrieben werden: {exc}") from exc
        self.stdout.write(payload)
