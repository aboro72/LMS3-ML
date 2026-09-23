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
