# Lastenheft ABoroLMS / ML Gruppe

**Stand:** 23.09.2026  
**Projekt:** LMS mit Kurs-, Prüfungs-, Zertifikats- und Zahlungsfunktionen  
**Bewertete Revision:** `f4fa398`  
**Dokumenttyp:** Fachliche Anforderungen und belastbarer Ist-Stand

**Aktualisierung:** Django 6.1.1/Python 3.12–3.14, PostgreSQL als Produktionsstandard,
ML-Einzelsystem ohne aktive Zahlungen, visueller Drag-and-drop-PageBuilder sowie
technisches Superadmin-Dashboard sind umgesetzt. Die lokale Validierung umfasst
`check`, Migrationsprüfung und 47 erfolgreiche Tests. Produktionsabnahme, Migration,
Backup/Restore, Browser-/PDF-Regression, Upload-Sicherheit und rechtliche Prüfung
bleiben offen.

## 1. Zweck und Einordnung

Dieses Lastenheft beschreibt den aktuell vorhandenen Funktionsumfang des LMS, das geplante Zielbild und die noch erforderlichen Arbeiten bis zu einer abnahmefähigen Produktversion.

Die Dateien `FEHLERBERICHT.md`, `PLAN_MODULARISIERUNG_EINZELSYSTEM.md`, `PROJECT_STATUS.md`, `TODO_SECURITY_ENCRYPTION.md` und `UMSETZUNGSPROTOKOLL.md` wurden als Bestands- und Planungsunterlagen ausgewertet. Ihre Aussagen wurden gegen den aktuell ausgecheckten Code, die vorhandenen Migrationen und einen aktuellen Testlauf geprüft. Aussagen in diesen Dateien werden daher nicht automatisch als bereits umgesetzt behandelt.

## 2. Produktziel

ABoroLMS soll als selbst hostbare Lern- und Prüfungsplattform für die ML Gruppe betrieben werden. Eine Installation soll Benutzerverwaltung, Lerninhalte, formale Zertifikatsprüfungen, Zertifikate, optionale Zahlungen und zentrale Betreiberkonfiguration bereitstellen.

Das langfristige Zielbild ist:

- eine gemeinsame Installation mit gemeinsamem Datenbankschema;
- zwei unabhängig freischaltbare Fachmodule: LMS und Prüfungen;
- drei Nutzungsvarianten: nur LMS, nur Prüfungen oder beide Module;
- eine zentrale Betreiberkonfiguration im Einzelbetrieb;
- ein separater Lizenz-/Seriennummerngenerator außerhalb der Kundeninstallation;
- Erhalt von Daten, Fortschritten, Prüfungen, Zertifikaten und Rechnungen bei Modulwechseln.

Der Lizenzgenerator und die zentrale Lizenzdurchsetzung sind im aktuellen Checkout noch nicht vorhanden.

## 3. Aktueller technischer Bestand

### 3.1 Architektur

- Django-Projekt unter `config` mit `manage.py`.
- Fach-Apps: `accounts`, `organisations`, `courses`, `exams`, `certificates`, `payments`, `security`.
- SQLite-Entwicklungsdatenbank; PostgreSQL ist Produktionsstandard, optionaler S3-kompatibler Medienspeicher ist vorbereitet.
- Server-rendered Django-Templates mit statischem CSS und JavaScript-Unterstützung für Prüfungsabläufe.
- Authentifizierung über Django und django-allauth.
- PDF-Erzeugung über ReportLab für Prüfungsbögen und WeasyPrint für Zertifikate.
- Feldverschlüsselung auf Basis von `cryptography` für ausgewählte Geheimnisse und Zahlungsdaten.

### 3.2 Rollen

Im Modell `Rolle` sind folgende fachliche Rollen vorgesehen:

- Lernender/Teilnehmer;
- Trainer;
- Prüfer;
- Organisationsadministrator;
- Prüfungsoperator;
- Superuser bzw. Superadmin.

Die Rolle Prüfungsoperator ist fachlich für Fragenkataloge und Prüfungsparameter vorgesehen. Trainer sollen normale Kursarbeit erledigen können, aber nicht automatisch Prüfungsinhalte verändern.

### 3.3 Vorhandene Datenbereiche

