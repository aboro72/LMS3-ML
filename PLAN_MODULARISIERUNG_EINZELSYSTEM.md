# Plan: ABoroLMS als modulares Einzelsystem mit Seriennummern

## Aktualer Implementierungsstand – 23.09.2026

Der ML-Betrieb läuft als Einzelsystem mit PostgreSQL als Produktionsstandard.
Django 6.1.1, Python 3.12–3.14, Installer, Gunicorn/Nginx, Redis/Celery,
Superadmin-Technikdashboard und visueller PageBuilder sind vorhanden. Zahlungen
sind im ML-Einzelsystem deaktiviert; der Zahlungs-/Lizenzumfang dieses Dokuments
bleibt deshalb Zielbild und ist nicht Teil der morgigen Betriebsabnahme.
Lokal sind `check`, Migrationsprüfung und 47 Tests erfolgreich. Offen bleiben
Serverbereitstellung, Datenmigration, Backup/Restore, Browser-/PDF-Abnahme,
Upload-Sicherheit, Datenschutz und rechtliche Prüfung.

Aktualisierung 20.09.2026: Einzelbetrieb standardmäßig aktiviert; Organisationsauswahl und Mandantenanmeldung entfernt, zentrale Verwaltungsrouten und serverseitige Betreiberzuordnung umgesetzt. Bisherige Organisations-Fremdschlüssel bleiben als interne Datenreferenz bestehen. Lizenzgenerator und übrige Modulplanung werden dadurch nicht als erledigt erklärt.

Stand: 18.09.2026  
Status: Umsetzung begonnen; Online-Prüfungsgrundlagen lokal umgesetzt  
Grundlage: aktueller Projektcode und korrigierte Produktanforderung

## 1. Verbindliches Zielbild

**Eine vollständig installierte Anwendung, zwei freischaltbare Module und drei Nutzungsvarianten.**

LMS und Prüfungsmodul werden immer gemeinsam ausgeliefert, installiert und aktualisiert. Modulschalter beziehungsweise Seriennummer bestimmen, welche Funktionen nutzbar sind:

| Freischaltung | Nutzbare Funktionen |
| --- | --- |
| Nur LMS | Kurse, Lektionen, Lernmaterialien, Übungen und Lernpfade |
| Nur Prüfungen | Fragenkataloge, Prüfungen, Bewertung, Zertifikate und Prüfungspfade |
| LMS + Prüfungen | Beide Bereiche gleichzeitig, einschließlich Kursen mit zugeordneten Abschlussprüfungen |

Die Anwendung wird zum **Einzelsystem**: eine Installation, ein Betreiber, eine Benutzerverwaltung und eine Systemkonfiguration. Mandantenauswahl, Organisationsregistrierung und mandantenabhängige URL-Präfixe entfallen. Das sichtbare Produkt- und Navigationsdesign wird auf die Marke **ML Gruppe** und die Domain `ml-gruppe.de` ausgerichtet.

Zusätzlich entsteht ein **Seriennummerngenerator als eigenständige Anwendung** für den Lizenzherausgeber. Er ist kein Menüpunkt der Kundeninstallation und wird nicht mit dieser ausgeliefert.

Dieser Plan ersetzt die vorherige Annahme zweier getrennter Installationsprofile. Kombinierter Betrieb gehört ausdrücklich zum Umfang. Ein Modulwechsel benötigt weder Neuinstallation noch Schemawechsel und löscht keine Daten.

Aktueller Auftrag: Die Umsetzung erfolgt schrittweise und wird dokumentiert. Erledigt sind Rückwärtsnavigation, Antwortwiederherstellung, Vollbildstart, Autosave, serverseitige pausierbare Zeit, aktive Fragen, Operatorrechte und die Trainerfreigabe pro Teilnehmer. Generator, Modularisierung, PDF-Parameter, Inhaltsversionierung und Datenmigration bleiben weitere Arbeitspakete. Details und Prüfungen stehen in [UMSETZUNGSPROTOKOLL.md](UMSETZUNGSPROTOKOLL.md).

### Aktueller Fortschritt

| Teilbereich | Stand |
| --- | --- |
| Zurück/Weiter und Antwortwiederherstellung | Lokal umgesetzt und getestet |
| Vollbildstart und Reaktion auf Vollbild-/Sichtbarkeitsverlust | Lokal umgesetzt und getestet |
| Autosave und Heartbeat | Lokal umgesetzt und getestet |
| Serverseitige aktive Zeit, Pause und Fortsetzen | Lokal umgesetzt, Migration angewendet und getestet |
| Fragenstatus `aktiv` bei neuer Fragenauswahl | Operator-Oberfläche, Suche und Schalter lokal umgesetzt |
| Prüfungsoperator | Rolle, Gruppe, Katalog-/Parameterrechte, Suche und Aktivschalter lokal umgesetzt |
| Trainerfreigabe und PDF-Parameter | Trainerfreigabe, grundlegende PDF-Parameter und Versuchssnapshots lokal umgesetzt; vollständige Versionsverwaltung offen |

Für Zertifikatsprüfungen gelten zusätzlich die verbindlichen Anforderungen in Abschnitt 15: Rückwärtsnavigation, Vollbild, automatische Antwortsicherung, pausierbare Restzeit, Trainerfreigabe und die neue Rolle **Prüfungsoperator**. Sie gelten bei allein aktivem Prüfungsmodul und im kombinierten Betrieb.

## 2. Produktumfang und Modulgrenzen

| Funktion | Nur LMS | Nur Prüfungen | Beides |
| --- | --- | --- | --- |
| Benutzer, Anmeldung, Profil und Passwortreset | Ja | Ja | Ja |
| Betreiberdesign, Startseite, SMTP und Einladungen | Ja | Ja | Ja |
| Kurse, Kapitel, Lektionen, Video und Lernmaterial | Ja | Nein | Ja |
| Lektionsübungen und Mini-Quiz | Ja | Nein | Ja |
| Lernpfade mit Kursen | Ja | Nein | Ja |
| Prüfungspfade mit Prüfungen | Nein | Ja | Ja |
| Fragenkataloge, Import und formale Prüfungen | Nein | Ja | Ja |
| Manuelle Bewertung und Prüfer-Queue | Nein | Ja | Ja |
| Neue Prüfungs-/Lösungsbögen und Offline-Archive | Nein | Ja | Ja |
| Neue Prüfungszertifikate | Nein | Ja | Ja |
| Verbindung Kurs → Abschlussprüfung | Nein | Nein | Ja |
| Bereits ausgestellte Nachweise und Rechnungen | Lesender Bestandszugriff | Lesender Bestandszugriff | Lesender Bestandszugriff |
| Zahlungen | Optional für Kurse | Optional für Prüfungen | Optional für beide |
| Mandantenverwaltung | Nein | Nein | Nein |

Mini-Quiz und Übungen bleiben Teil des LMS. Formale Prüfungen mit Versuchen, Bewertung und Zertifikat gehören zum Prüfungsmodul. Neue Lernabschlussbescheinigungen und ein Pfad-Gesamtzertifikat wären gesonderte Erweiterungen.

Im kombinierten Betrieb sind Lernpfade und Prüfungspfade gleichzeitig verfügbar. Gemischte Pfade aus beliebigen Kurs- und Prüfungsschritten sind für Version 1 nicht vorausgesetzt; bestehende Kurs-Abschlussprüfungen bleiben jedoch nutzbar.

## 3. Relevanter Ist-Zustand

