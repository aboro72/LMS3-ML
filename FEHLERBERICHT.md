# Fehlerbericht ABoroLMS

## Aktualer Gesamtstand – 23.09.2026

Die historische Mandanten-Isolationskorrektur ist abgeschlossen. Die aktuelle
lokale Validierung ergibt `manage.py check` ohne Fehler, keine offenen Migrationen
und **47 erfolgreiche Tests**. Zusätzlich wurden Produktionsinstallation,
PostgreSQL/Gunicorn/Nginx/Redis/Celery, Staticfiles, PageBuilder und das technische
Superadmin-Dashboard ergänzt.

Für die Produktivfreigabe verbleiben: Serverbereitstellung der letzten Änderungen,
Backup/Restore, Datenmigrationsprobe, Browser-/PDF-Regression, Upload-/Virenscan-
Konzept, Datenschutzphase 2 und rechtliche Prüfung. Zahlungen bleiben im
ML-Einzelsystem deaktiviert.

Nachtrag 2026-09-10: Lokale Produktionspruefungen und Payment-Deaktivierung sind in
[PRODUKTIONSPRUEFUNG.md](PRODUKTIONSPRUEFUNG.md) dokumentiert. Payment ist lokal
ausgeschaltet und ueber die Superadmin-Zahlungseinstellungen wieder aktivierbar.

Stand: 2026-09-09

## Nachpruefung und ergaenzende Korrektur am 2026-09-09

Die unten dokumentierte Erstkorrektur war unvollstaendig: Die Kursliste war
rollenbewusst gefiltert, die direkte Kursbearbeitung verwendete aber weiterhin
`OrganisationMixin` und damit alle aktiven Organisationsprofile. Der GET-Zugriff
auf einen fremden Kurs lieferte fuer Lernende und Organisationsadministratoren
mit Trainerrolle in einer anderen Organisation weiterhin HTTP 200 statt 404.
Neue Regressionstests haben diesen Fehler vor der Korrektur reproduziert.

`TrainerKursUpdateView.get_queryset()` verwendet jetzt ebenfalls
`trainer_course_queryset()`. Damit werden sowohl direkte GET-Zugriffe als auch
manipulierte POST-Anfragen auf Kurse ausserhalb der aktiven Trainerorganisationen
mit HTTP 404 abgewiesen. Dies verhindert auch das Verschieben eines fremden
Kurses in eine eigene Organisation durch Manipulation des Formulars.

Die neue Testklasse `TrainerCourseEditIsolationTests` prueft fremde Lernenden-
und Organisationsadministratorprofile, inaktive Trainerprofile sowie den
weiterhin erlaubten Zugriff aktiver Trainer und Superuser.

Abschliessende Validierung mit `.venv/Scripts/python.exe`:

- `manage.py check`: keine Probleme.
- `manage.py makemigrations --check --dry-run`: keine ausstehenden Modellaenderungen.
- `manage.py test --noinput`: 40 Tests in 85.136 Sekunden, alle erfolgreich.

Die nachfolgenden Angaben zu 30 Tests beschreiben die historische Erstpruefung.
Die aufgefuehrten Rest-Risiken bleiben gesonderte Integrations-, Betriebs- und
Pruefaufgaben; sie sind durch diese Mandantenkorrektur nicht erledigt.

## Zusammenfassung

Bei der Erweiterung der Unit- und Integrationstests wurde ein sicherheitsrelevanter Mandanten-Isolationsfehler gefunden und behoben. Trainer konnten in bestimmten Konstellationen Kurse, Fragenkataloge oder Pruefungen aus Organisationen sehen und bearbeiten, in denen sie zwar ein aktives Profil hatten, aber nicht die Trainerrolle.

Der Fehler ist behoben und durch neue Tests abgesichert. Die finale Validierung laeuft mit 30 Tests erfolgreich durch.

## Gefundener Fehler

### Fehler-ID

`ABOROLMS-TENANT-001`

### Titel

Trainer-Querysets beruecksichtigten aktive Organisationsprofile, aber nicht zwingend die Trainerrolle.

