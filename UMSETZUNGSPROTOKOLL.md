# Umsetzungsprotokoll ABoroLMS

Grundlage: [Plan zur Modularisierung und zu Zertifikatsprüfungen](PLAN_MODULARISIERUNG_EINZELSYSTEM.md).

## 18.09.2026 – Schritt 1: Zurück-Navigation in Online-Prüfungen

**Status:** Lokal umgesetzt und automatisiert geprüft. Noch nicht auf dem Demo-Server bereitgestellt.

### Auswahl des ersten Schritts

Rückwärtsnavigation lässt sich unabhängig von Lizenzierung, Mandantenmigration und neuen Rollen umsetzen. Fragensuche und Aktivstatus wurden zunächst erwogen, aber zurückgestellt, weil die schreibenden Katalogfunktionen mit der vorgesehenen Operatorrolle abgestimmt werden müssen.

### Was geändert wurde

- Sichtbarer Zurück-Button auf jeder Fragenseite, auch auf der letzten Frage.
- Vor Zurück/Weiter wird die aktuelle Antwort gespeichert. Bei Frage 1 führt Zurück zur internen Übersicht desselben Versuchs; dort kann eine Frage ausgewählt werden.
- Die Übersicht erstellt keinen neuen Versuch und gibt die Prüfung nicht ab. Die bisherige Prüfungszeit läuft weiter.
- SC-, MC- und Wahr/Falsch-Auswahlen werden beim Wiederöffnen korrekt markiert. Freitext/Szenario und Zuordnungen werden ebenfalls wiederhergestellt.
- Zufällige Antwortoptionen werden pro Versuch und Frage reproduzierbar angeordnet, statt bei jedem Seitenaufruf neu gemischt. Dies gilt auch nach erneuter Anmeldung bei unveränderten Optionen und unverändertem Anwendungsschlüssel. Eine dauerhafte Versionierung der Fragen/Optionen ist damit noch nicht umgesetzt.
- Die Option `kein_zurueck` wird in der Online-Prüfungsansicht nicht mehr angewendet und nicht mehr im Prüfungsformular angeboten. Das alte Datenbankfeld bleibt vorerst zur Kompatibilität bestehen. Die vorhandenen formalen Prüfungsabläufe werden einheitlich behandelt; eine neue Unterscheidung von Prüfungsarten wurde nicht eingeführt.
- Zuordnungsantworten aus dem Browser werden als JSON-Objekt validiert und gespeichert. Zuvor konnte der Formularwert als JSON-Zeichenkette statt als Objekt gespeichert werden.
- Der Zuordnungs-Submit-Handler verwendet ausdrücklich das Prüfungsformular. Dadurch hängt er nicht versehentlich am vorher im Seitenkopf stehenden Abmeldeformular.
- Ungültige Fragenpositionen und fehlerhafte Zuordnungen werden ohne Antwortänderung abgewiesen.

### Geänderte Dateien

| Datei | Zweck |
| --- | --- |
| `apps/exams/views.py` | Navigation, interne Übersicht, Vorbelegung und reproduzierbare Antwortreihenfolge |
| `apps/exams/services.py` | Zuordnungsantworten parsen und validieren |
| `apps/exams/forms.py` | Abschaltoption für Rückwärtsnavigation aus dem Formular entfernen |
| `templates/exams/take.html` | Zurück-Button, Übersicht, Auswahlmarkierungen und korrekter Submit-Handler |
| `apps/exams/test_navigation.py` | Sieben neue Regressionstests |
| `PLAN_MODULARISIERUNG_EINZELSYSTEM.md` | Umsetzungsstatus und verbleibende Arbeit aktualisieren |

Keine Datenbankmigration erforderlich; keine Bestandsdaten gezielt verändert.

### Prüfung

- `python manage.py test apps.exams --noinput`: **20 Tests erfolgreich**, davon sieben neue Navigationstests.
- Abgedeckt: Speichern/Zurück/Wiederherstellen aller sechs Fragetypen, interne Übersicht, Weiter und Antwort leeren, stabile Reihenfolge nach neuer Anmeldung, ungültige Eingaben und Zugriff durch fremde Benutzer.
- `python manage.py check`: keine Beanstandungen.
- `git diff --check` für die betroffenen bestehenden Codedateien: keine Whitespace-Fehler.
- Kein manueller End-to-End-Browsertest in diesem Schritt. Die HTML-Antworten und HTTP-Abläufe wurden mit dem Django-Testclient geprüft.

### Noch nicht umgesetzt