| Bereich | Aktueller Befund | Geplanter Umbau |
| --- | --- | --- |
| Installation | Beide Fach-Apps stehen bereits in `config/settings/base.py`; `config/urls.py` bindet beide ein. | Gemeinsame Installation beibehalten; zentrale Freischaltung ergänzen. |
| Mandanten | `Organisation`, `UserProfile`, Organisationsfilter, Tenant-Middleware und Session-Kontext bestimmen Rechte und Darstellung. | Betreiberkonfiguration und globale Rollen einführen; Mandantenlaufzeit ablösen. |
| Kurse | `Kurs` besitzt `angebotstyp` und einen optionalen Prüfungs-Fremdschlüssel. | Reine Prüfungsangebote ohne Kurs ermöglichen; optionale Verbindung für kombinierten Betrieb erhalten. |
| Lernpfade | `Lernpfad`, `LernpfadKurs` und `LernpfadEinschreibung` liegen in `apps/courses/models.py`. | Gemeinsame Pfadgrundlage mit Kurs- und Prüfungsschritten. |
| Fortschritt | Lernpfade zählen Kurse mit 100 % Lektionsfortschritt; `pflichtkurs` fließt derzeit nicht ein. Kurse ohne Lektionen haben 0 %. | Pflicht-/Wahlregeln festlegen; Prüfungsfortschritt aus final bestandenen Prüfungen ableiten. |
| Prüfungen | Prüfung, Anmeldung, Versuche, Antworten und Bewertung sind eigene Modelle. | Eigenständiges Prüfungsangebot und Prüfungspfad darauf aufbauen. |
| Zertifikate | Bezüge zu Prüfungsversuch und Kurseinschreibung; Aussteller und Design kommen aus Organisationen. | Betreiberdesign und dauerhafte Nachweisdaten; Bestandszugriff unabhängig vom Modulschalter. |
| Zahlungen | `Zahlung.kurs` ist verpflichtend. | Prüfungsgebühren unabhängig von Kursen ermöglichen, falls Zahlungen erhalten bleiben. |
| PDF | Erklärungen für alle Fragetypen, Bewertungsschema und neues Layout sind vorhanden. | Erhalten und regressionsprüfen. |

Vor Umsetzung werden alle Zugriffswege, Signale, Commands und Hintergrundaufgaben inventarisiert. Ältere Projektstatusdateien ersetzen diese Codeprüfung nicht.

## 4. Technische Architektur

### 4.1 Eine Installation und ein Datenbankschema

- Beide Module bleiben in `INSTALLED_APPS`; ihre Tabellen existieren auch bei nur einem aktiven Modul.
- Ein gemeinsamer Installer und gemeinsamer Upgradepfad liefern den vollständigen Funktionsumfang.
- Alle erforderlichen Migrationen laufen unabhängig von der Lizenz. Eine abgelaufene Lizenz verhindert keine Reparaturen oder Updates.
- Aktivieren gibt vorhandene Funktionen frei. Abschalten erhält Inhalte, Beziehungen und Historie; Reaktivierung stellt sie wieder bereit.
- Fachliche Entkopplung bleibt notwendig: Eine Einzelprüfung braucht keinen leeren Kurs, ein Lernkurs keine formale Prüfung.
- Sinnvolle Fremdschlüssel müssen nicht allein wegen der Lizenzierung entfernt werden. Getrennte Django-Migrationsgraphen sind kein Ziel mehr.

### 4.2 Verantwortlichkeiten

| Baustein | Verantwortung |
| --- | --- |
| Gemeinsamer Kern | Betreiberkonfiguration, Startseite, gemeinsame Dienste und Modulzustand |
| `licensing` (neu) | Lizenzimport, Prüfung, Status, Modulrechte, Aktivierungsseite und Änderungsprotokoll |
| `accounts` | Benutzer, globale Rollen, Kontofunktionen und Einladungen |
| `security` | Bestehende Verschlüsselung und Sicherheitsprüfungen |
| `paths` (neu oder herausgelöst) | Pfadstruktur, Teilnahme, Reihenfolge und Abschluss |
| `courses` | Lerninhalte, Einschreibung, Lernfortschritt und Lernpfade |
| `exams` | Prüfungsangebote, operatorverwaltete Fragen/Parameter, Trainerfreigaben, wiederaufnehmbare Versuche, Bewertung und Prüfungspfade |
| `certificates` | Nachweise, Nummern, PDF und öffentliche Verifikation |
| `payments` | Optionale Zahlungen, Rechnungen und fachbezogene Freischaltung |
| Separate Generatoranwendung | Lizenzen ausstellen, verwalten und exportieren |

Lizenzrecht und Benutzerberechtigung bleiben getrennt: Ein freigeschaltetes Modul erteilt einem Teilnehmer keine Trainer- oder Prüferrechte.

Bei Zahlungen wird ein vom Kurs unabhängiger Zahlungsgegenstand benötigt, wenn auch Prüfungen kostenpflichtig angeboten werden. Die jeweilige Fachfunktion übernimmt nach Zahlung die Freischaltung. Wiederholte Bestätigungen dürfen keine doppelten Zugänge oder Rechnungen erzeugen.

## 5. Zusammenspiel von Schaltern und Seriennummern

### 5.1 Empfohlene Regel

**Nutzbares Modul = gültiges Lizenzrecht UND eingeschaltetes Modul.**

- Lizenz LMS: LMS ist einschaltbar; Prüfungen lassen sich nicht zusätzlich aktivieren.
- Lizenz Prüfungen: Prüfungen sind einschaltbar; LMS bleibt gesperrt.
- Lizenz beides: beide gleichzeitig oder jeweils einzeln aktivierbar.
- Ohne gültige Lizenz bleiben Aktivierung, administrative Kontofunktionen und ausdrücklich erlaubte Bestands-/Wartungsfunktionen erreichbar; neue fachliche Nutzung wird nicht freigegeben.

Die Schalter dienen der betrieblichen Auswahl innerhalb der lizenzierten Rechte. Ein einfacher Schalter umgeht in der Kundenanwendung keine Seriennummer. Ob zusätzlich ein lizenzfreier interner Entwicklungs-/Demobetrieb gewünscht ist, bleibt eine ausdrückliche Entscheidung; kein stiller Fallback im Kundenbetrieb.

### 5.2 Zentrale Durchsetzung

- Eine gemeinsame Prüfung wie `require_module("lms")` oder `require_module("exams")` schützt den Zugang serverseitig.
- Sie gilt für Views, Formularaktionen, Services, Downloads, Django-Admin, fachliche Commands und Hintergrundaufgaben sowie gegebenenfalls APIs.
- Navigation und Dashboard zeigen aktive Bereiche. Direkte URLs gesperrter Funktionen geben keine geschützten Daten zurück.
- Auch ein Django-Superuser umgeht die Lizenz nicht automatisch. Wartungszugänge werden ausdrücklich begrenzt.
- Aktivierung funktioniert ohne Neuinstallation und ohne Prozessneustart. Versionierter Zustand beziehungsweise Cache-Invalidierung synchronisiert Web- und Workerprozesse.
- Prüf-/Lesefehler schalten keine zusätzlichen Rechte frei. Der Umgang mit einer bereits validierten Lizenz wird verbindlich definiert.
- Lizenzimport und Schalteränderungen sind ausschließlich für berechtigte Administratoren möglich und werden protokolliert.

### 5.3 Wechsel und laufender Betrieb

| Vorgang | Verhalten |
| --- | --- |
| Modul hinzukaufen | Neue Lizenz prüfen, Rechte atomar übernehmen, Modul einschalten; vorhandene Daten erhalten. |
| Modul ausschalten | Betroffene Vorgänge anzeigen, neue Starts sperren, laufende Vorgänge nach Abschlussregel behandeln. |
| Wieder einschalten | Vorhandene Inhalte und Fortschritte stehen wieder bereit. |
| Lizenz ersetzen | Erst vollständig prüfen; ungültige Eingabe beschädigt keine vorhandene gültige Aktivierung. |
| Rechte reduzieren oder Lizenz läuft ab | Keine neue Nutzung betroffener Funktionen; Daten bleiben erhalten. |

Empfehlung für einen eingeschränkten Abschlussbetrieb: Bereits begonnene Prüfungen dürfen mit ihrem verbleibenden aktiven Zeitbudget fortgesetzt und abgegeben sowie ihre offenen Bewertungen abgeschlossen werden. Technische Unterbrechungen verbrauchen dabei keine Prüfungszeit (Abschnitt 15). Neue Versuche sind gesperrt. Eingehende Zahlungsbestätigungen werden korrekt verbucht, ohne dadurch gesperrte Neunutzung freizugeben. Umfang und mögliche Frist sind vor Umsetzung festzulegen.

Ausgestellte Zertifikate, öffentliche Verifikation, gespeicherte Rechnungen und zulässige Datenexporte bleiben als abgegrenzter Bestandszugriff verfügbar. Dies ist keine allgemeine Freigabe des abgeschalteten Moduls.

## 6. Lizenzformat und Prüfung

### 6.1 Signierte Lizenz

Empfehlung: Die Lizenz enthält die Modulrechte und eine digitale Signatur. Sie wird als kopierbarer Aktivierungscode oder Lizenzdatei importiert. Eine kurze sichtbare Seriennummer identifiziert die Lizenz für Supportzwecke, ist allein aber kein Freischaltungsnachweis.