### Schweregrad

Hoch

### Kategorie

Mandanten-Isolation, Rollen-/Rechtepruefung, Datenzugriff

### Betroffene Bereiche

- Trainer-Kursverwaltung
- Trainer-Kursformular
- Trainer-Fragenkataloge
- Trainer-Pruefungen

### Betroffene Dateien

- `apps/courses/views.py`
- `apps/courses/forms.py`
- `apps/exams/views.py`
- `apps/exams/forms.py`

## Beschreibung

Ein Benutzer kann mehrere `UserProfile`-Eintraege besitzen, beispielsweise:

- Trainer in Organisation A
- Lernender in Organisation B

Die bisherigen Querysets fuer Trainerbereiche haben alle aktiven Organisationen eines Nutzers verwendet. Dabei wurde nicht geprueft, ob der Nutzer in der jeweiligen Organisation wirklich die Rolle `trainer` besitzt.

Dadurch konnte ein Trainer aus Organisation A im Trainerbereich auch Kurse, Fragenkataloge oder Pruefungen aus Organisation B sehen, wenn er dort nur als Lernender oder in einer anderen Rolle aktiv war.

## Reproduktion vor dem Fix

### Voraussetzungen

1. Organisation A existiert.
2. Organisation B existiert.
3. Benutzer `trainer` hat Profil:
   - Organisation A, Rolle `trainer`
   - Organisation B, Rolle `learner`
4. Organisation B besitzt einen Kurs, Fragenkatalog oder eine Pruefung.

### Schritte

1. Als `trainer` einloggen.
2. Trainer-Kursverwaltung unter `/trainer/kurse/` oeffnen.
3. Trainer-Fragenkataloge unter `/trainer/fragenkataloge/` oeffnen.
4. Trainer-Pruefungen unter `/trainer/pruefungen/` oeffnen.

### Fehlerhaftes Ergebnis vor dem Fix

Objekte aus Organisation B wurden angezeigt, obwohl der Benutzer dort keine Trainerrolle hatte.

### Erwartetes Ergebnis

Trainerbereiche duerfen nur Objekte aus Organisationen anzeigen, in denen der Benutzer ein aktives Profil mit Rolle `trainer` besitzt.

## Technische Ursache

Die Querysets verwendeten sinngemaess:

```python
organisation_ids = user.profile.filter(aktiv=True).values_list("organisation_id", flat=True)
```

Diese Logik ist fuer allgemeine Organisationszuordnung zu breit. Fuer Trainerfunktionen muss die Rolle eingeschraenkt werden:

```python
organisation_ids = user.profile.filter(
    rolle=Rolle.TRAINER,
    aktiv=True,
).values_list("organisation_id", flat=True)
```

## Korrektur

Die Querysets und Formularfilter wurden rollenbewusst gemacht.

### Geaenderte Logik

- `apps/courses/views.py`
  - `trainer_course_queryset()` filtert nur noch Organisationen mit aktiver Trainerrolle.

- `apps/courses/forms.py`
  - `KursForm` zeigt Nicht-Superusern nur Organisationen, in denen sie Trainer sind.

- `apps/exams/views.py`
  - `trainer_catalog_queryset()` filtert nur noch Organisationen mit aktiver Trainerrolle.
  - `trainer_exam_queryset()` filtert nur noch Organisationen mit aktiver Trainerrolle.

- `apps/exams/forms.py`
  - `FragenkatalogForm` und `PruefungForm` beschraenken Organisationen/Kataloge auf aktive Trainerorganisationen.

## Neue Tests zur Absicherung

Die Testdatei wurde erweitert:

`apps/courses/tests.py`

### Neue Testklassen

- `UploadValidationTests`
- `CourseAccessAndReviewTests`
- `LearningPathTests`
- `OrganisationInvitationTests`
- `PaymentAndInvoiceTests`
- `ExamServiceTests`
- `CertificateViewTests`
- `TrainerExamTenantIsolationTests`

### Relevante Mandanten-Isolationstests