- Benutzer, Profile, Rollen und Einladungen;
- Organisationen, Lizenztyp und Organisationsdesign;
- SMTP-Konfiguration und E-Mail-Vorlagen;
- Kurse, Kategorien, Abschnitte, Lektionen, Videos und Begleitmaterial;
- Lernfortschritt, Übungen, Einschreibungen, Bewertungen und Lernpfade;
- Fragenkataloge, Themen, Fragen, Antworten und Zuordnungspaare;
- Prüfungen, Prüfungsversionen, Themenquoten, Anmeldungen, Freigaben, Versuche und Antworten;
- Prüfungsbogenarchive und PDF-Erzeugung;
- Zertifikatsdesign, Zertifikate, Zertifikatsnummern und öffentliche Verifikation;
- Zahlungen, Zahlungseinstellungen, organisationsbezogene Zahlungseinstellungen, Rechnungen und Audit-Log.

## 4. Funktionale Anforderungen

### 4.1 Gemeinsame Plattform

| ID | Anforderung | Ist-Stand |
| --- | --- | --- |
| PLT-01 | Benutzer können sich registrieren, anmelden, abmelden, ihr Profil verwalten und Passwörter zurücksetzen. | Weitgehend vorhanden; allauth und eigener Adapter sind eingebunden. |
| PLT-02 | Rollen und Berechtigungen müssen serverseitig geprüft werden. | Rollenmixins, Profile und mehrere Rechteprüfungen vorhanden; vollständige Admin-/Browserabdeckung offen. |
| PLT-03 | Betreiberdesign, Startseite, SMTP und E-Mail-Vorlagen müssen zentral konfigurierbar sein. | Modelle und zentrale Einzelbetriebsrouten vorhanden. |
| PLT-04 | Direkte URLs dürfen keine Rollen- oder Modulgrenzen umgehen. | Für zentrale Kernbereiche teilweise umgesetzt; Gesamtabnahme ausstehend. |
| PLT-05 | Einladungen müssen erzeugt, versendet, angenommen, abgelaufen und widerrufen werden können. | Token- und Annahmelogik vorhanden; realer E-Mail-Versand und End-to-End-Abnahme offen. |

### 4.2 LMS-Modul

| ID | Anforderung | Ist-Stand |
| --- | --- | --- |
| LMS-01 | Trainer legen Kurse, Kategorien, Abschnitte und Lektionen an. | Vorhanden. |
| LMS-02 | Lektionen unterstützen Text, Video-URL, Video-Upload und Begleitmaterial. | Vorhanden; Upload-Limits und Endungen sind konfigurierbar. |
| LMS-03 | Lernende können Kurse ansehen, Lektionen bearbeiten und Fortschritt speichern. | Vorhanden. |
| LMS-04 | Lektionen können Übungen/Mini-Quiz enthalten. | Vorhanden. |
| LMS-05 | Lernpfade können Kurse enthalten und Einschreibungen sowie Fortschritt verwalten. | Vorhanden; genaue Pflicht-/Wahlabschlussregeln sind noch zu präzisieren. |
| LMS-06 | Kurse können kostenlos oder kostenpflichtig sein. | Datenmodell und manuelle/Demo-Zahlungslogik vorhanden. |
| LMS-07 | Trainer sehen Umsatz- und Kursauswertungen. | Vorhanden. |
| LMS-08 | Trainer dürfen nur Organisationen bearbeiten, in denen sie aktiv Trainer sind. | Logik und Isolationstests vorhanden; im vollständigen Testlauf verifiziert. |

### 4.3 Prüfungsmodul