Der Generator signiert mit einem privaten Herausgeberschlüssel. Die Kundenanwendung enthält nur öffentliche Prüfschlüssel. Weder ein privater Signierschlüssel noch ein gemeinsames Ausstellergeheimnis wird an Kunden ausgeliefert.

Signaturverfahren, gepflegte Bibliothek und Datenserialisierung werden im technischen Entwurf festgelegt und mit gemeinsamen Testvektoren geprüft. Keine selbst entwickelte Kryptografie.

### 6.2 Vorgeschlagene Lizenzfelder

| Feld | Zweck |
| --- | --- |
| Formatversion und Produktkennung | Format und Produkt eindeutig prüfen |
| Lizenz-ID / Seriennummer | Eindeutige Zuordnung und Support |
| Revision | Änderungen und Erweiterungen nachvollziehen |
| Lizenznehmer | Anzeige und Zuordnung, möglichst wenige personenbezogene Angaben |
| Modulrechte | LMS, Prüfungen oder beides |
| Ausstellungszeitpunkt | Nachvollziehbarkeit |
| Gültig ab / gültig bis | Optional befristet oder unbefristet |
| Installationsbindung | Optional nach gewähltem Lizenzmodell |
| Schlüsselkennung | Zugelassenen öffentlichen Prüfschlüssel bestimmen |
| Signatur | Änderungen am Lizenzinhalt erkennen |

Benutzerlimits oder weitere Editionsgrenzen gehören nicht automatisch zum Umfang. Falls gewünscht, sind Zählweise und Überschreitungsverhalten gesondert festzulegen.

### 6.3 Validierung und Grenzen des Offline-Betriebs

- Vor Übernahme Größenbegrenzung, Format, Signatur, Produkt, bekannte Modulrechte, Gültigkeit und gegebenenfalls Installationsbindung prüfen.
- Unbekannte Formate und manipulierte Rechte ablehnen; Inhalt deterministisch serialisieren.
- Schlüsselrotation über Schlüsselkennung und vertrauenswürdige Softwareupdates vorsehen.
- Empfehlung für Version 1: lokale Offline-Prüfung ohne verpflichtenden Lizenzserver.
- Eine sehr kurze Seriennummer mit Online-Aktivierung benötigt dagegen einen zusätzlichen Aktivierungsdienst; dieser ist noch nicht beschlossen.
- Offline-Lizenzen lassen sich nicht sofort aus der Ferne widerrufen. Eine Sperrliste müsste importiert oder per Update verteilt werden; alternativ ist ein späterer Online-Dienst erforderlich.
- Eine Installations-ID allein verhindert keine Kopie einer vollständigen Installation. Gerätebindung, Aktivierungszählung und Serverumzug benötigen eigene Regeln.
- Befristete Offline-Lizenzen hängen von der lokalen Uhr ab. Bei vollständigem Zugriff auf Server und Programmcode besteht kein absoluter Manipulationsschutz; Ziel ist eine verlässliche reguläre Freischaltung.
- Das Ersetzen einer Lizenz durch ältere Revisionen und das Zurückspielen von Sicherungen müssen im technischen Entwurf ausdrücklich berücksichtigt werden.

## 7. Eigenständige Seriennummerngenerator-Anwendung

### 7.1 Zweck und Auslieferung

Der Generator ist eine separate interne Anwendung für ABoroSoft. Er läuft ohne LMS-Server und ohne Kundendatenbank.

Vorschlag: Windows-Desktop-Anwendung mit eigener EXE. Plattform und Oberflächentechnologie sind noch zu bestätigen. Eigener Quellbereich oder eigenes Repository, eigener Build und eigene Release-Artefakte. Bei gemeinsamem Repository schließen Kundeninstaller und Kundenpaket Generator, Ausstellerbestand und private Schlüssel ausdrücklich aus.

### 7.2 Mindestfunktionen

- Lizenznehmer und interne Referenz erfassen.
- Module wählen: **LMS**, **Prüfungen**, **beides**.
- Unbefristete Laufzeit oder optional Beginn/Ende einstellen.
- Optional eine Installationsanfrage oder Installations-ID übernehmen.
- Eindeutige Seriennummer erzeugen, Lizenz signieren und vor Export selbst verifizieren.
- Aktivierungscode kopieren und signierte Lizenzdatei exportieren.
- Ausgestellte Lizenzen lokal auflisten, suchen und ihre Rechte anzeigen.
- Verlängern oder erweitern: neue Revision ausstellen, vorherige Ausgabe nachvollziehbar erhalten.
- Ersetzung beziehungsweise interne Sperrung dokumentieren; klar anzeigen, dass dies offline keine sofortige Kundensperre bewirkt.
- Lizenzbestand sichern und wiederherstellen; Schlüssel getrennt sichern.

### 7.3 Schlüsselverwaltung

- Privater Schlüssel außerhalb von Quellcode und EXE, verschlüsselt gespeichert.
- Freigabe zum Signieren über Passwort oder geeigneten Betriebssystemspeicher.
- Bewusste initiale Schlüsselerzeugung; kein neuer Schlüssel bei jedem Programmstart oder als stiller Ersatz eines verlorenen Schlüssels.
- Keine Standardpasswörter oder privaten Schlüssel in Logs, Beispieldaten und Installern.
- Kundenausgaben enthalten nur Lizenzdaten und Signatur.
- Wiederherstellung von Bestand und Schlüssel auf einer zweiten autorisierten Maschine praktisch testen.
- Version 1 kann als Einzelplatzanwendung beginnen. Mehrere Aussteller mit zentraler Vergabe und Benutzerverwaltung wären ein zusätzliches Paket.

### 7.4 Liefergegenstände

1. Eigenständig startbare Generatoranwendung mit Build-/Paketierungsanleitung.
2. Dokumentiertes Lizenzformat und gemeinsame Testvektoren mit der ABoroLMS-Verifikation.
3. Anleitung für Ausstellung, Erweiterung, Verlängerung, Export und Wiederherstellung.
4. Getrennte Testschlüssel und Testlizenzen für alle drei Freischaltungen; keine produktiven Herausgeberschlüssel in Testdaten.

## 8. Lernpfade, Prüfungspfade und kombinierter Betrieb

### 8.1 Struktur

- Gemeinsame Grundlage: Titel, Slug, Beschreibung, Art (Lernen/Prüfung), Veröffentlichung und Version.
- Schritte: Reihenfolge, Pflicht-/Wahlstatus, Freischaltungsregel und genau ein zur Pfadart passender Kurs- oder Prüfungsbezug.
- Teilnahme: Benutzer, zugewiesene Pfadversion, Beginn und Abschlusszeitpunkt.
- LMS erlaubt Lernpfade; Prüfungen erlaubt Prüfungspfade; beide Rechte erlauben beide gleichzeitig.
- Fremdschlüssel und Servicevalidierung sichern die Bezüge; keine unkontrollierten freien Objekt-IDs.

### 8.2 Regeln

| Regel | Lernpfad | Prüfungspfad |
| --- | --- | --- |
| Schritt abgeschlossen | Lernabschluss des Kurses erreicht | Prüfung final bewertet und bestanden |
| Pfad abgeschlossen | Alle Pflichtkurse abgeschlossen | Alle Pflichtprüfungen bestanden |
| Noch offen | Kurs unvollständig | Laufender Versuch oder offene manuelle Bewertung |
| Wiederholung | Weiterlernen nach Zugriffsregeln | Neuer Versuch nach Versuchslimit und Freischaltung |

- Fortschritt = erledigte Pflichtschritte / alle Pflichtschritte; Wahlbestandteile separat anzeigen.
- Leere Pfade gelten nicht als abgeschlossen; Veröffentlichung benötigt mindestens einen Pflichtschritt.
- Kurse ohne abschließbare Lektionen werden nicht automatisch abgeschlossen.
- Pfadteilnahme ersetzt weder kostenpflichtigen Zugang noch erforderliche Prüfungsanmeldung.
- Ein späterer Fehlversuch hebt einen gültig bestandenen Schritt nicht automatisch auf.
- Vorhandene passende Abschlüsse sollen angerechnet werden; genaue Versionsregel festlegen.
- Strukturänderungen begonnener Pfade werden versioniert und verändern Abschlüsse nicht rückwirkend.
- Optional vorherigen Pflichtschritt voraussetzen; freie Abhängigkeitsgraphen zunächst nicht vorsehen.