- `test_trainer_course_list_only_contains_trainer_role_organisations`
- `test_trainer_catalog_list_only_contains_trainer_role_organisations`
- `test_trainer_exam_list_only_contains_trainer_role_organisations`

Diese Tests bilden exakt die gefundene Risikokonstellation ab: Ein Benutzer ist Trainer in einer Organisation und Lernender in einer anderen Organisation. Die fremde Organisation darf im Trainerbereich nicht sichtbar sein.

## Aktueller Teststand

Final ausgefuehrt:

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

Ergebnis:

```text
System check identified no issues (0 silenced).
No changes detected
Found 30 test(s).
Ran 30 tests in 63.929s
OK
```

## Weitere abgesicherte Bereiche

Neben dem gefundenen Mandantenfehler prueft die neue Testbasis jetzt auch:

- Upload-Validierung fuer Dateiendungen und Dateigroessen
- Zugriff auf bezahlte Kurse
- Kursbewertungen inklusive Aktualisierung bestehender Bewertung
- Lernpfad-Einschreibung und Fortschritt
- Organisations-Dashboard-Umsaetze
- Einladungsannahme per Token
- abgelaufene oder falsche Einladungen
- Zahlungserstellung und Audit-Log
- Zahlungsbestaetigung, Einschreibung und Rechnungserstellung
- Idempotenz der Zahlungsbestaetigung
- private Rechnungssichtbarkeit
- Zahlungseinstellungen als Singleton
- Pruefungsbewertung fuer Single Choice, Multiple Choice, Freitext und Zuordnung
- maximale Pruefungsversuche
- Zeitlimit-Ablauf
- automatische Zertifikatserstellung nach bestandener Pruefung
- oeffentliche Zertifikatsverifikation
- geschuetzter Zertifikats-PDF-Download

## Nicht gefundene Fehler in der aktuellen Testabdeckung

Die aktuelle Testausfuehrung zeigt keine weiteren Fehler in den abgedeckten Bereichen. Das bedeutet nicht, dass das System vollstaendig fehlerfrei ist, sondern dass die aktuell automatisiert geprueften Kernfluesse stabil laufen.

## Bekannte Rest-Risiken

### Payment-Provider

Echte Stripe-/PayPal-/Google-Pay-Flows sind bewusst noch nicht implementiert oder getestet, weil die API-Keys noch fehlen. Demo- und manuelle Zahlungsfluesse sind getestet.

### Browser-/UI-Regressionen

Die Tests pruefen serverseitige Views, Rechte, Datenbanklogik und Services. Visuelle Layout-Probleme oder JavaScript-Probleme werden damit nicht vollstaendig erkannt.

### Datei-Uploads in Produktion

Dateiendungen und Groessenlimits sind getestet. Noch nicht abgedeckt sind Virenscan, MIME-Sniffing auf Serverebene, Webserver-Limits und Video-Transcoding.

### Rechtliche Rechnungsdetails

Belege werden technisch erzeugt und geschuetzt angezeigt. Steuerlogik, fortlaufende Nummern nach produktiven gesetzlichen Anforderungen und Rechnungspflichtangaben sollten vor Live-Betrieb fachlich/rechtlich geprueft werden.

### Nebenlaeufigkeit

Die Rechnungsnummernlogik ist fuer normale Nutzung vorbereitet, aber noch nicht explizit gegen parallele Zahlungsbestaetigungen unter hoher Last getestet.

## Empfehlung

Vor dem produktiven Einsatz sollten als naechste Qualitaetsschritte folgen:

1. Browserbasierte Smoke-Tests fuer die wichtigsten Seiten.
2. Tests fuer Admin-Aktionen und Superadmin-Flows.
3. Tests fuer E-Mail-Versand und Einladungs-E-Mail-Inhalt.
4. Provider-Tests fuer Stripe-Webhooks, sobald API-Keys verfuegbar sind.
5. Security-Review fuer alle rollen- und mandantenbezogenen Views.
6. Last-/Nebenlaeufigkeitstest fuer Rechnungsnummern und Zahlungsbestaetigungen.
