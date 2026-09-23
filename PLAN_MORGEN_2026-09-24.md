# Arbeitsplan ABoroLMS – 24.09.2026

## Geprüfter Ausgangsstand am 23.09.2026

- `manage.py check`: erfolgreich.
- `makemigrations --check --dry-run`: keine offenen Migrationen.
- Vollständige Testsuite: **47 Tests erfolgreich**.
- Superadmin-Dashboard: technische Informationen, Auslastung, Benutzerverwaltung und Django-Admin-Link umgesetzt.
- Startseiten-PageBuilder: Drag-and-drop-Bausteine lokal umgesetzt; Serverbereitstellung steht noch aus.
- Produktionsserver: Gunicorn, PostgreSQL, Nginx/ISPConfig-Proxy und Staticfiles wurden grundsätzlich eingerichtet.
- Zahlungen: im ML-Einzelsystem bewusst deaktiviert; echte Stripe-/PayPal-/Google-Pay-Integration ist daher kein morgiger Schwerpunkt.

## Priorität 1 – zuerst erledigen

### 1. Lokale Änderungen sicher auf den Server bringen

Vorher eine Sicherung von Datenbank, `.env`, `media` und `staticfiles` erstellen. Danach übertragen:

- `apps/accounts/views.py`
- `apps/organisations/views.py`
- `templates/accounts/dashboard.html`
- `templates/organisations/startseite_pagebuilder.html`
- `templates/home.html`
- aktuelle Produktions-/Installerdateien und Requirements

Auf dem Server anschließend:

```bash
cd /opt/aborolms
sudo -u aborolms .venv/bin/python manage.py migrate --noinput
sudo -u aborolms .venv/bin/python manage.py collectstatic --noinput
sudo systemctl restart aborolms
sudo systemctl status aborolms --no-pager
```

### 2. Browser-Abnahme der wichtigsten Rollen

Mit echten Testkonten prüfen:

- Superadmin: `/dashboard/`, `/verwaltung/benutzer/`, `/admin/`
- Prüfungsoperator: Fragenkataloge und Prüfungen verwalten
- Trainer: Teilnehmer, Versuche, bestanden/nicht bestanden und Versuchnummern
- Lernender: Einladungen, freigegebene Prüfungen, Ergebnisse und Versuche
- Prüfer: offene manuelle Bewertungen

Direkte unberechtigte URLs ebenfalls testen. Erwartung: Login, 403 oder 404 — niemals fremde Daten.

### 3. Öffentliche und technische Seiten abnehmen

- `/`
- `/accounts/login/`
- `/startseite/`
- `/startseite/editor/`
- `/startseite/pagebuilder/`
- `/static/css/aborolms.css`
- Zertifikatsverifikation und PDF-Download

Dabei besonders prüfen: CSS/JavaScript, HTTPS-Weiterleitung, Upload-Größe und keine 400/404/500/502-Fehler.

## Priorität 2 – danach

### 4. Backup und Restore praktisch testen

- PostgreSQL-Dump erzeugen.
- Medienverzeichnis separat sichern.
- Neue Testdatenbank aus dem Dump wiederherstellen.
- `migrate`, `check`, Login, Prüfung, Zertifikat und PDF nach Restore prüfen.
- Rücksicherungsbefehle dokumentieren.

### 5. Datenmigration vorbereiten

Noch keine produktive Löschung oder Zusammenführung durchführen. Zuerst ein lesendes Prüfkommando erstellen, das berichtet:

- Benutzer und Rollen
- Organisationen und aktive Profile
- Fragenkataloge und Prüfungen
- Einladungen, Anmeldungen und laufende Versuche
- Zertifikate und PDFs
- Dateien und Dateiprüfsummen
- alte Zahlungen nur als Bestand, nicht als aktiver ML-Zahlungsfluss

Danach festlegen, welche Organisation als Betreiberbestand übernommen wird.

### 6. Produktionsabnahme dokumentieren

Für jeden Test festhalten:

- URL und Rolle
- erwartetes Ergebnis
- tatsächliches Ergebnis
- Screenshot oder Logauszug bei Fehlern
- Status: bestanden/offen

## Priorität 3 – Sicherheits- und Qualitätsarbeiten

- Upload-Sicherheit um MIME-Prüfung und Virenscan-Konzept erweitern.
- Videoverarbeitung und ffmpeg-Fehlerfälle prüfen.
- Datenschutz-/Verschlüsselungs-TODOs für Rechnungsdaten, Hash-Lookups, Export, Löschung und Key-Rotation planen.
- Rechtliche Prüfung von Zertifikaten, Rechnungen, Impressum, Datenschutz und E-Mail-Texten vorbereiten.
- Browser-Regressionstests mit Desktop und Mobilbreite ergänzen.
- PDF-Regressionstests für Prüfungsbogen, Lösungsbogen und Zertifikat durchführen.

## Bewusst nicht für morgen einplanen

- Stripe, PayPal und Google Pay: im ML-Einzelsystem deaktiviert.
- Vollständiger Lizenzgenerator und Seriennummernmodul.
- Entfernung aller historischen Organisations-Fremdschlüssel aus dem Datenmodell. Diese bleiben vorerst als interne Bestandsreferenzen erhalten.

## Fertig-Kriterium für morgen

Der Stand gilt als abgenommen, wenn:

1. der aktuelle Code auf dem Server läuft,
2. keine offenen Migrationen vorliegen,
3. Staticfiles geladen werden,
4. die vier Hauptrollen ihre erlaubten Wege erfolgreich durchlaufen,
5. keine fremden Daten erreichbar sind,
6. Backup und Restore einmal erfolgreich durchgeführt wurden,
7. alle gefundenen Fehler mit Priorität und Logauszug dokumentiert sind.
