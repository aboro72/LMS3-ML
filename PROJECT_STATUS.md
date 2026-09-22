# ABoroLMS Projektstatus

## Einzelinstallation – 20.09.2026

- Einzelbetrieb ist der Standard. Genau eine interne Betreiberkonfiguration ersetzt die Mandantenauswahl; mehrere Altbestände werden nicht stillschweigend vermischt.
- Zentrale Verwaltung unter `/verwaltung/`: Benutzer/Einladungen, Design, E-Mail und Zertifikat-Design. Mandanten-Anmeldung, -Registrierung und Organisationsübersicht sind im Einzelbetrieb nicht erreichbar.
- Formulare weisen die interne Betreiberreferenz serverseitig zu; keine Organisationsauswahl in Kursen, Kategorien, Lernpfaden, Fragenkatalogen und Prüfungen. Auch Admin-Formulare blenden die technische Referenz aus.
- Navigation, Tabellen, Operator-Dashboard und Logout verwenden den Einzelbetrieb. Alte Organisations-Verwaltungslinks leiten auf zentrale URLs um.
- Bestehende Fremdschlüssel bleiben intern zur Datenerhaltung bestehen. Betreiberbezeichnung: ML Gruppe. SQLite-Sicherung vor dieser Datenänderung: `tmp/before-single-system.sqlite3`.
- Verifiziert: 40 Accounts-/Prüfungstests erfolgreich; 19 echte HTTP-Seitenabrufe auf Port 8000 mit vier Rollen erfolgreich, inklusive Erstellformularen ohne Organisationsfeld.

## Erledigt

- Produktannahme aktualisiert: ABoroLMS wird als Selfhosting-Produkt geplant, nicht als reines SaaS-Angebot.
- Branding aktualisiert: ABoroSoft wird vorerst ohne GmbH-Bezeichnung gefuehrt.
- Spaeterer Installationsumfang vorgemerkt: GitHub-basierte Installationsskripte fuer Linux mit Apache2 oder Nginx sowie alternativ Windows mit IIS.
- Projektstruktur fuer Phase 1 begonnen: `config`, `apps`, `templates`, `static`, `requirements`, `media`.
- Bestehendes Startprojekt `djangoproject` wurde durch `config` als Django-Projektmodul ersetzt.
- `manage.py` zeigt auf `config.settings.development`.
- Custom User, Rollen, UserProfile, Organisation und Einladung sind modelliert.
- Admin, Auth-Routing, Registrierung, Dashboard, Base-Templates und ABoroLMS-CSS sind angelegt.
- Initial-Migrations fuer `accounts` und `organisations` sind vorhanden.
- Entwicklungsabhaengigkeiten wurden in `.venv` installiert.
- `python manage.py check`, `makemigrations --check --dry-run` und `migrate` wurden erfolgreich ausgefuehrt.
- Phase 2 umgesetzt: `courses`-App mit Kurs, Abschnitt, Lektion, Einschreibung und Lektionsfortschritt.
- Kurs-Katalog, Kurs-Detailseite, Einschreibung, Lerninterface und Trainer-Kursverwaltung sind angelegt.
- Demo-Daten enthalten jetzt eine Demo-Organisation, Rollen-Nutzer und einen veroeffentlichten Beispielkurs.
- Demo-Daten enthalten einen Benutzer je Rolle; die Zugangsdaten werden auf der Startseite angezeigt.
- Startseiteninhalt wurde produktnaeher ueberarbeitet; Demo-Benutzerbereich bleibt unveraendert sichtbar.
- Phase 2 wurde validiert: `check`, Migration, Demo-Command und Smoke-Tests fuer Katalog, Detail, Lernen und Trainerseiten.
- Demo-Kurs `ABoroLMS Grundlagen` ist mit der Zertifikatspruefung `ABoroLMS Grundlagen Zertifikatspruefung` verbunden.
- Demo-Kurs `ABoroLMS Grundlagen` enthaelt 4 Abschnitte und 8 vorbereitende Lerneinheiten passend zur Zertifikatspruefung.
- Kurslektionen unterstuetzen Video-Uploads fuer Selfhosting: Trainer koennen MP4/WebM/MOV/M4V hochladen oder eine Video-URL hinterlegen.
- Lerninterface spielt hochgeladene Videos ueber HTML5-Video ab und zeigt bei fehlender Videodatei einen Platzhalter.
- Lektionen unterstuetzen mehrere Begleitmaterialien sowie optionale Multiple-Choice-Uebungsfragen zur Lernfortschrittspruefung.
- Demo-Kurs enthaelt jetzt 8 Uebungsfragen, 24 Uebungsantworten und 2 Begleitmaterialien.
- Bezahlte Kurse werden ueber eine Payment-App abgebildet: Stripe, Google Pay, PayPal und Ueberweisung sind als Zahlungsarten vorhanden.
- Zahlungsanbieter und optionale API-Keys koennen in den Django-Admin-Zahlungseinstellungen aktiviert und gepflegt werden.
- Nach bestaetigter Zahlung wird die Einschreibung bezahlt markiert und der Kurs dauerhaft freigeschaltet.
- Zahlungen laufen zentral ein; pro Zahlung werden 15% Plattformgebuehr und 85% Trainer-Anteil fest gespeichert.
- Superadmin-Auszahlungsuebersicht zeigt offene Trainer-Summen und erlaubt manuelle Bestaetigung von Ueberweisungen sowie Auszahlungstracking.
- Demo-Kurs `ABoroLMS Grundlagen` kostet 49 EUR; Demo-Zahlungen zeigen 7,35 EUR Plattformgebuehr und 41,65 EUR Trainer-Anteil.
- Demo-Pruefung enthaelt 8 Fragen und 30 Antworten mit plausiblen falschen Antworten und passenden richtigen Antworten.
- Pruefungsdetail, Pruefungsstart, Durchfuehrungsseite und Ergebnisansicht sind fuer den Demo-Fluss angelegt.
- RollenMixin leitet anonyme Nutzer jetzt korrekt zum Login weiter, statt auf `AnonymousUser.profile` zuzugreifen.