- Vollständige Inhalts-/Frageversionierung für bereits laufende Versuche.
- Trainerfreigabe und Operatorrolle einschließlich Entzug bisheriger Trainerrechte.
- Fragensuche, Aktivieren/Deaktivieren und versionierte Frage-/Prüfungsinhalte.
- Operatorgesteuerte PDF-Parameter.
- Modulschalter, Lizenzprüfung, eigenständiger Seriennummerngenerator und Umbau zum Einzelsystem.

### 19.09.2026 – Schritt 2: Vollbild, Autosave und pausierbare Prüfungszeit

**Status:** Lokal umgesetzt, Migration ausgeführt und automatisiert geprüft. Noch nicht auf dem Demo-Server bereitgestellt.

#### Was geändert wurde

- Eine laufende Online-Prüfung fordert Vollbild über die Browser-Fullscreen-API an. Ohne bestätigtes Vollbild wird der Prüfungsinhalt gesperrt und die Zeit nicht aktiviert.
- Vollbildausstieg pausiert die Prüfung; erneutes Vollbild setzt denselben Versuch fort. Ein sichtbarer Status informiert über „läuft“, „pausiert“ oder eine unterbrochene Verbindung.
- Ein Countdown zeigt die verbleibende Zeit. Der Browser berechnet nur die Anzeige; das verbindliche Zeitbudget wird serverseitig geführt.
- Antwort-Autosave bei Auswahl-/Eingabeänderung mit kurzer Verzögerung. Zusätzlich sendet die Oberfläche alle fünf Sekunden einen Heartbeat.
- Bei fehlender Verbindung wird die Bearbeitung gesperrt. Ein veralteter Heartbeat pausiert den Versuch beim nächsten Zugriff; die bis dahin bestätigte Restzeit bleibt erhalten.
- Fortsetzen, Pausieren und Autosave haben getrennte serverseitige Endpunkte und prüfen immer Benutzer, Versuch und Prüfungszugehörigkeit.
- Eine Prüfung speichert jetzt aktive Sekunden, Beginn der aktiven Phase, letzte Aktivität und Pausenzeitpunkt. Die neue Migration `apps/exams/migrations/0008_frage_aktiv_and_more.py` wurde lokal angewendet.
- Fragen besitzen ein `aktiv`-Feld. Die Auswahl neuer Prüfungsfragen berücksichtigt bereits nur aktive Fragen; die Bedienoberfläche zum Umschalten und die Operatorrechte folgen im nächsten Paket.
- Fehlerhafte Zuordnungsdaten und fremde Fragen werden beim Autosave abgewiesen. Mehrfache oder verspätete Browserrequests dürfen keine fremde Antwort speichern.
- Die bestehende Zurück-Navigation arbeitet mit diesem Autosave zusammen. Vor Navigation wird weiterhin das vollständige Formular gespeichert.

#### Geänderte Dateien

| Datei | Zweck |
| --- | --- |
| `apps/exams/models.py` | Aktiver Zeitstatus des Versuchs und `Frage.aktiv` |
| `apps/exams/migrations/0008_frage_aktiv_and_more.py` | Datenbankmigration |
| `apps/exams/services.py` | Zeitbudget, Pause/Fortsetzen, Heartbeat und aktive Fragenauswahl |
| `apps/exams/views.py` | Fortsetzen-, Pausieren- und Autosave-Endpunkte sowie veraltete Heartbeats |
| `apps/exams/urls.py` | Neue Prüfungsendpunkte |
| `templates/exams/take.html` | Vollbildstart, Status, Countdown, Heartbeat und Autosave-JavaScript |
| `apps/exams/test_navigation.py` | Autosave-, Heartbeat- und Zeitpausen-Regressionstests |

#### Prüfung

- Migration `exams.0008` erfolgreich angewendet.
- `python manage.py test apps.exams --noinput`: **22 Tests erfolgreich**.
- `python manage.py check`: keine Beanstandungen.
- Geprüft: Autosave von Antworten, serverseitige Heartbeats, Pause/Fortsetzen, eingefrorene aktive Sekunden, Restzeit, Vollzugriffsschutz und bestehende Navigation.

#### Noch offene Grenzen

- Die Fullscreen-API kann durch den Benutzer beendet werden und sperrt nicht das gesamte Betriebssystem. Das System reagiert darauf mit Pause; ein verwalteter Kiosk-/Prüfungsbrowser wäre ein eigenes Paket.
- Ein harter Prozessabbruch kann das letzte noch nicht übertragene Zeichen verlieren. Bestätigte Autosaves bleiben erhalten; Eingaben werden bei Änderung und per Heartbeat regelmäßig übertragen.
- Trainerfreigabe, Prüfungsoperator, Fragensuche/Aktivschalter und versionierte PDF-/Prüfungsparameter sind noch nicht umgesetzt.

### Nächster sinnvoller Schritt