| ID | Anforderung | Ist-Stand |
| --- | --- | --- |
| EXM-01 | Prüfungsoperatoren verwalten Fragenkataloge, Fragen, Antworten, Themen und Prüfungsparameter. | Fachlogik und Operator-Guards vorhanden. |
| EXM-02 | Fragen können gesucht, aktiviert und deaktiviert werden. | Vorhanden; deaktivierte Fragen werden bei neuen Ziehungen ausgeschlossen. |
| EXM-03 | CSV-Import für Fragen und Antwortstrukturen wird unterstützt. | Vorhanden; Vorschau/Dublettenregeln und Änderungsverlauf offen. |
| EXM-04 | Prüfungen unterstützen verschiedene Fragetypen einschließlich Single Choice, Multiple Choice, Freitext und Zuordnung. | Vorhanden. |
| EXM-05 | Teilnehmer können Prüfungen anmelden, starten, pausieren, fortsetzen und abgeben. | Kernablauf, serverseitige aktive Zeit und Autosave vorhanden. |
| EXM-06 | Die Prüfungsoberfläche unterstützt Zurück/Weiter, Vollbildstart, Restzeit und Reaktion auf Sichtbarkeitsverlust. | Lokal umgesetzt und getestet; ein echter Kiosk-/Prüfungsbrowser ist nicht Bestandteil des aktuellen Umfangs. |
| EXM-07 | Trainer können einzelne Teilnehmer für konkrete Prüfungen freigeben oder Freigaben widerrufen. | Modell und serverseitige Prüfung vorhanden. |
| EXM-08 | Jede Durchführung verwendet einen unveränderlichen Fragen-/Parameter-Snapshot. | Modell und Snapshot-Grundlage vorhanden; vollständige Archiv-/Abnahmekette offen. |
| EXM-09 | Prüfungs- und Lösungsbögen können mit konfigurierbaren Antwortzeilen und Fußzeile erzeugt werden. | Grundfunktion vorhanden; vollständige visuelle Regression offen. |
| EXM-10 | Prüfer bearbeiten Freitextantworten über eine Queue. | Vorhanden. |
| EXM-11 | Prüfungsstatistiken und Ergebnislisten stehen berechtigten Rollen zur Verfügung. | Vorhanden. |

### 4.4 Zertifikate

- Zertifikate werden nach bestandener Prüfung automatisch ausgestellt.
- Zertifikate besitzen Verifikationscodes und eine öffentliche Verifikationsseite.
- Zertifikats-PDFs können geschützt heruntergeladen werden.
- Design, Logo, Farben, Fußzeile und Unterschriften sind organisationsbezogen modelliert.
- Interne Zertifikatsnummern sind im Modell vorgesehen.
- Rechtliche Anforderungen an Rechnungs- und Zertifikatsinhalte müssen vor Produktivbetrieb fachlich geprüft werden.

### 4.5 Zahlungen und Rechnungen

Für die aktuelle ML-Einzelsystem-Abnahme sind Zahlungen deaktiviert. Dieser
Abschnitt beschreibt den vorhandenen technischen Bestand und ein optionales
späteres Modul, nicht einen aktiven Zahlungsfluss.

- Zahlungsarten für Stripe, PayPal, Google Pay und Überweisung sind im Modell vorgesehen.
- Zahlungseinstellungen und Secrets können im Admin gepflegt werden.
- Zahlungen speichern Plattformgebühr und Traineranteil.
- Nach bestätigter Zahlung können Einschreibung und Rechnung erzeugt werden.
- Audit-Log und Auszahlungstracking sind vorhanden.
- Echte Provider-Integrationen und Webhooks sind noch nicht vollständig implementiert oder produktiv getestet.
- Prüfungsgebühren ohne Kursbezug sind im Zielbild vorgesehen, im aktuellen Datenmodell aber noch nicht vollständig entkoppelt.

### 4.6 Einzelbetrieb und Betreiberkonfiguration

Aktuell sind Einstellungen wie `SINGLE_SYSTEM_MODE`, Betreibername, Domain, Betreiber-Slug und Farbwerte vorhanden. Zentrale Routen unter `/verwaltung/` sowie `/startseite/` sind angelegt. Technische Organisationsfremdschlüssel bleiben im Datenmodell bestehen.

Für den produktiven Einzelbetrieb müssen zusätzlich erfüllt sein:

- genau eine Betreiberkonfiguration ohne versteckten Mehrmandantenbetrieb;
- zentrale Rollen- und Rechteauswertung;
- keine sichtbare Organisationsauswahl im normalen Ablauf;
- saubere Behandlung alter URLs und POST-Endpunkte;
- geprüfte Migration einer ausgewählten Quellorganisation;
- vollständige Abnahme ohne Vermischung von Demo- und Produktivdaten.

### 4.7 Lizenzierung und Module

Das Lastenheft fordert:

- signierte Lizenzdaten mit Produktkennung, Lizenz-ID, Revision, Modulrechten und Gültigkeit;
- Prüfung mit öffentlichem Schlüssel in der Kundenanwendung;
- separaten Generator mit privatem Signierschlüssel;
- zentrale serverseitige Durchsetzung für Views, Formulare, Services, Downloads, Admin und Commands;
- Aktivieren/Deaktivieren ohne Neuinstallation und ohne Datenverlust;
- klar definierte Regeln für Ablauf, laufende Prüfungen, offene Bewertungen, Zahlungen und Bestandszugriff.