### 8.3 Verbindung beider Module

Bei aktiven Modulen kann ein Kurs eine Abschlussprüfung anbieten. Lernfortschritt und Prüfungsergebnis werden getrennt angezeigt. Ob die Prüfung für einen Kursabschluss verpflichtend ist, wird ausdrücklich konfiguriert; Empfehlung: Lernabschluss und Prüfungszertifikat standardmäßig getrennt behandeln.

Wird das Prüfungsmodul ausgeschaltet, bleiben Zuordnung und Ergebnisse erhalten. Eine verpflichtende Prüfung wird nicht stillschweigend als bestanden behandelt; betroffene Abschlüsse sind blockiert. Die Administration zeigt diese Abhängigkeiten vor dem Ausschalten. Gleiches gilt für Prüfungen mit vorgeschalteter Kursvoraussetzung beim Abschalten des LMS.

## 9. Umbau zum Einzelsystem

### 9.1 Konfiguration und Rechte

- Organisationsangaben in eine zentrale Betreiberkonfiguration überführen: Name, Kontakt, Logo, Farben, Startseite, SMTP, E-Mail-Vorlagen, Zertifikatsdesign und gegebenenfalls Zahlungsdaten.
- Genau eine Konfiguration technisch sicherstellen; kein versteckter Standardmandant als Dauerlösung.
- Org-Admin wird Anwendungsadministrator, nicht automatisch Django-Superuser.
- Rollen: Administrator, Trainer, **Prüfungsoperator**, Prüfer und Lernender/Teilnehmer. Trainer sind keine Prüfungsautoren für Zertifikatsprüfungen mehr. Nur eine ausdrücklich zugewiesene Operatorrolle erlaubt dort Fragenpflege und Parametrierung (Abschnitt 15).
- Lizenz, Modulschalter und Benutzerrolle gemeinsam prüfen; Abschalten löscht keine Rollen.
- Organisationsfilter erst durch geprüfte Eigentums-, Rollen-, Teilnahme- und Freischaltungsregeln ersetzen.

### 9.2 URLs und Zugänge

- `/` wird die Betreiberstartseite; Login und Logout beziehen sich auf diese Installation.
- Bekannte alte URLs wie `/demo-organisation/` und Modulpräfixe gezielt auf die neuen Ziele weiterleiten.
- Die zentrale Startseite ist `/startseite/`; der Pagebuilder ist optional unter `/startseite/editor/` bzw. `/startseite/pagebuilder/` erreichbar. Organisations-Startseiten mit sichtbarem Slug werden im Einzelsystem nicht mehr verlinkt.
- Lernpfade und Prüfungspfade besitzen getrennte Wege: `/lernpfade/` und `/pruefungspfade/`.
- Kein pauschales Entfernen beliebiger erster URL-Segmente.
- Einladungen, Passwortreset, Zertifikatslinks und QR-Codes prüfen und erhalten.
- Alte POST-Endpunkte benötigen eine eigene Übergangsbehandlung; kein allgemeiner 301-Redirect für Prüfungsabgaben oder Zahlungen.
- Tenant-Middleware, `active_organisation_id`, Mandantenregistrierung und Mandantenwechsel nach Umstellung entfernen.

### 9.3 Betreiberdesign ML Gruppe

- Betreibername, Domain, Logo, Favicon, Primär-/Akzentfarben und Bildsprache werden zentral aus der Betreiberkonfiguration geladen.
- Die Anwendung verwendet im Einzelsystem keine sichtbaren ABoroLMS-Platzhalter mehr; interne Paket- und Migrationsnamen bleiben aus Kompatibilitätsgründen unverändert.
- Die Startseite erklärt das Angebot der ML Gruppe und führt direkt zu Lernpfaden, Prüfungspfaden und Anmeldung.
- Für die produktive Aktivierung werden Logo, Favicon und die verbindlichen Farbwerte aus dem Styleguide der ML Gruppe in `OrganisationDesign` hinterlegt. Aus `mlgruppe.de` wurden als Arbeitswerte Tiefblau `#0c437b`, Türkis `#2fb2bf`/`#058eab`, Anthrazit `#2b2e34` und die helle Fläche `#f9f9fb` übernommen.
- Für den ML-Produktivbetrieb wird `SINGLE_SYSTEM_MODE=True` verwendet. Historische Organisations-Fremdschlüssel bleiben bis zur geprüften Datenmigration intern erhalten; Demo-/Mehrmandantentests laufen weiterhin nur im expliziten Testmodus.

## 10. Datenmigration und Bestandsschutz

### 10.1 Vorbereitung

Ein lesendes Prüfkommando berichtet Organisationen, Benutzer/Rollen, Inhalte, Pfade, Kurs-Prüfungs-Verbindungen, laufende Versuche, offene Bewertungen, Zahlungen, Nachweise und Dateien. Produktion wird nicht mit der lokalen Demo gleichgesetzt.

Bei mehreren Organisationen wird eine Quelle je Zielinstallation ausgewählt. Andere Organisationen erhalten eigene Installationen oder bleiben im gesicherten Altsystem. Keine automatische Zusammenführung von Benutzern, Rechten oder Finanzdaten.

**Alle übernommenen Daten beider Module bleiben erhalten, unabhängig von der anfänglichen Freischaltung.** Spätere Aktivierung benötigt keine erneute Übernahme. Bestandskunden erhalten vor dem produktiven Wechsel eine passende Lizenz oder eine vereinbarte Übergangslizenz.

### 10.2 Reihenfolge

1. Datenbank, Medien und Verschlüsselungskonfiguration sichern; Rücksicherung testen.
2. Betreiber-, Lizenz- und Pfadstrukturen ergänzen; vorhandene Tabellen zunächst erhalten.
3. Rollen und ausgewählte Organisationsdaten übertragen; IDs, Kennwörter, Zertifikatscodes, Nummern und Dateizuordnungen möglichst bewahren.
4. Reine Prüfungsangebote vom künstlichen Kursbezug lösen; Kurs-Abschlussprüfungen erhalten.
5. Pfade zuordnen; mehrdeutige Bestände fachlich prüfen statt automatisch umdeuten.
6. Mengen, Beziehungen, Fortschritte, Ergebnisse, Geldbeträge, Dateiprüfsummen und Rechte vergleichen. Abweichungen durch neue Pflichtschrittberechnung berichten.
7. Alle drei Freischaltungen und Wechsel auf einer Produktionskopie prüfen.
8. Erst danach Mandantenfelder und überflüssige Laufzeitabhängigkeiten bereinigen.

Für Zertifikatsprüfungen kommt eine eigene Übernahmeprüfung hinzu: bisherige Trainer verlieren Katalog-/Parameterrechte, ohne automatisch Operator zu werden. Operatoren werden ausdrücklich benannt. Bestehende aktive Prüfungen gelten nicht automatisch als trainerfreigegeben. Das Feld `kein_zurueck` verliert für Zertifikatsprüfungen seine Wirkung. Der Wechsel auf pausierbare Zeitmessung erfolgt nach Abschluss laufender Altversuche oder über einen gesondert geprüften Übernahmeweg.

Gemeinsamer Migrationsgraph; historische Migrationen nicht einfach löschen oder umschreiben. Modulschalter führen niemals Migrationen oder Löschläufe aus.

### 10.3 Produktiver Wechsel und Rückweg

- Wartungsfenster und kontrollierter Schreibstopp; laufende Prüfungen beenden oder Wechsel verschieben.
- Finaler Snapshot, Übernahme, Aktivierung, Datenvergleich und Funktionstest vor Freigabe.
- Bis dahin Rückkehr auf alten Code, Datenbank und Medien möglich.
- Nach neuen Schreibvorgängen ist eine Rücksicherung allein nicht verlustfrei: neue Vorgänge abgleichen oder vorwärts korrigieren.
- Altsystem während vereinbarter Rückfallfrist geschützt und schreibgeschützt erhalten.
- Archivierte Bögen, Zertifikate und Rechnungen nicht neu berechnen oder überschreiben.
- Demofragen zum alten Mandantenmodell in einer neuen Inhaltsversion aktualisieren, keine historischen Versuche umdeuten.

## 11. Umsetzungspakete