### 18.09.2026 – Schritt 3: Prüfungsoperator als Rolle

**Status:** Lokal umgesetzt, Migration ausgeführt und automatisiert geprüft. Noch nicht auf dem Demo-Server bereitgestellt.

#### Was geändert wurde

- Neue globale Rolle `exam_operator` / „Prüfungsoperator“ in `Rolle` ergänzt.
- Die bestehende `post_migrate`-Logik legt die Gruppe automatisch an; die Rolle ist damit auch in neuen Installationen vorhanden.
- Eine eigene Hilfe-Seite für die Rolle verhindert, dass ein Operator im Rollenhilfe-Bereich auf eine unbekannte Rollen-ID läuft.
- Der Context-Processor stellt `ist_exam_operator` für die spätere Navigation und Rechteauswertung bereit.
- Die Rollen-Choice-Migration `apps/accounts/migrations/0004_alter_userprofile_rolle.py` wurde lokal angewendet.
- Noch keine Katalogrechte verschoben: Die bisherige Trainer-Katalogoberfläche bleibt bewusst unverändert, damit dieser Schritt nicht unbemerkt bestehende Berechtigungen abschneidet.

#### Geänderte Dateien

| Datei | Zweck |
| --- | --- |
| `apps/accounts/models.py` | Neue Rolle `EXAM_OPERATOR` |
| `apps/accounts/context_processors.py` | Operatorstatus für Templates |
| `apps/accounts/views.py` | Hilfe-Inhalte für Prüfungsoperatoren |
| `apps/accounts/migrations/0004_alter_userprofile_rolle.py` | Rollen-Choice aktualisieren |
| `apps/accounts/test_exam_operator.py` | Regressionstest für Choice, Gruppe und Profil |

#### Prüfung

- Migration `accounts.0004` erfolgreich angewendet.
- `python manage.py test apps.accounts apps.exams --noinput`: **29 Tests erfolgreich**.
- `python manage.py check`: keine Beanstandungen.

#### Noch offen in Phase 5a

- Katalog- und Prüfungsparameter-Views serverseitig auf Prüfungsoperatoren begrenzen.
- Trainerrechte für Zertifikatsfragen und Parameter entfernen, ohne normale LMS-Kursarbeit zu sperren.
- Suche, Aktiv/Inaktiv-Bedienung, CSV-Vorschau und Inhaltsversionierung ergänzen.

### 20.09.2026 – Schritt 4: Operatorrechte, Fragensuche und Aktivstatus

**Status:** Lokal umgesetzt und getestet. Noch nicht auf dem Demo-Server bereitgestellt.

#### Was geändert wurde

- Katalog- und Prüfungsparameter-Änderungen (Erstellen, Bearbeiten, Löschen, Fragen/Antworten, Zuordnungen, CSV-Import, Themen und Prüfungsparameter) verlangen serverseitig `EXAM_OPERATOR`.
- Trainer behalten Prüfungslisten, Statistiken, Ergebnisse sowie Prüflings- und Lösungs-PDFs. Bearbeiten-/Erstellen-Schaltflächen werden Trainern nicht angeboten.
- Fragenkataloge können nach Fragen-ID, Fragetext und Erklärung durchsucht und nach aktiv/inaktiv gefiltert werden.
- Operatoren können Fragen aktivieren oder deaktivieren. Deaktivierte Fragen werden bei neuen Prüfungsziehungen nicht verwendet; laufende Versuche bleiben unverändert.
- Die Katalognavigation wird für reine Trainer ausgeblendet.
- Operatorprofile werden in den Katalog- und Prüfungsformularen als zulässiger Organisationskontext berücksichtigt.

#### Geänderte Dateien

| Datei | Zweck |
| --- | --- |
| `apps/accounts/mixins.py` | Wiederverwendbarer Operatorzugriff |
| `apps/exams/views.py` | Operator-Guards, Suche, Statusfilter und Aktivschalter; kombinierter Trainer-/Operator-Lesezugriff |
| `apps/exams/forms.py` | Organisationsauswahl für Operatorprofile |
| `apps/exams/urls.py` | Aktiv/Inaktiv-Endpunkt |
| `templates/exams/trainer/catalog_form.html` | Such-/Statusfilter und Aktivschalter je Frage |
| `templates/exams/trainer/catalog_list.html` | Katalogsuche |
| `templates/exams/trainer/exam_list.html` | Bearbeitungsaktionen nur für Operatoren |
| `templates/base.html` | Katalognavigation nur für Operatoren |
| `apps/exams/test_operator_permissions.py` | Rechte-, Such- und Aktivstatus-Regressionstests |

#### Prüfung