**Ist:** Im aktuellen Checkout existieren dafür noch keine eigenständige `licensing`-App, kein Generator und keine vollständige zentrale Modulprüfung.

## 5. Nichtfunktionale Anforderungen

### 5.1 Sicherheit und Datenschutz

- Passwörter werden gehasht und nicht verschlüsselt.
- Feldverschlüsselung verwendet einen separaten `FIELD_ENCRYPTION_KEY`.
- Bereits verschlüsselte Felder umfassen unter anderem SMTP-Passwort, Payment-Secrets, Bankdaten, Providerreferenzen und Betreiber-Notizen.
- Schlüssel dürfen nicht aus dem normalen `SECRET_KEY` abgeleitet werden.
- Rollen-, Organisations- und Objektzugriffe müssen serverseitig abgesichert sein.
- Auditierbare Aktionen, Datenexport, Löschung/Anonymisierung und Schlüsselrotation sind noch zu spezifizieren.
- Rechnungsname und Rechnungs-E-Mail benötigen ein Hybridmodell oder Hash-Lookups, falls exakte Suche weiter erforderlich ist.
- Upload-Sicherheit benötigt zusätzlich Virenscan, MIME-Prüfung, Webserver-Limits und gegebenenfalls Transcoding.

### 5.2 Betrieb und Deployment

- Installationsskripte für Linux mit Apache/Nginx und Windows mit IIS/Waitress/NSSM sind vorgesehen.
- Produktionskonfiguration muss Secrets aus Umgebungsvariablen beziehen.
- Medien, Datenbank und Verschlüsselungsschlüssel müssen gemeinsam mit einem getesteten Restore-Prozess gesichert werden.
- Unterstützte Datenbanken, Browser, Geräte und maximale Datei-/Videogrößen sind verbindlich zu dokumentieren.

### 5.3 Qualität

- `python manage.py check` muss ohne Fehler durchlaufen.
- `makemigrations --check --dry-run` muss „No changes detected“ melden.
- Unit-, Integrations- und Browser-Smoke-Tests müssen den Kernbetrieb und negative Berechtigungsfälle abdecken.
- PDF- und zentrale Browserflüsse benötigen visuelle Regressionstests.

## 6. Aktueller Verifikationsstand

Am 23.09.2026 wurde der technische Stand im aktuellen Checkout erneut geprüft:

```text
python manage.py check
System check identified no issues (0 silenced).
```

Zusätzlich erfolgreich geprüft:

```text
python manage.py makemigrations --check --dry-run
No changes detected

python manage.py migrate --noinput
No migrations to apply.

python manage.py test --noinput
Ran 47 tests in 185.208s
OK
```

Im Rahmen der technischen Bereinigung wurden die fehlenden Migrationen für den aktuellen Modellstand ergänzt, der Prüfungszeitgeber beim Start eines Versuchs aktiviert, ungültige Zuordnungswerte für die korrekte Teilbewertung zugelassen, das Einzelbetriebs-/Mehrmandanten-Routing entkoppelt und der Demo-Daten-Schutztest korrigiert. Die Testbasis für fachlich mehrmandantenbezogene Szenarien verwendet den expliziten Mehrmandanten-Testmodus; die Produktivvoreinstellung `SINGLE_SYSTEM_MODE=True` bleibt unverändert.

Damit ist der technische Entwicklungsstand für die vorhandenen automatisierten Kernfälle stabil. Eine fachliche Produktivabnahme ist weiterhin nicht erfolgt; insbesondere Lizenzierung, rechtliche Dokumentanforderungen, Backup/Restore, Datenmigration und Browser-/PDF-Smoke-Tests bleiben offen. Echte Zahlungsanbieter gehören im ML-Einzelsystem derzeit nicht zum aktiven Umfang.

## 7. Abnahmekriterien

Eine erste fachliche Abnahme ist erfüllt, wenn:

