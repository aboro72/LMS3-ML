# ABoroLMS Handover

Stand: 2026-09-23

## Verbindlicher aktueller Stand

- Django **6.1.1**, Python 3.12–3.14; lokale Umgebung Python 3.14.
- PostgreSQL ist die Produktionsreferenz; Linux nutzt Gunicorn, Nginx/ISPConfig, Redis und Celery.
- ML Gruppe wird als Einzelsystem betrieben. Zahlungen sind für diesen Betrieb deaktiviert; historische Daten bleiben erhalten.
- Superadmin-Dashboard: technische Informationen, Auslastung, Benutzerverwaltung und direkter Django-Admin-Link.
- Startseite: zentraler Editor und visueller Drag-and-drop-PageBuilder vorhanden; produktive Serverabnahme offen.
- Letzte lokale Validierung: `check` OK, keine offenen Migrationen, **47 Tests OK**.
- Priorität vor Produktivfreigabe: Deployment der letzten Änderungen, Browser-/PDF-Abnahme, Backup/Restore und Datenmigrationsprobe.

## Kurzbeschreibung

ABoroLMS ist aktuell ein Selfhosting-orientiertes Django-LMS mit klassischem Server-Side-Rendering. Es ist als Udemy-aehnliche Kursplattform gedacht: Trainer koennen Kurse mit Kapiteln, Lektionen, Video-Uploads, Begleitmaterial und Uebungsfragen erstellen. Lernende koennen Kurse kaufen, bearbeiten, ihren Fortschritt speichern, Uebungen beantworten und eine Zertifikatspruefung starten. Zahlungen werden zentral auf ein ABoroSoft-Konto gefuehrt; Trainer-Auszahlungen werden manuell vorbereitet und mit 15% Plattformgebuehr berechnet.

## Technischer Stand

- Backend: Django 6.1.1, Python 3.14 lokal; Python 3.12–3.14 werden unterstützt.
- Frontend: Django Templates, Bootstrap 5, Vanilla JS, SortableJS fuer Kursstruktur.
- Settings: `config.settings.development` fuer lokale Entwicklung, `config.settings.production` vorbereitet.
- Datenbank lokal: SQLite `db.sqlite3`.
- Rich Text: `django-quill-editor`.
- Datei-Uploads: lokal ueber `MEDIA_ROOT`; S3-Storage ist in Production-Settings vorbereitet.
- Selfhosting: Linux-Installer für PostgreSQL/Nginx/Gunicorn/Redis/Celery sowie Windows-Installer für PostgreSQL/IIS/Waitress/Redis/NSSM.

## Wichtige Apps

- `apps.accounts`: Custom User, Rollen, UserProfile, Demo-Daten-Command, Rollen-/Organisations-Mixins.
- `apps.organisations`: Organisationen, Einladungen, Lizenztyp.
- `apps.courses`: Kurse, Abschnitte, Lektionen, Video-/Datei-Uploads, Begleitmaterial, Uebungsfragen, Einschreibungen und Fortschritt.
- `apps.exams`: Fragenkataloge, Fragen, Antworten, Pruefungen, Versuche, Teilnehmerantworten, Bewertungsservice.
- `apps.payments`: Zahlungen, Zahlungseinstellungen, Checkout, Freischaltung, Auszahlungsuebersicht.

## Demo-Zugaenge

Alle Demo-Benutzer haben das Passwort `ChangeMe123!`.

| Rolle | Benutzername | E-Mail |
| --- | --- | --- |
| Super-Admin | `superadmin` | `superadmin@example.com` |
| Org-Admin | `orgadmin` | `orgadmin@example.com` |
| Trainer | `trainer` | `trainer@example.com` |
| Pruefer | `examiner` | `examiner@example.com` |
| Lernender | `learner` | `learner@example.com` |

Die Demo-Zugaenge werden auf der Startseite angezeigt und sollen dort vorerst erhalten bleiben.