| Phase | Ergebnis | Abnahme |
| --- | --- | --- |
| 0. Details festlegen | Lizenz-/Schalterregel, Generatorplattform, Laufzeit und Datenquelle. | Abschnitt 13 geklärt. |
| 1. Bestandsaufnahme | Zugriffs-/Abhängigkeitsinventar, Datenbericht und Sicherungsprobe. | Modulzugänge und Bestandsabhängigkeiten bekannt. |
| 2. Lizenzformat | Signaturverfahren, Testvektoren, Statusmodell und Wechselregeln. | Gemeinsame prüfbare Grundlage für Generator und Verifikation. |
| 3. Generator und Lizenzprüfung | Separate Anwendung sowie Import/Verifikation in ABoroLMS. | Gültige Lizenzen erzeugen exakt die vorgesehenen Rechte; manipulierte scheitern. |
| 4. Modulschalter | Zentrale Guards, Administration, Navigation und Prozesssynchronisierung. | Alle drei Zustände ohne Neuinstallation nutzbar. |
| 5. Fachmodule und Pfade | Prüfungsangebote, Pfadkern, beide Pfadarten und optionale Verbindungen. | Prüfung ohne Kurs; Lernen ohne Prüfungszwang; kombinierter Betrieb erhalten. |
| 5a. Prüfungsrollen und Katalog | Prüfungsoperator, serverseitige Katalog-/Parameterrechte, Fragen-Suche sowie Aktiv/Inaktiv-Schalter sind lokal umgesetzt. Inhaltsversionierung und CSV-Vorschau folgen. | Erledigt: Trainer können diese Änderungswege nicht mehr nutzen; offen bleiben Versionierung und CSV-Vorschau. |
| 5b. Freigabe und PDF | Trainerfreigabe für zugeordnete Teilnehmer, unveränderliche Prüfungsversion und zusammengehörige PDF-Fassungen. | Trainerfreigabe, PDF-Parameter und ein unveränderlicher Snapshot je Versuch lokal umgesetzt. Operator-Release und vollständige PDF-Verknüpfung folgen. |
| 5c. Online-Prüfungsablauf | Vollbild, Zurück/Weiter, Antwortsicherung, Restzeitanzeige, Unterbrechung und Fortsetzen. | Erster technischer Teil lokal umgesetzt und getestet; Browser-/Geräteabbruch, echte Kioskprüfung und vollständige Inhaltsversionierung bleiben zu verifizieren. |
| 6. Einzelbetrieb | Betreiberkonfiguration, Rollen, URLs, Einladungen und Login/Logout. | Keine Mandantenverwaltung oder versteckte Mandantenauswahl. |
| 7. Migrationsprobe und Paketierung | Produktionskopie umziehen, beide Anwendungen paketieren, Wiederherstellung und Handbücher. | Datenvergleich erfolgreich; Kundenpaket ohne Generator/Signierschlüssel. |
| 8. Produktiver Wechsel | Vereinbartes Wartungsfenster, finaler Umzug und Beobachtung. | Freigegebenes Einzelsystem mit dokumentiertem Rückweg. |

Kleine abnehmbare Änderungen statt vollständigem Neubau. Der Generator ist ein eigener Liefergegenstand innerhalb dieses Vorhabens.

## 12. Tests und Gesamtabnahme

### Lizenz und Generator

- Lizenzen für LMS, Prüfungen und beides; unbefristet sowie gegebenenfalls befristet.
- Falsche Signatur, manipulierte Rechte, falsches Produkt, unbekannter Schlüssel und ungültiges Format ablehnen.
- Falls aktiviert: Ablauf, zukünftiger Gültigkeitsbeginn und falsche Installationsbindung prüfen.
- Upgrade, Verlängerung, Ersatz und Downgrade prüfen; fehlerhafter Import erhält die bisherige gültige Aktivierung.
- Testlizenzen in einer frisch installierten Kundenanwendung tatsächlich importieren und nutzen.
- Generator ohne LMS starten; Export, Archiv und Wiederherstellung auf zweiter autorisierter Maschine testen.
- Kundenartefakte auf Generatorbestandteile, private Schlüssel und Entwicklungs-Bypässe prüfen.

### Modulgrenzen und laufende Vorgänge

- Alle drei Zustände nutzen dieselbe Software und dasselbe Schema.
- Schalter überschreiten keine Lizenzrechte; Rollenprüfung bleibt wirksam.
- Direkte URLs, Admin, Downloads, Commands und fachliche Hintergrundaufgaben umgehen Sperren nicht.
- Web-/Workerprozesse übernehmen Änderungen konsistent.
- Abschalten, Ablauf und Reaktivierung mit laufenden Versuchen, offenen Bewertungen und Zahlungen testen.
- Daten bleiben erhalten; erlaubte Bestands-/Abschlusszugriffe bleiben eng begrenzt.

### Fachliche Abläufe und Migration

- LMS: anmelden → Lernpfad → Kurs → Pflichtkurse abschließen → Pfadabschluss.
- Prüfungen: anmelden/einladen → Prüfungspfad → Prüfung → Bewertung → Zertifikat/Pfadabschluss.
- Beides: parallele Pfade und Kurs-Abschlussprüfung einschließlich Sperrabhängigkeiten.
- Teilnehmer sehen keine fremden Ergebnisse oder Lösungen.
- Rollen, Fortschritte, Versuche, Nachweise, Rechnungen und Dateien gegen Übernahmebericht prüfen.
- Verifikation, alte Links, Login/Logout und Verschlüsselung bleiben funktionsfähig.
- Prüfungs-/Lösungsbögen und Zertifikats-PDFs erneut visuell kontrollieren.
- Neuinstallation und Upgrade auf den unterstützten Datenbanken testen.
- Die zusätzliche Abnahme für Zertifikatsprüfungen aus Abschnitt 15.9 vollständig durchführen; insbesondere echte Browser-/Verbindungsabbrüche und negative Rollenprüfungen.

**Gesamtabnahme:** Eine Einzelinstallation enthält immer beide Module. Lizenz und Schalter erlauben nur LMS, nur Prüfungen oder beides. Beide Pfadarten bleiben erhalten. Der eigenständige Generator stellt die Lizenzen aus und gehört nicht zur Kundeninstallation.

## 13. Noch festzulegende Details

Gemeinsame Installation, drei Freischaltungen, Einzelbetrieb und separater Generator sind bereits festgelegt und stehen nicht erneut zur Auswahl.

Ebenso festgelegt sind für Zertifikatsprüfungen: immer verfügbare Zurück-Navigation, verpflichtender Vollbildmodus, Antwortsicherung und Zeitpause bei Unterbrechung, Restzeittimer, Trainerfreigabe sowie exklusive Katalog-/Parameterverwaltung durch Prüfungsoperatoren. Offen sind nur die unten genannten Detailregeln, nicht diese Anforderungen selbst.

| Offener Punkt | Empfehlung / Ausgangspunkt |
| --- | --- |
| Verhältnis Schalter zu Seriennummer | Schalter aktivieren nur lizenzierte Module; internen lizenzfreien Betrieb ausdrücklich entscheiden. |
| Generatorplattform | Windows-Desktop-Anwendung mit EXE; Technologie nach Buildumgebung festlegen. |
| Aktivierung | Offline signierter Code plus Lizenzdatei; kurze Seriennummer als Referenz. Online-Dienst nur bei Bedarf. |
| Laufzeit | Unbefristet als Grundlage; optionale Befristung für Test-/Zeitlizenzen. |
| Bindung und Umzug | Kunde, Installation oder Domain festlegen; geplanter Umzug mit Ersatzlizenz. |
| Ablauf und offene Vorgänge | Begrenzter Abschlussbetrieb und lesende Nachweise; Regeln und Fristen bestätigen. |
| Zahlungen und Limits | Umfang ausdrücklich entscheiden; keine zusätzlichen Editionsgrenzen stillschweigend einführen. |
| Datenquelle | Eine ausgewählte Organisation je Zielinstallation; Daten beider Module erhalten. |
| Pfad-/Kursabschlüsse | Pflichtschritte bestimmen Pfadabschluss; Lernabschluss und Prüfungszertifikat standardmäßig getrennt. |
| Trainerfreigabe | Empfehlung: pro Durchführung und zugeordneten Teilnehmern; genaue Gültigkeit und Wiederholungsregel festlegen. |
| Wiederaufnahme | Empfehlung: derselbe freigegebene Versuch wird ohne erneute Trainerfreigabe fortgesetzt; manuelle Sperren bleiben wirksam. |
| Vollbildumgebung | Unterstützte Browser/Geräte definieren; ein verriegelter Prüfungsbrowser wäre ein zusätzliches Paket. |
| PDF-Vorgaben | Konkrete Operatoroptionen festlegen, etwa Layout, Antwortplatz, Auswahlregeln und Metadaten. |