1. alle Modelländerungen als nachvollziehbare Migrationen vorliegen;
2. `check`, Migrationscheck und vollständiger Testlauf erfolgreich sind;
3. Login, Logout, Registrierung, Passwortreset und Einladungsannahme funktionieren;
4. Kurskatalog, Kurslernen, Lernpfad und Fortschritt mit Lernenden getestet sind;
5. Trainer, Prüfungsoperatoren, Prüfer, Administratoren und Lernende nur ihre erlaubten Aktionen sehen und ausführen können;
6. Prüfung, Autosave, Pause, Fortsetzen, Restzeit, Abgabe, Bewertung und Zertifikat Ende-zu-Ende funktionieren;
7. Prüfungs- und Zertifikats-PDFs visuell geprüft sind;
8. Zahlungsbestätigung idempotent ist und keine doppelten Einschreibungen/Rechnungen erzeugt;
9. Verschlüsselungs-Key, Backup, Restore und Secrets im Zielbetrieb geprüft sind;
10. der Einzelbetriebsmodus mit einer ausgewählten Datenquelle migriert und gegen Demo-/Fremddaten abgegrenzt ist;
11. für produktive Lizenzierung Generator, Signaturprüfung, Modulschalter und Ablaufregeln abgenommen sind;
12. Browser-Smoke-Tests auf den unterstützten Browsern erfolgreich sind.

## 8. Priorisierte offene Arbeiten

### Release-Blocker

- Produktivkonfiguration, Backup/Restore und Deployment auf einer Zielumgebung praktisch abnehmen.
- Browser-Smoke- und PDF-Regressionstests auf den unterstützten Zielsystemen durchführen.
- Lizenz-/Modulentscheidung treffen und die daraus resultierende zentrale Durchsetzung implementieren.

### Hohe Priorität

- Einzelbetriebs-Migration mit Bestandsaufnahme, Sicherung und Rückweg umsetzen.
- Modul- und Lizenzprüfung als zentrale, serverseitig erzwungene Funktion implementieren.
- Lizenzgenerator separat spezifizieren und entwickeln.
- Prüfungs-Snapshot, PDF-Archiv und Änderungsverlauf vollständig abnehmen.
- Browser-/Verbindungsabbruch, Prüfungsfortsetzung und negative Rollenfälle zusätzlich als Browser-Smoke-Fälle prüfen.

### Mittlere Priorität

- Echte Stripe-/PayPal-/Google-Pay-Webhooks integrieren und testen.
- Prüfungszahlungen unabhängig von Kursen modellieren, falls Prüfungen kostenpflichtig angeboten werden.
- CSV-Vorschau, Dublettenregeln und Änderungsverlauf ergänzen.
- Rechnungs-/Adressdaten mit Hash-Lookups, Export, Anonymisierung und Schlüsselrotation absichern.
- Upload-Virenscan, MIME-Prüfung und Transcoding prüfen.

## 9. Fachliche Entscheidungen, die noch bestätigt werden müssen

- Lizenzlaufzeit: unbefristet, befristet oder beides;
- offline signierter Lizenzcode oder zusätzlicher Online-Aktivierungsdienst;
- Installationsbindung und geplanter Umzug auf einen anderen Server;
- Verhalten bei Lizenzablauf während laufender Prüfungen und offener Bewertungen;
- verbindliche Pflicht-/Wahlregeln für Lern- und Prüfungspfade;
- unterstützte Browser/Geräte und Umfang eines echten Kioskmodus;
- gesetzliche Rechnungsangaben, Nummernkreise und Steuerlogik;
- Produktiv-Branding einschließlich Logo, Favicon und endgültiger Farbwerte;
- eine ausgewählte Datenquelle je Einzelinstallation und Umgang mit weiteren Organisationen.

## 10. Quellen

- [FEHLERBERICHT.md](FEHLERBERICHT.md) – behobener Mandanten-/Rollenfehler und bekannte Rest-Risiken
- [PLAN_MODULARISIERUNG_EINZELSYSTEM.md](PLAN_MODULARISIERUNG_EINZELSYSTEM.md) – Zielbild, Lizenzierung, Einzelbetrieb und Prüfungsanforderungen
- [PROJECT_STATUS.md](PROJECT_STATUS.md) – bisheriger Projektstatus
- [TODO_SECURITY_ENCRYPTION.md](TODO_SECURITY_ENCRYPTION.md) – Verschlüsselung, Datenschutz und Betriebsaufgaben
- [UMSETZUNGSPROTOKOLL.md](UMSETZUNGSPROTOKOLL.md) – chronologische Umsetzungsschritte