## Demo-Daten

Management-Command:

```bash
python manage.py create_demo_data
```

Der Command erstellt oder aktualisiert:

- Demo-Organisation `Demo Organisation`.
- Einen Benutzer je Rolle.
- Demo-Kurs `ABoroLMS Grundlagen`.
- 4 Kursabschnitte und 8 Lektionen.
- Erste Lektion als Video-Lektion mit Platzhalter, falls noch keine Datei hochgeladen ist.
- 8 Uebungsfragen, 24 Uebungsantworten und 2 Begleitmaterialien.
- Zertifikatspruefung `ABoroLMS Grundlagen Zertifikatspruefung`.
- Fragenkatalog `ABoroLMS Zertifikatsfragen`.
- 8 Pruefungsfragen und 30 Antworten.
- Demo-Zahlungseinstellungen mit aktivierten Zahlungsarten.
- Demo-Zahlung fuer `learner`, damit der kostenpflichtige Kurs bereits freigeschaltet ist.

## Aktuelle Kernfunktionen

### Rollen und Mandanten

- Rollenmodell basiert auf Django Groups plus `UserProfile`.
- Rollen: `superadmin`, `org_admin`, `trainer`, `examiner`, `learner`.
- `RollenMixin` leitet anonyme Nutzer korrekt zum Login weiter.
- Querysets fuer Trainerbereiche werden nach Organisation gefiltert.

### Kurse

- Kurse haben Preis, kostenlos/bezahlt-Flag, Organisation, Trainer und optional eine Abschlusspruefung.
- Kurskatalog unter `/kurse/`.
- Kursdetail unter `/kurse/<slug>/`.
- Lerninterface unter `/kurse/<slug>/lernen/`.
- Einzelne Lektionen unter `/kurse/<slug>/lernen/<lektion_id>/`.
- Trainerverwaltung unter `/trainer/kurse/`.

### Lektionen

- Typen: Video, Dokument, Text/HTML, Quiz.
- Video-Lektionen unterstuetzen:
  - lokale Uploads: MP4, WebM, MOV, M4V
  - externe Video-URL
  - Platzhalter, wenn noch kein Video hinterlegt ist
- Jede Lektion kann mehrere Begleitmaterialien haben.
- Jede Lektion kann optionale Multiple-Choice-Uebungsfragen haben.
- Uebungsfragen werden direkt ausgewertet und zeigen erklaerende Rueckmeldung.

### Pruefungen

- Fragenkataloge, Fragetypen, Antworten, Zuordnungspaare und Pruefungen sind modelliert.
- Pruefungsstart und Durchfuehrung funktionieren fuer den Demo-Fluss.
- Automatische Bewertung fuer SC/MC/WF/Zuordnung/Freitext-Grundlogik ist in `apps.exams.services`.
- Ergebnisansicht unter `/pruefungen/<id>/ergebnis/<versuch_id>/`.

### Payments

Hinweis für den aktuellen ML-Einzelsystembetrieb: Zahlungen sind deaktiviert.
Die folgenden Zahlungsfunktionen beschreiben den vorhandenen Bestand bzw. ein
optionales späteres Modul und sind nicht Bestandteil der aktuellen Abnahme.

- Zahlungseinstellungen im Django Admin:
  - `/admin/payments/zahlungseinstellungen/1/change/`
- Zahlungsarten:
  - Stripe
  - Google Pay
  - PayPal
  - Ueberweisung
- API-Keys sind optional und koennen im Admin gepflegt werden.
- Demo-Autoconfirm kann in Zahlungseinstellungen aktiviert/deaktiviert werden.
- Bezahlte Kurse fuehren zum Checkout.
- Nach bestaetigter Zahlung wird `Einschreibung.bezahlt=True` gesetzt.
- Ueberweisungen bleiben offen, bis Superadmin den Eingang bestaetigt.
- Superadmin-Auszahlungen:
  - `/superadmin/auszahlungen/`
  - zeigt Bruttosumme, 15% Plattformgebuehr und 85% Trainer-Anteil
  - erlaubt Markierung als Betreiber informiert und ausgezahlt