## 14. Nächster Schritt

Offene Details festhalten, anschließend Bestandsaufnahme und Lizenzformat spezifizieren. Dabei den neuen Zertifikatsprüfungsablauf aus Abschnitt 15 bereits berücksichtigen. Danach Generator und Verifikation sowie die in Abschnitt 11 geordneten Prüfungs- und Einzelbetriebspakete umsetzen.

Die Umsetzung von Phase 5c ist teilweise abgeschlossen: Rückwärtsnavigation, Vollbildstart, Autosave, Heartbeat, serverseitig pausierbare Zeit und die Trainerfreigabe pro Teilnehmer sind lokal umgesetzt und getestet. Dies ersetzt nicht die weiterhin erforderlichen Detailentscheidungen für Lizenzierung, Prüfungsrollen, PDF-Parameter und vollständige Inhaltsversionierung. Siehe [Umsetzungsprotokoll](UMSETZUNGSPROTOKOLL.md).

## 15. Verbindlicher Ablauf für Zertifikatsprüfungen

Diese Anforderungen ergänzen das Gesamtvorhaben. Sie gelten für Zertifikatsprüfungen online und, soweit betroffen, für die zugehörigen PDF-Fassungen. Die Bearbeitung von normalen Lektionsübungen im LMS bleibt eine Trainerfunktion. Die fachliche Kennzeichnung einer Zertifikatsprüfung muss serverseitig eindeutig sein; ein Trainer darf die Regeln nicht durch Umbenennen oder Ändern des Angebotstyps umgehen.

### 15.1 Rollen und Zuständigkeiten

Neue Rolle: **Prüfungsoperator**, vorgeschlagener interner Schlüssel `exam_operator`.

| Aktion bei Zertifikatsprüfungen | Trainer | Prüfungsoperator | Prüfer | Prüfling |
| --- | --- | --- | --- | --- |
| Fragenkatalog erstellen, ändern oder importieren | Nein | Ja | Nein | Nein |
| Fragen manuell anlegen oder per CSV einfügen | Nein | Ja | Nein | Nein |
| Fragen suchen, fachlich bearbeiten, aktivieren/deaktivieren | Nein | Ja | Nein | Nein |
| Bestehensgrenze, Fragenzahl und sonstige Prüfungsparameter einstellen | Nein | Ja | Nein | Nein |
| PDF-Parameter und Auswahlregeln festlegen | Nein | Ja | Nein | Nein |
| Vorgegebene Prüfung für zugeordnete Teilnehmer freigeben | Ja | Nicht automatisch | Nein | Nein |
| Prüflings-PDF und passende Lösungsfassung erzeugen | Ja, nach festen Vorgaben | Ja, zur Vorbereitung/Prüfung der Vorgaben | Nein, sofern nicht gesondert berechtigt | Nein |
| Freitext/Szenario bewerten | Nur mit Prüferrolle | Nur mit Prüferrolle | Ja | Nein |
| Freigegebene Online-Prüfung bearbeiten und fortsetzen | Nur als berechtigter Teilnehmer | Nur als berechtigter Teilnehmer | Nur als berechtigter Teilnehmer | Ja |

Trainer erhalten im Zertifikatsbereich eine Durchführungsansicht: zugeordnete Prüfungen, Teilnehmerfreigabe sowie Erzeugung/Download der beiden PDF-Fassungen. Es gibt dort keinen Frageneditor, CSV-Import und keine editierbaren Prüfungs- oder PDF-Einstellungen.

Die Rollen sind getrennt. Zusätzliche Rechte entstehen nur durch ausdrücklich zugewiesene Zusatzrollen. Wer Trainer und Operator ist, handelt bei Änderungen mit seiner Operatorberechtigung; die Trainerrolle allein genügt niemals. Auch Administrationsoberflächen und direkte POST-Aufrufe müssen dies durchsetzen. Ein technischer Superuser-Bypass in den bisherigen Mixins darf die fachliche Operatorpflicht nicht automatisch aufheben. Rollenvergabe und fachliche Änderungen werden protokolliert.

### 15.2 Fragenkatalog, Suche und Aktivstatus

- Nur Prüfungsoperatoren erstellen Zertifikatskataloge, pflegen Fragen und importieren CSV-Dateien.
- Suche nach Fragetext und stabiler Fragen-ID; Filter nach Katalog, Thema/Tag, Fragetyp, Schwierigkeit und Aktivstatus. Optional auch Erklärungen/Bewertungshinweise durchsuchen.
- Neue Fragen erhalten einen eindeutigen Status. Empfehlung: zunächst Entwurf/inaktiv, Aktivierung durch den Operator nach Prüfung.
- Aktivieren/deaktivieren statt Löschen bereits verwendeter Fragen. Änderungszeitpunkt und bearbeitender Operator bleiben nachvollziehbar.
- Nur aktive, für die Prüfungsversion freigegebene Fragen dürfen bei neuen Online-Versuchen und neuen PDF-Bögen gezogen werden.
- Anzahl und Themenquoten werden vor Freigabe und bei jeder neuen Ziehung geprüft. Bei zu wenigen aktiven Fragen: verständliche Meldung, keine heimliche Reduzierung und kein Rückgriff auf deaktivierte Fragen.
- Änderungen an Text, Antworten, korrekten Lösungen, Punkten, Erklärungen und Bewertungsschemata werden versioniert. Begonnene Versuche und vorhandene PDF-Archive behalten ihre ursprünglichen Inhalte.
- Deaktivierung verhindert neue Ziehungen, ändert aber keinen laufenden Versuch und kein archiviertes Dokument. Ein fachlich notwendiger Rückruf ist ein gesonderter protokollierter Vorgang.
- CSV-Import mit Vorschau, Pflichtfeld-/Fragetypprüfung, nachvollziehbaren Zeilenfehlern und definierter Dublettenregel. Keine unbemerkte Überschreibung verwendeter Fragen.

### 15.3 Prüfungs- und PDF-Parameter

Nur der Prüfungsoperator stellt unter anderem ein:

- Bestehensgrenze, Fragenzahl, Punkte-/Bewertungsregeln und Themenquoten.
- Zeitbudget, erlaubte Versuche, Fragen-/Antwortreihenfolge und zulässige Voraussetzungen.
- Verwendeten Katalog und veröffentlichte Prüfungsversion.
- Fachliche PDF-Auswahlregeln und PDF-Vorgaben: beispielsweise Titel-/Kopfdaten, Layout, Antwortplatz, Metadaten und Darstellung der Lösungen.

Die verpflichtenden Anforderungen sind dabei nicht abschaltbar: Ein Operator darf für Zertifikatsprüfungen weder Zurück-Navigation noch Antwortsicherung deaktivieren oder die unterbrechbare Zeitmessung umgehen.

Der Trainer kann die beiden Fassungen erzeugen, aber keine Parameter über Formulare, URL-Parameter oder manipulierte Requests überschreiben. Prüflings- und Lösungsbogen entstehen aus derselben einmal gezogenen Fragenmenge, identischer Fragen-/Antwortreihenfolge und derselben Parameterrevision. Beide tragen eine gemeinsame Bogenkennung und werden zusammen archiviert. Ein erneuter Download lädt das Archiv statt Fragen erneut zu ziehen.

Die Lösungsfassung enthält korrekte Antworten, Erklärungen aller Fragetypen und die vorgesehenen Bewertungsschemata. Die Prüflingsfassung enthält diese Informationen nicht. Das zuletzt erstellte PDF-Layout bleibt erhalten; Gestaltungsvorgaben werden nur durch Operatoren geändert.

### 15.4 Trainerfreigabe vor Prüfungsstart

Eine veröffentlichte oder aktive Prüfung ist **noch keine Startfreigabe**. Anmeldung, bezahlter Zugang und Pfadteilnahme ersetzen die Freigabe durch den Trainer nicht.

Empfohlenes Modell: eine Durchführung mit Prüfungsversion und zugeordneten Teilnehmern. Die Freigabe erfasst mindestens Prüfung/Durchführung, Teilnehmer, freigebenden Trainer, Zeitpunkt und Status; optional einen Gültigkeitszeitraum. Gruppenfreigaben werden auf die zugeordneten Teilnehmer begrenzt.

