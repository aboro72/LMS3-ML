# Backup, Restore und Einzelsystem-Migration

Stand: 23.09.2026. PostgreSQL ist die produktive Standarddatenbank; die vorhandenen
SQLite-Befehle dienen weiterhin der lokalen Entwicklung. Ein produktiver PostgreSQL-
Dump und eine testweise Wiederherstellung auf dem Zielserver sind noch durchzuführen.

## Aktueller ML-Betriebsmodus

ML Gruppe läuft als Einzelsystem. Neue Zahlungen sind standardmäßig deaktiviert;
historische Zahlungen und Rechnungen bleiben zur Nachvollziehbarkeit erhalten.
Die Sperre gilt serverseitig auch bei direktem Aufruf der Checkout-, Zahlungs-
und Auszahlungs-URLs.

## Bestandsaufnahme

Vor einer produktiven Migration wird ausschließlich lesend ausgeführt:

```powershell
.venv\Scripts\python.exe manage.py audit_single_system --output reports\single-system-audit.json
```

Der Bericht erfasst die konfigurierte Betreiberorganisation, alle Organisationen,
Benutzer/Profile, Kurse, Lernpfade, Prüfungen, Versuche, Zertifikate, Zahlungen,
Rechnungen sowie Anzahl, Größe und SHA-256-Prüfsumme aller Medien-Dateien.

Die lokale Demo-Datenbank darf nicht als produktive Quelle behandelt werden. Bei
mehreren Organisationen muss vor dem Umzug genau eine Quellorganisation fachlich
ausgewählt werden.

## Backup

Für die lokale SQLite-Umgebung:

```powershell
.venv\Scripts\python.exe manage.py backup_system backups\before-single-system
```

Das Backup enthält `database.sqlite3` (bei SQLite), `data.json` als portablen
Django-Datenexport, `media.zip` und `manifest.json` mit Zeitstempel, Dateigrößen
und Prüfsummen.

Der `FIELD_ENCRYPTION_KEY` gehört nicht in das Backup. Er muss separat und sicher
aufbewahrt werden. Ohne denselben Schlüssel sind verschlüsselte Felder nicht
wiederherstellbar.

## Restore

Die Wiederherstellung ist absichtlich geschützt und erzeugt vor dem Ersetzen der
SQLite-Datei eine Sicherheitskopie:

```powershell
.venv\Scripts\python.exe manage.py restore_system backups\before-single-system --confirm
```

Die Medien werden ebenfalls wiederhergestellt. Mit `--skip-media` kann das
Medienarchiv ausgelassen werden. Der Restore-Befehl unterstützt bewusst nur
SQLite. Für PostgreSQL, MySQL oder MSSQL müssen die nativen Dump-/Restore-
Werkzeuge des Zielsystems verwendet und anschließend Anwendung, Medien und
`FIELD_ENCRYPTION_KEY` gemeinsam geprüft werden.

## Empfohlene produktive Reihenfolge

1. Schreibzugriffe und laufende Prüfungen im Wartungsfenster stoppen.
2. Datenbank, Medien und Verschlüsselungsschlüssel sichern.
3. Backup testweise in einer getrennten Umgebung wiederherstellen.
4. `audit_single_system` vor und nach der Migration ausführen und Berichte vergleichen.
5. Eine Quellorganisation auswählen; keine Organisationen automatisch zusammenführen.
6. Rollen, Inhalte, Fortschritte, Versuche, Zertifikate, Rechnungen und Dateien vergleichen.
7. Browser- und PDF-Smoke-Tests durchführen.
8. Erst danach den produktiven Einzelsystem-Betrieb freigeben.