## Wichtige Befehle

Installation:

```bash
.venv\Scripts\python.exe -m pip install -r requirements\development.txt
```

Migration:

```bash
python manage.py migrate
```

Demo-Daten:

```bash
python manage.py create_demo_data
```

Validierung:

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
```

Start:

```bash
python manage.py runserver
```

## Bereits validiert

Zuletzt erfolgreich:

```bash
python manage.py check
```

Weitere zuvor getestete Flows:

- Startseite rendert mit Demo-Zugaengen.
- Kursdetail und Lernansicht rendern.
- Trainer-Kursbearbeitung rendert.
- Uebungsfragen koennen abgesendet und ausgewertet werden.
- Demo-Checkout per Stripe-Demomodus schaltet Kurs frei.
- Ueberweisung bleibt offen und kann durch Superadmin bestaetigt werden.
- Superadmin-Auszahlungsuebersicht rendert.

## Bekannte Luecken und Risiken

- Echte Stripe-/PayPal-/Google-Pay-Integration ist noch nicht umgesetzt. Es gibt Konfiguration und Demo-Fluss, aber keine Provider-Checkout-Sessions und keine Webhooks.
- Google Pay laeuft praktisch meist ueber Stripe oder einen Payment-Provider. Die finale technische Umsetzung muss providerbezogen entschieden werden.
- Ueberweisungsdaten sind Demo-Daten. Fuer Produktion braucht es saubere Admin-Pflege, Anzeige und rechtliche Texte.
- Trainer-Auszahlungen sind manuell geplant; es gibt noch keinen automatischen Payout-Provider.
- Pruefungs-Trainer-Templates, CSV-Import-UI und Examiner-Queue sind noch nicht vollstaendig produktreif.
- Zertifikatsgenerierung mit PDF, QR-Code und Verify-URL ist umgesetzt; WeasyPrint benoetigt unter Windows GTK3-Runtime.
- Erste automatisierte Tests sind vorhanden; die Abdeckung ist noch fokussiert und sollte weiter ausgebaut werden.
- Datei-Uploads brauchen fuer Produktion Limits, Validierung, Speicherstrategie und ggf. Virenscan.
- Video-Uploads brauchen fuer groessere Dateien Webserver-Konfiguration, max upload size und ggf. Transcoding-Strategie.
- Kein echtes Berechtigungs-Audit fuer alle Views abgeschlossen.
- Installation/Deployment-Skripte fuer Linux und Windows sind vorhanden; produktive Umgebungen muessen je Server validiert werden.

## Empfohlene naechste Schritte

1. Tests ausbauen
   - Rollen-/Mandanten-Zugriffe.
   - Kurskauf und Freischaltung.
   - Pruefungsbewertung.
   - Uebungsfragen-Auswertung.
   - Auszahlungsberechnung 85/15.

2. Payment produktionsreif machen
   - Stripe Checkout Session erstellen.
   - Stripe Webhook fuer `checkout.session.completed`.
   - PayPal Order API integrieren.
   - Google Pay final ueber Stripe oder separaten Provider klaeren.
   - Webhook-Signaturen pruefen.

3. Zertifikate umsetzen
   - `certificates`-App anlegen.
   - Zertifizierung und Zertifikat modellieren.
   - PDF via WeasyPrint erzeugen.
   - QR-Code einbetten.
   - `/verify/<uuid>/` ohne Login.

4. Pruefungssystem abrunden
   - Trainer-UI fuer Fragenkataloge verbessern.
   - CSV-Import vollstaendig mit Fehlerreport.
   - Examiner-Queue visuell und funktional ausbauen.
   - Zeitlimit-Server-Sync sauber implementieren.
   - Szenario-Fragen im UI abbilden.

5. Kursverwaltung professioneller machen
   - Lektionen bearbeiten/loeschen.
   - Drag-and-drop Reihenfolge serverseitig speichern.
   - Kapitel/Lektionen kompakter darstellen.
   - Kurs-Vorschau fuer nicht gekaufte Nutzer.
   - Bewertungs-/Review-System fuer Kurse.

6. Selfhosting vorbereiten
   - `.env.example` finalisieren.
   - Installationsskript fuer Ubuntu + Nginx + Gunicorn.
   - Installationsskript fuer Ubuntu + Apache2 + mod_wsgi oder Gunicorn reverse proxy.
   - Windows/IIS-Konzept klaeren.
   - Media-/Static-Konfiguration dokumentieren.

7. Admin-Oberflaechen
   - Betreiber-Dashboard fuer Umsaetze, offene Ueberweisungen, Auszahlungen.
   - Trainer-Dashboard fuer Verkaeufe und Kursstatistik.
   - Org-Admin Dashboard fuer Nutzer und Lizenzen.

8. Rechtliches und Betrieb
   - Rechnungs-/Beleglogik klaeren.
   - Steuerliche Behandlung zentraler Zahlungen und Trainer-Auszahlungen pruefen.
   - AGB, Datenschutz, Impressum, Widerruf und Zahlungsbedingungen vorbereiten.
   - Audit-Log fuer Zahlungen und manuelle Bestaetigungen.

## Wichtige Dateien fuer Weiterentwicklung

- `PROJECT_STATUS.md`: laufender Fortschrittsstatus.
- `apps/accounts/management/commands/create_demo_data.py`: zentrale Demo-Daten.
- `apps/courses/models.py`: Kurs-, Lektion-, Material- und Uebungsmodelle.
- `apps/courses/views.py`: Kurskatalog, Lerninterface, Trainerpflege.
- `apps/exams/services.py`: Pruefungsbewertung.
- `apps/payments/models.py`: Zahlungen und Zahlungseinstellungen.
- `apps/payments/views.py`: Checkout, Zahlungsstatus, Auszahlungsuebersicht.
- `templates/home.html`: Startseite mit Demo-Zugaengen.
- `static/css/aborolms.css`: aktuelles UI-Stylesheet.

## Hinweis zur Arbeitsweise

Das Projekt ist noch ein Prototyp mit funktionierenden Kernfluesse. Bei der Weiterarbeit zuerst `python manage.py check`, `python manage.py migrate` und `python manage.py create_demo_data` ausfuehren. Danach die wichtigsten Seiten im Browser pruefen: `/`, `/kurse/`, `/kurse/aborolms-grundlagen/`, `/trainer/kurse/`, `/superadmin/auszahlungen/`.

## Aktualisierung 2026-06-29

Neu hinzugekommen:

- Einladungsannahme per Token unter `/organisationen/einladung/<token>/` fuer eingeloggte Nutzer.
- Lernpfade unter `/lernpfade/` mit Einschreibung und Fortschrittsanzeige.
- Kursbewertungen fuer bezahlte/eingeschriebene Nutzer.
- Trainer-Umsatzdashboard unter `/trainer/umsatz/`.
- Pruefungsstatistiken je Trainer-Pruefung.
- Rechnungen/Belege fuer bestaetigte Zahlungen.
- Superadmin-Audit-Log unter `/superadmin/audit-log/`.
- Upload-Limits und erlaubte Dateiendungen sind ueber `.env` konfigurierbar.
- Optionaler S3-kompatibler Medien-Storage ist in `config.settings.production` vorbereitet.

Validierung:

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

Bewusst offen:

- Echte Stripe-/PayPal-/Google-Pay-Provider-Flows und Webhooks, bis die API-Keys fuer Tests verfuegbar sind.
- Ausbau der Testabdeckung ueber die jetzt ergaenzten Kernfluss-Tests hinaus.