Vor jeder Neuanlage eines Versuchs werden serverseitig geprüft:

1. Prüfungsmodul nutzbar und Teilnehmer authentifiziert.
2. Anmeldung/Zugang sowie gegebenenfalls Zahlung und Voraussetzungen vorhanden.
3. Trainerfreigabe für genau diesen Teilnehmer und diese Prüfungsversion vorhanden.
4. Versuchslimit nicht erreicht und kein fortsetzbarer Versuch vorhanden.
5. Genügend gültige aktive Fragen vorhanden und Prüfungseinstellungen vollständig.
6. Vollbildbereitschaft der Oberfläche; erst der bestätigte Start aktiviert das Zeitbudget.

Mehrfachklicks oder parallele Anfragen dürfen keine Doppelversuche erzeugen. Bei vorhandenem laufenden/pausierten Versuch wird dieser angeboten statt ein weiterer angelegt.

Empfehlung: Wiederaufnahme desselben unterbrochenen Versuchs braucht keine neue Freigabe. Eine manuelle Sperre bleibt wirksam; die Restzeit bleibt dabei eingefroren. Ein neuer Wiederholungsversuch erfordert eine dafür gültige Freigabe. Bereits begonnene Versuche werden durch einen abgelaufenen Startzeitraum nicht automatisch ungültig.

### 15.5 Prüfungsoberfläche, Zurück und Vollbild

- Während einer laufenden Prüfung sind **Zurück**, **Weiter**, Fragenposition, Speicherstatus und Restzeit sichtbar.
- Zurück führt innerhalb der Prüfung zur vorherigen Frage, nicht zur vorherigen Browserseite. Vor dem Wechsel wird der aktuelle Stand gesichert.
- Auf der ersten Frage bleibt der Button sichtbar und führt zur Prüfungsübersicht desselben Versuchs; kein unbestätigtes Verlassen und kein Zurücksetzen.
- Bereits beantwortete Fragen können vor endgültiger Abgabe erneut geöffnet und geändert werden. Alle Fragetypen werden korrekt vorausgefüllt, einschließlich SC/MC, Wahr/Falsch und Zuordnungen.
- Das vorhandene `kein_zurueck` wird für Zertifikatsprüfungen entfernt beziehungsweise verbindlich ignoriert, inklusive serverseitiger Beschränkungen.
- Start und Fortsetzen erfolgen über einen bewussten Klick, der Vollbild anfordert. Wird Vollbild abgelehnt oder nicht unterstützt, beginnt keine Prüfungszeit; es erscheint eine verständliche Meldung.
- Dedizierte Prüfungsansicht ohne normale Website-Navigation und unnötige Links. Fragenwechsel erfolgen innerhalb derselben Seite, damit Vollbild nicht durch jeden Seitenwechsel verloren geht.
- Beim Verlassen von Vollbild oder bei einer tatsächlichen Unterbrechung: Eingaben sperren, Inhalt abdecken, Antworten soweit erreichbar sichern und den Versuch pausieren. Fortsetzen erfordert erneut bestätigtes Vollbild.
- Kein endgültiger Fehlversuch allein wegen eines versehentlichen Vollbildausstiegs oder technischen Abbruchs. Unterbrechungen werden protokolliert.
- Endgültige Abgabe ist eine eigene, bestätigte Aktion mit Hinweis auf unbeantwortete Fragen; Zurück/Weiter geben nicht versehentlich ab.