- `python manage.py test apps.exams apps.accounts --noinput`: **31 Tests erfolgreich**.
- `python manage.py check`: keine Beanstandungen.
- Geprüft: Trainerzugriff auf den Katalogeditor wird mit 403 abgewiesen; Operator kann suchen, deaktivieren und den Statusfilter verwenden.

#### Noch offen

- Trainerfreigabe pro Zertifikatsdurchführung und Teilnehmer.
- Unveränderliche Prüfungsversionen, CSV-Vorschau/Dublettenregeln und Änderungsverlauf.
- Operatorgesteuerte PDF-Parameter.

### Nächster sinnvoller Schritt

Serverseitige Trainerfreigabe für konkrete Zertifikatsdurchführungen umsetzen. Danach PDF-Parameter und unveränderliche Prüfungsversionen ergänzen.
### 20.09.2026 - Schritt 5: Trainerfreigabe pro Teilnehmer | Lokal umgesetzt. PruefungsFreigabe-Modell, Trainer-/Operator-Freigabe und Widerruf, serverseitige Startpruefung, Migration exams.0009 sowie 3 Freigabetests umgesetzt. Naechster Schritt: PDF-Parameter und unveraenderliche Pruefungsversionen.
### 20.09.2026 - Schritt 6: Operatorgesteuerte PDF-Parameter | Lokal umgesetzt. Pruefung speichert Antwortzeilen und optionale Fusszeile; beide PDF-Fassungen verwenden diese Werte. Migration exams.0010 und 34 Tests erfolgreich. Naechster Schritt: unveraenderliche Pruefungsversionen mit festem Fragen-Snapshot.
### 20.09.2026 - Schritt 7: Unveraenderliche Pruefungsversion je Versuch | Lokal umgesetzt. Neue Pruefungsversion speichert Parameter, gezogene Fragen, Antwortoptionen, Erklaerungen und Bewertungshinweise als JSON-Snapshot; jeder neue Versuch wird damit verknuepft. Migration exams.0011 und 35 Tests erfolgreich. Naechster Schritt: PDF-Archiv und Snapshot-Version gemeinsam ausliefern.
### 20.09.2026 - Schritt 8: Einzelsystem-Branding fuer ML Gruppe | Konfigurationsgrundlage umgesetzt. Single-System-Einstellungen fuer Marke, Domain und Organisations-Slug sowie dynamischer Markenname im Grundlayout ergaenzt. Der Schalter bleibt bis zur Datenmigration deaktiviert. Website ml-gruppe.de war aus der Entwicklungsumgebung nicht abrufbar; verbindliche Logo-/Farbwerte werden daher ueber OrganisationDesign eingespielt. Systemcheck und 35 Tests erfolgreich.
Klarstellung zu Schritt 8: ml-gruppe.de ist erreichbar, liefert aktuell jedoch eine Spaceship-Domainverkaufsseite (Domain for sale) und keine ML-Gruppe-Unternehmensseite. Es wurden deshalb keine Spaceship-Farben oder Fremdmarken in das LMS uebernommen. Fuer die endgueltige Gestaltung werden die kuenftigen ML-Gruppe-Brandingwerte ueber OrganisationDesign hinterlegt.
Ergaenzung zu Schritt 8: Die zentrale Startseite wurde auf ML Gruppe umgestellt. Inhalte sprechen jetzt Lernpfade, Zertifikatspruefungen und Nachweise an; neue Hero-/Kartenstile nutzen das ML-Farbset aus mlgruppe.de.
### 20.09.2026 - Schritt 9: Zentrale Einzelsystem-Startseite | Neue Routen /startseite/, /startseite/editor/ und /startseite/pagebuilder/ ergaenzt. Im aktivierten SINGLE_SYSTEM_MODE wird die konfigurierte Betreiberorganisation intern automatisch verwendet; sichtbare Organisations-Slugs und Organisationswechsel sind im normalen Ablauf nicht erforderlich. Pagebuilder bleibt optional. Systemcheck und Logouttests erfolgreich.
Ergaenzung zu Schritt 9: Organisationsregistrierung (/organisationen/signup/) aus der URL-Konfiguration entfernt. OrgAdmin-Navigation wird im Einzelsystem nicht mehr angezeigt; zentrale Design-/Startseitenverwaltung ist Superadmin vorbehalten. Weiterleitungs-URL-Felder werden im Single-System ausgeblendet. Tenant-Template-Links verwenden im Single-System die zentralen URLs statt tenant_* Endpunkten.
Demo-Rollen aktualisiert: orgadmin wird beim create_demo_data-Lauf entfernt; neuer Zugang exam_operator (Passwort ChangeMe123!) wird als Pr�fungsoperator mit UserProfile angelegt. Der Operator erh�lt eigene Navigation f�r Fragenkataloge und Pr�fungen.