- Phase 3 abgeschlossen: Trainer-Fragenkatalog-UI, Trainer-Pruefungs-UI, CSV-Import-UI, Examiner-Queue und Freitext-Bewertung fertiggestellt.
- Zuordnungsfragen (ZO) haben jetzt eine vollstaendige Dropdown-UI im Pruefungsablauf.
- Navbar zeigt rollenbasierte Links: Trainer-Dropdown, Examiner-Queue, Org-Admin-Dropdown, Superadmin-Dropdown.
- Phase 4 abgeschlossen: Zertifikate (app `certificates`) mit automatischer Ausstellung nach bestandener Pruefung,
  QR-Code, WeasyPrint-PDF-Download und oeffentlicher Verifikationsseite.
  WeasyPrint-PDF benoetigt GTK3-Runtime unter Windows (https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#windows).
- Phase 5 abgeschlossen: SaaS-Features – Organisation-Selbstregistrierung, OrgAdmin-Dashboard mit KPIs,
  Mitgliederverwaltung mit Einladung, Lizenzlimit-Pruefung bei Kurs-Erstellung und Nutzer-Einladung,
  Superadmin-Organisationsuebersicht.
- Zertifikats-Design je Organisation: Org-Admins koennen Hauptfarbe, Akzentfarbe, Logo, Anzeigename,
  Fusszeile und Unterschriftenzeile individuell konfigurieren. PDF-Export verwendet die Org-Einstellungen.
  Demo-Kurs um Lektion "Zertifikats-Design individualisieren" und zugehoerige Pruefungsfrage ergaenzt.

## Aktuell in Arbeit

- Phase 5 und Zertifikats-Design sind abgeschlossen.

- Installationsskripte erstellt: deploy/install-linux.sh (Debian/Ubuntu, Apache2 oder Nginx),
  deploy/install-windows.ps1 (Windows Server, IIS + Waitress + NSSM + GTK3).

## Noch offen

- GTK3-Runtime fuer WeasyPrint-PDF-Export unter Windows (install-windows.ps1 laed sie automatisch herunter).
- Echte Zahlungsintegration (Stripe, PayPal, Google Pay) mit Webhooks.
- Einladungstoken-Flow: E-Mail-Versand und Annahme-View fuer eingeladene Nutzer.

## Aktualisierung 2026-06-29

- Basisqualitaet erweitert: erste Django-Tests fuer Upload-Validierung, Org-Dashboard-Umsaetze, Einladungsannahme, Zahlungsbelege/Audit und Kursbewertungen hinzugefuegt.
- Upload-Validierung ergaenzt: konfigurierbare Limits und erlaubte Dateiendungen fuer Videos, Dokumente und Bilder.
- Repository-Hygiene ergaenzt: `.gitignore` fuer Python-, Django-, Env- und IDE-Artefakte angelegt.
- Org-Admin-Dashboard korrigiert: Zahlungsstatus verwendet jetzt die Modell-Konstante statt eines falschen Grossbuchstaben-Strings.
- Erweiterungen umgesetzt: Lernpfade, Kursbewertungen, Trainer-Umsatzdashboard, Pruefungsstatistiken, Einladungsannahme per Token, Rechnungen/Belege und Audit-Log.
- Production-Settings fuer optionalen S3-kompatiblen Medien-Storage auf Django-5-`STORAGES` aktualisiert.
- Payment-Provider-Integration mit echten Stripe-/PayPal-/Google-Pay-Webhooks bleibt bewusst offen, bis API-Keys verfuegbar sind.
