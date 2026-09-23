# ABoroLMS installieren

Stand: 23.09.2026. Referenz für den ML-Betrieb: Django 6.1.1, Python 3.12–3.14,
PostgreSQL, Nginx/ISPConfig, Gunicorn, Redis und Celery. Zahlungen sind im
ML-Einzelsystem deaktiviert.

Die Installation besteht aus einem System-Bootstrap und einem einmaligen Web-Assistenten. Der Web-Assistent wird nicht öffentlich unter `/install/` aktiviert, sondern nur unter einer zufälligen Token-URL, die das Bootstrap-Skript ausgibt. Nach erfolgreicher Einrichtung wird der Assistent automatisch deaktiviert.

## Ubuntu / Debian

Interaktiv:

```bash
sudo bash deploy/install-linux.sh \
  --repo https://example.invalid/aborolms.git \
  --domain lms.example.de
```

Unbeaufsichtigt mit lokalem PostgreSQL, Nginx, Redis und Celery:

```bash
sudo bash deploy/install-linux.sh \
  --repo https://github.com/aboro72/LMS3-ML.git \
  --domain lms-3.ml-projekt.de \
  --db-pass 'quaSeu2i' \
  --unattended
```

Der lokale Postfix-Mailserver ist optional:

```bash
sudo bash deploy/install-linux.sh --with-postfix ...
```

Danach die ausgegebene URL `/install/<token>/` einmalig im Browser öffnen. Der Assistent richtet die PostgreSQL-Verbindung, den Admin, SMTP und die Systemparameter ein. Für öffentliche Domains sollte HTTPS vor dem ersten produktiven Betrieb aktiviert werden.

Nach der Installation sollten `/dashboard/`, `/startseite/pagebuilder/`,
`/static/css/aborolms.css` und `/admin/` mit einem Superadmin geprüft werden.

### Testnutzer für die Abnahme anlegen

Der Befehl legt nur Testkonten und Rollenprofile für das ML-Einzelsystem an.
Er erzeugt keine Kurse, Prüfungen, Demo-Zahlungen oder Demo-Inhalte:

```bash
cd /opt/aborolms
sudo -u aborolms env DJANGO_SETTINGS_MODULE=config.settings.production \
  .venv/bin/python manage.py create_test_users \
  --password 'TEMPORAERES-ABNAHME-PASSWORT'
```

Angelegt bzw. aktualisiert werden:

| Benutzername | Rolle |
| --- | --- |
| `superadmin` | Superadmin |
| `trainer` | Trainer |
| `exam_operator` | Prüfungsoperator |
| `examiner` | Prüfer |
| `learner` | Lernender |

Das temporäre Passwort nach der Abnahme ändern oder die Testkonten löschen.
Den Befehl nicht ohne bewusst gesetztes Passwort in einer öffentlich erreichbaren
Produktivinstallation ausführen.

### Testnutzer wieder löschen

Zuerst nur anzeigen, welche verwalteten Testkonten gefunden werden:

```bash
sudo -u aborolms env DJANGO_SETTINGS_MODULE=config.settings.production \
  .venv/bin/python manage.py delete_test_users
```

Die Löschung muss ausdrücklich bestätigt werden:

```bash
sudo -u aborolms env DJANGO_SETTINGS_MODULE=config.settings.production \
  .venv/bin/python manage.py delete_test_users --confirm
```

Gelöscht werden ausschließlich die festen Testbenutzernamen `superadmin`,
`trainer`, `exam_operator`, `examiner` und `learner`.

## Windows Server

PowerShell als Administrator öffnen:

```powershell
Set-ExecutionPolicy Bypass -Scope Process -Force
.\deploy\install-windows.ps1 `
  -RepoUrl "https://example.invalid/aborolms.git" `
  -Domain "lms.example.de"
```

Für einen unbeaufsichtigten Lauf:

```powershell
.\deploy\install-windows.ps1 `
  -RepoUrl "https://example.invalid/aborolms.git" `
  -Domain "lms.example.de" `
  -Unattended
```

Windows nutzt PostgreSQL, IIS, Waitress, Redis und NSSM-Dienste für Anwendung und Celery. Die Datenbankauswahl bleibt für kompatible relationale Backends möglich; MongoDB ist kein unterstütztes Produktionsziel.

## Sicherheitsregeln

- Die Bootstrap-Skripte müssen mit administrativen Rechten laufen; der Webprozess selbst läuft danach unter einem eigenen Dienstkonto.
- PostgreSQL-Passwort, Installer-Token und `FIELD_ENCRYPTION_KEY` niemals in Git einchecken.
- `INSTALLER_ENABLED` nach der Einrichtung nicht wieder aktivieren, außer für eine kontrollierte Neuinstallation.
- Zahlungen sind im ML-Einzelsystem standardmäßig deaktiviert.
- Postfix ist nur eine lokale Transportoption. Für produktive Zustellung sind SPF, DKIM, DMARC und ein getesteter SMTP-Relay zusätzlich erforderlich.