**Browsergrenze:** Web-Vollbild kann vom Benutzer beendet werden und ist keine vollständige Sperre des Betriebssystems oder anderer Anwendungen. Die Oberfläche kann dieses Verhalten erkennen und reagieren, aber keinen normalen Browser in einen manipulationssicheren Prüfungsrechner verwandeln. Grundlage: [WHATWG Fullscreen Standard](https://fullscreen.spec.whatwg.org/). Ein gesonderter verriegelter Prüfungsbrowser oder verwalteter Kiosk wäre nur bei weitergehendem Bedarf ein eigenes Paket.

### 15.6 Automatische und dauerhafte Antwortsicherung

- SC/MC/Wahr-Falsch und Zuordnungen bei Änderung speichern; Freitext/Szenario fortlaufend nach kurzer Eingabepause sowie spätestens vor Navigation sichern.
- Serverbestätigter Datenbankstand ist maßgeblich. Anzeige unterscheidet „Speichert“, „Gespeichert“ und „Verbindung unterbrochen“; „Gespeichert“ erscheint erst nach Bestätigung.
- Entwurfsantworten sind unabhängig von endgültiger Abgabe. Leeren einer Antwort wird ebenfalls gespeichert.
- Revisionsnummern je Antwort und eindeutige Request-IDs verhindern, dass verspätete Requests einen neueren Stand überschreiben. Wiederholte Übertragung ist idempotent.
- Jeder Schreibzugriff prüft Eigentümer, Versuch, tatsächliche Fragenzugehörigkeit, erlaubte Antwortoptionen, Zustand und verbleibendes aktives Zeitbudget. Keine Lösungen an den Browser übertragen.
- Ein lokaler Wiederherstellungsentwurf kann die Lücke bei kurzzeitigem Netzausfall verkleinern. Er ist benutzer-/versuchsgebunden, zeitlich begrenzt und nach Abgabe/Abmeldung zu entfernen; kein ungeschützter dauerhafter Bestand auf gemeinsam genutzten Rechnern.
- Bei Rückkehr werden lokale Entwürfe gegen bestätigte Revisionen abgeglichen, nicht blind über neuere Serverdaten geschrieben. Nach endgültiger Abgabe keine nachträgliche Antwortänderung.
- Bei fehlender Serververbindung nicht unbemerkt weiterarbeiten lassen: Bearbeitung pausieren und Inhalt sperren, bis die Sitzung wiederhergestellt ist.

**Zuverlässigkeitsgrenze:** Nach einem harten Browser-/Geräteabbruch kann ein noch nicht übertragenes letztes Eingabezeichen nicht garantiert auf dem Server vorhanden sein. Verbindlich erhalten bleiben sämtliche als gespeichert bestätigten Antworten; kurze Speicherintervalle und Wiederherstellungsentwürfe minimieren die verbleibende Lücke. Abschluss-/Unload-Ereignisse sind nicht zuverlässig und dürfen nicht die einzige Sicherung sein. Grundlage: [Chrome Page Lifecycle API](https://developer.chrome.com/docs/web-platform/page-lifecycle-api).

### 15.7 Restzeit, Unterbrechung und Fortsetzen

Die heutige Rechnung `gestartet_am + zeitlimit` wird für Zertifikatsprüfungen durch ein **serverseitig geführtes aktives Zeitbudget** ersetzt. Die Pause zählt nicht zur Prüfungszeit.

Vorgeschlagene Zustände:

`BEREIT → LAUFEND ↔ PAUSIERT → ABGEGEBEN → BEWERTUNG_AUSSTEHEND / ABGESCHLOSSEN`

Zeitbudget verbraucht: einmalig abgeben/finalisieren und vorhandene Antworten bewerten; offene manuelle Bewertungen bleiben möglich. Technisch unterbrochen bedeutet nicht `ABGEBROCHEN` oder `ABGELAUFEN`.

Zusätzlich speichern: Zeitbudget beim Start, verbrauchte aktive Zeit, letzte bestätigte Aktivität, Beginn der aktuellen aktiven Phase, Pausenereignisse, aktuelle Fragenposition, Sitzungsgeneration und Freigabebezug. Fragen-, Antwortreihenfolge und Inhalte werden pro Versuch fixiert und bei Rückkehr nicht neu gemischt.

**Erkennung und Zeitabrechnung:**

- Browser sendet regelmäßig ein Lebenszeichen; Speicheranfragen können zugleich Aktivität bestätigen. Ausgangspunkt für Tests: alle 5 Sekunden, Ausfallerkennung nach 15 Sekunden. Das sind technische Vorschlagswerte, keine fertige Produktvorgabe.
- Bei erkanntem Vollbildausstieg beziehungsweise Verbindungsverlust sperrt der Browser sofort die Bearbeitung. Der Server pausiert nach gültiger Meldung oder ausbleibenden Lebenszeichen.
- Ein Browserabsturz liefert häufig keine letzte Meldung. Deshalb setzt der Server die Pause bei erkennbarer Verbindungslücke auf den letzten bestätigten Aktivitätszeitpunkt zurück, statt die gesamte Ausfallzeit abzuziehen. Die Unsicherheit wird durch das Lebenszeichenintervall begrenzt und dokumentiert.
- Serverseitige Zeitstempel und konsistente Zustandsübergänge sind maßgeblich; vom Client frei übermittelte Restzeit oder rückdatierte Pausen werden nicht übernommen. Doppelte Lebenszeichen, verspätete Requests und wiederholtes Fortsetzen dürfen weder Zeit verdoppeln noch Budget erhöhen.
- Eine vermeintliche Fristüberschreitung bei ausgebliebenem Lebenszeichen darf nicht vor der Unterbrechungsprüfung zur endgültigen Abgabe führen. Während einer bestätigten aktiven Sitzung wird Null hingegen verbindlich serverseitig durchgesetzt.
- Keine einzige JavaScript-Uhr als Wahrheit: Browser zeigt laufenden Countdown aus Serverbudget und synchronisiert regelmäßig. Bei Pause erscheint „Pausiert“ mit eingefrorener Restzeit, nach Wiederaufnahme läuft genau dieses Budget weiter.
- Beispiel: Nach 8 Minuten aktiver Bearbeitung einer 25-Minuten-Prüfung bleiben nach einem 10-minütigen Browserausfall weiterhin ungefähr 17 Minuten, innerhalb der dokumentierten Erkennungsgenauigkeit.

**Wiederaufnahme:** Nach erneuter Anmeldung den vorhandenen Versuch anbieten, Bestandsantworten und feste Reihenfolge laden, Vollbild erneut anfordern und erst nach bestätigter Fortsetzung Zeit berechnen. Laden der Übersicht oder Wartezeit auf Wiederaufnahme verbraucht keine Prüfungszeit. Es entsteht weder ein zusätzlicher Versuch noch eine neue Zufallsauswahl.

**Mehrere Tabs/Geräte:** Nur eine aktive Bearbeitungssitzung pro Versuch. Übernahme erneuert eine serverseitige Sitzungsgeneration und macht alte Schreib-/Zeitmeldungen ungültig. Reload, parallele Requests, Serverneustart und Workerwechsel müssen dieselben gespeicherten Zustände verwenden.

Eine technische Störung und ein absichtlich geschlossener Browser sind nicht immer unterscheidbar. Gemäß Anforderung wird in beiden Fällen die Zeit geschützt und der Vorfall protokolliert, nicht automatisch durchgefallen gewertet. Eine beaufsichtigte Wiederfreigabe bei auffälligen Unterbrechungen wäre eine ausdrücklich zu vereinbarende Zusatzregel.

### 15.8 Konkrete Änderungen am bestehenden Code

| Bereich | Geplante Arbeit |
| --- | --- |
| `apps/accounts/models.py`, Rollenanlage und Mixins | Prüfungsoperator ist ergänzt und wird als Gruppe angelegt; Katalog-/Parameter-Guards sind umgesetzt, weitere globale Guards folgen. |
| `apps/exams/models.py` | Fragenaktivstatus, pausierbarer Versuch und `PruefungsFreigabe` sind umgesetzt; Inhalts-/Parameterrevisionen und Antwortrevisionen folgen. |
| `apps/exams/forms.py`, `views.py`, `urls.py` | Operatoroberfläche und Suchfilter; Trainerdurchführung; geschützte Start-/Speicher-/Pause-/Fortsetzen-/Abgabewege. |
| `apps/exams/services.py` | Aktive Fragenauswahl und autoritative pausierbare Zeitrechnung sind umgesetzt; unveränderliche Versuchsdaten, idempotente Revisionen und vollständige Finalisierung folgen. |
| `templates/exams/take.html` und Prüfungs-JavaScript | Vollbildstart, Rückwärtsnavigation, Vorbelegung, Autosave, Heartbeat und Countdown sind umgesetzt; Speicherstatusanzeige und Browser-End-to-End-Prüfung folgen. |
| PDF-Service und Offline-Archiv | Operatorparameter festhalten, Traineränderungen verhindern, zusammengehörige Bögen reproduzierbar archivieren. |
| Tests und Bestandsmigration | Rollenentzug ohne automatische Operatorbeförderung, explizite Trainerfreigaben und Übergang laufender Altversuche. |

Aktualisierter Stand: `take.html` besitzt Zurück-Navigation, Vollbildstart, Autosave, Heartbeat, Countdown und Antwortwiederherstellung. Antworten werden bei Änderungen und vor Zurück/Weiter gespeichert. Die aktive Prüfungszeit wird serverseitig geführt, bei Vollbild-/Sichtbarkeitsverlust pausiert und beim Fortsetzen wieder aufgenommen. Antwortoptionen werden pro Versuch/Frage reproduzierbar angeordnet. Die Rolle `exam_operator` ist global angelegt und getestet; Katalog-/Parameter-Guards, Suche, Aktivschalter und konkrete Trainerfreigaben mit Widerruf sind umgesetzt. Vollständige Inhaltssnapshots, eine explizite Speicherstatusanzeige, echte Browser-/Geräteabbruchszenarien und Operator-PDF-Parameter sind noch offen. Trainer können Katalog-/Parameteränderungen nicht mehr nutzen, behalten aber Prüfungsdurchführung und PDF-/Statistikzugriff.

### 15.9 Zusätzliche Abnahmefälle

1. Trainer kann Zertifikatskatalog weder über Oberfläche noch direkte URL, POST, Import oder Admin ändern; Operator kann suchen, bearbeiten und aktiv/inaktiv setzen.
2. Trainer kann Bestehensgrenze, Fragenzahl, Zeitbudget, Auswahlregeln und PDF-Parameter nicht überschreiben. Normale LMS-Übungen bleiben bearbeitbar.
3. Angemeldeter und gegebenenfalls zahlender Prüfling kann ohne passende Trainerfreigabe keinen Versuch starten; parallele Startanfragen erzeugen höchstens einen Versuch.
4. Zurück funktioniert nach jeder Frage, auch auf der letzten. Auf der ersten führt es zur internen Übersicht; vorhandene Antworten aller Fragetypen bleiben sichtbar und änderbar.
5. Start ohne bestätigtes Vollbild verbraucht keine Zeit. Vollbildausstieg führt zur Pause und verdeckt Inhalte; erneutes Vollbild erlaubt Fortsetzung.
6. Browserprozess hart beenden, Tab schließen, Reload, Netzausfall und Geräte-Ruhezustand testen. Bestätigte Antworten bleiben erhalten; Ausfallzeit wird nicht vom Budget abgezogen.
7. Nach 8 aktiven Minuten und 10 Minuten Unterbrechung bleiben bei 25 Minuten Budget ungefähr 17 Minuten gemäß festgelegter Genauigkeit. Wiederholte Pausen erhöhen das Budget nicht.
8. Countdown entspricht Serverzeit; manipulierte Clientzeit, doppelte Lebenszeichen, alte Tabs und verzögerte Speicherrequests verändern Ergebnis/Zeit nicht unzulässig.
9. Fortsetzen behält Fragen, Antworten, Reihenfolgen, letzte Position und Versuchsnummer. Serverneustart verliert keine bestätigten Zustände.
10. Zeitablauf und manuelle Abgabe finalisieren genau einmal. Nachträgliche Schreibversuche scheitern; offene Freitextbewertung bleibt möglich.
11. Deaktivierte Fragen werden nicht neu gezogen; bei zu wenigen aktiven Fragen werden Online-Start und PDF-Erstellung mit Erklärung blockiert. Bestehende Versuche/Bögen bleiben unverändert.
12. Trainer erzeugt zwei zusammengehörige PDFs nach Operatorvorgaben: gleiche Aufgaben und Reihenfolge, Lösungen/Erklärungen nur in der Lösungsfassung. Keine Teilnehmerberechtigung auf Lösungsdownloads.
13. Alle Abläufe unter beiden erlaubten Modulkonfigurationen testen: nur Prüfungen und LMS + Prüfungen. Lizenz-/Schalterwechsel während Unterbrechungen beachten.

**Abnahmeziel Zertifikatsprüfung:** Operatoren verantworten Inhalt und Regeln. Trainer geben die Durchführung frei und erzeugen vorgegebene Bögen. Prüflinge bearbeiten im Vollbild, können zurückgehen und setzen einen technisch unterbrochenen Versuch mit gespeicherten Antworten und erhaltener Restzeit fort.
