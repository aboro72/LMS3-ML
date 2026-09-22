from django.conf import settings as django_settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django_quill.quill import Quill

from apps.accounts.models import Rolle, UserProfile
from apps.courses.models import Abschnitt, Begleitmaterial, Einschreibung, Kurs, Lektion, Niveau, Uebungsantwort, Uebungsfrage
from apps.exams.models import Antwort, Frage, Fragenkatalog, Pruefung, ZuordnungsPaar
from apps.organisations.models import LizenzTyp, Organisation, OrganisationDesign, OrganisationEmailKonfiguration, OrganisationStartseite
from apps.payments.models import Zahlung, Zahlungsart, Zahlungseinstellungen, Zahlungsstatus
from apps.payments.services import bestaetige_zahlung, erstelle_zahlung


def quill_html(html):
    import json
    return Quill('{"delta": "", "html": ' + json.dumps(html) + "}")


# ---------------------------------------------------------------------------
# Kursinhalte: 7 Abschnitte × 2 Lektionen = 14 Lektionen
# Jede Lektion hat optional eine Uebungsfrage und/oder ein Begleitmaterial.
# ---------------------------------------------------------------------------
KURSINHALTE = [
    {
        "titel": "Grundlagen und Architektur",
        "lektionen": [
            {
                "titel": "Was ist ABoroLMS?",
                "typ": Lektion.Typ.VIDEO,
                "dauer": 8,
                "ist_vorschau": True,
                "inhalt": (
                    "<h2>Was ist ABoroLMS?</h2>"
                    "<p>ABoroLMS ist ein selbst gehostetes Learning Management System (LMS) auf Django-Basis. "
                    "Unternehmen und Bildungsanbieter betreiben die Plattform auf eigenem Server – "
                    "ohne monatliche SaaS-Gebuehren und mit vollstaendiger Datenkontrolle.</p>"
                    "<h3>Kernfunktionen im Ueberblick</h3>"
                    "<ul>"
                    "<li><strong>Kurse und Lektionen:</strong> Video-Upload oder externe URL, Begleitmaterialien, Uebungsfragen.</li>"
                    "<li><strong>Pruefungssystem:</strong> 6 Fragetypen, Zufallsreihenfolge, automatische Auswertung, Examiner-Queue.</li>"
                    "<li><strong>Zertifikate:</strong> Automatische PDF-Ausstellung nach bestandener Pruefung mit QR-Code-Verifikation.</li>"
                    "<li><strong>Zahlungen:</strong> Stripe, PayPal, Google Pay und Ueberweisung – 85 % Trainer, 15 % Plattform.</li>"
                    "<li><strong>Mandantenfaehigkeit:</strong> Mehrere Organisationen, eine Installation, Daten logisch getrennt.</li>"
                    "</ul>"
                    "<h3>Selfhosting-Technologie</h3>"
                    "<p>ABoroLMS basiert auf <strong>Django 6</strong>, Bootstrap 5 und SQLite/PostgreSQL. "
                    "Die Installation ist ueber GitHub-Skripte geplant: Linux mit Apache2 oder Nginx sowie Windows mit IIS.</p>"
                    "<p>Diese Demo laeuft mit der Pro-Lizenz (100 Nutzer, 25 Kurse) und zeigt alle verfuegbaren Funktionen.</p>"
                ),
                "uebung": {
                    "frage": "Welches Betriebsmodell verfolgt ABoroLMS?",
                    "antworten": [
                        ("Selfhosting auf eigenem Server – keine monatlichen SaaS-Gebuehren.", True),
                        ("Rein cloudbasiert ohne eigene Installation moeglich.", False),
                        ("Nur als Desktop-Anwendung ohne Webbrowser nutzbar.", False),
                    ],
                    "erklaerung": "ABoroLMS ist als Selfhosting-Produkt konzipiert: volle Kontrolle, keine Abhaengigkeit von Drittanbietern.",
                },
                "material": None,
            },
            {
                "titel": "Architektur: Apps, Mandanten und Settings",
                "typ": Lektion.Typ.TEXT,
                "dauer": 7,
                "ist_vorschau": False,
                "inhalt": (
                    "<h2>Architektur: Apps, Mandanten und Settings</h2>"
                    "<p>ABoroLMS ist als modulares Django-Projekt aufgebaut. Jede Funktion hat ihre eigene App:</p>"
                    "<ul>"
                    "<li><code>accounts</code> – Nutzer, Rollen, UserProfile, Einladungen</li>"
                    "<li><code>organisations</code> – Mandantenmodell, Lizenztypen, Org-Admin-Views</li>"
                    "<li><code>courses</code> – Kurse, Abschnitte, Lektionen, Fortschritt, Einschreibung</li>"
                    "<li><code>exams</code> – Fragenkataloge, Pruefungen, Versuche, Freitext-Queue</li>"
                    "<li><code>payments</code> – Zahlungsarten, 85/15-Aufteilung, Auszahlungstracking</li>"
                    "<li><code>certificates</code> – Zertifikate, PDF-Export, oeffentliche Verifikation</li>"
                    "</ul>"
                    "<h3>Mandantenfaehigkeit durch Organisationsbezug</h3>"
                    "<p>Jede zentrale Entitaet – Kurs, Fragenkatalog, Pruefung, Zahlung – hat einen ForeignKey auf <code>Organisation</code>. "
                    "Views filtern konsequent nach den Organisationen des angemeldeten Nutzers. "
                    "Kein separates Datenbankschema pro Mandant noetig.</p>"
                    "<h3>Wichtige Settings</h3>"
                    "<ul>"
                    "<li><code>PLATFORM_COMMISSION_PERCENT</code> (Standard: 15) – Plattformgebuehr in Prozent</li>"
                    "<li><code>PAYMENT_DEMO_AUTOCONFIRM</code> – Zahlungen automatisch bestaetigen (Demo-Modus)</li>"
                    "<li><code>MEDIA_ROOT</code> – Speicherort fuer Videos, Thumbnails, Begleitmaterialien</li>"
                    "<li><code>SECRET_KEY</code>, <code>ALLOWED_HOSTS</code> – per <code>.env</code> oder Umgebungsvariable</li>"
                    "</ul>"
                    "<p><strong>Faustregel:</strong> Alle QuerySets in Views beginnen mit einem Organisations-Filter, "
                    "damit kein Nutzer Daten fremder Mandanten sehen kann.</p>"
                ),
                "uebung": {
                    "frage": "Wie trennt ABoroLMS Daten verschiedener Organisationen?",
                    "antworten": [
                        ("Durch Organisationsbezug (ForeignKey) und konsequente QuerySet-Filterung in Views.", True),
                        ("Durch separate Datenbanken je Organisation auf demselben Server.", False),
                        ("Durch unterschiedliche Django-Projekte je Mandant.", False),
                    ],
                    "erklaerung": "Eine Installation, ein Datenbankschema – Isolation entsteht durch FK-Filter, nicht durch Trennung der Daten.",
                },
                "material": (
                    "ABoroLMS_Architektur_Ueberblick.txt",
                    (
                        "ABoroLMS Architektur – Kurzreferenz\n"
                        "====================================\n\n"
                        "Apps und Zustaendigkeiten:\n"
                        "  accounts      -> Nutzer, Rollen, UserProfile, Einladungen\n"
                        "  organisations -> Org-Modell, Lizenz, Org-Admin-Dashboard\n"
                        "  courses       -> Kurse, Lektionen, Fortschritt, Einschreibung\n"
                        "  exams         -> Katalog, Pruefungen, Versuche, Examiner-Queue\n"
                        "  payments      -> Zahlungsarten, 85/15-Split, Auszahlungen\n"
                        "  certificates  -> Zertifikat-Model, PDF, QR-Verifikation\n\n"
                        "Mandantenfaehigkeit: ForeignKey Organisation + QuerySet-Filter\n"
                        "Keine separaten Schemas – eine Installation fuer alle Mandanten\n\n"
                        "Key-Settings:\n"
                        "  PLATFORM_COMMISSION_PERCENT = 15\n"
                        "  PAYMENT_DEMO_AUTOCONFIRM    = True  (nur Demo!)\n"
                        "  MEDIA_ROOT                  = <Pfad zu hochgeladenen Dateien>\n"
                    ),
                ),
            },
        ],
    },
    {
        "titel": "Rollen und Organisationsverwaltung",
        "lektionen": [
            {
                "titel": "Die fuenf Rollen im Ueberblick",
                "typ": Lektion.Typ.TEXT,
                "dauer": 7,
                "ist_vorschau": False,
                "inhalt": (
                    "<h2>Die fuenf Rollen im Ueberblick</h2>"
                    "<p>ABoroLMS unterscheidet fuenf Rollen, die ueber <strong>Django Groups</strong> und "
                    "<strong>UserProfile</strong> je Organisation vergeben werden. "
                    "Ein Nutzer kann in verschiedenen Organisationen unterschiedliche Rollen haben.</p>"
                    "<table>"
                    "<tr><th>Rolle</th><th>Zustaendigkeit</th><th>Beispiel-URL</th></tr>"
                    "<tr><td><strong>Super-Admin</strong></td><td>Betreiber der gesamten Plattform, sieht alles</td><td>/admin/</td></tr>"
                    "<tr><td><strong>Org-Admin</strong></td><td>Verwaltet Nutzer und Einstellungen der eigenen Organisation</td><td>/organisationen/&lt;slug&gt;/</td></tr>"
                    "<tr><td><strong>Trainer</strong></td><td>Erstellt Kurse, Fragenkataloge, Pruefungen</td><td>/trainer/kurse/</td></tr>"
                    "<tr><td><strong>Pruefer</strong></td><td>Bewertet manuelle Freitextantworten</td><td>/examiner/queue/</td></tr>"
                    "<tr><td><strong>Lernender</strong></td><td>Nimmt an Kursen teil, absolviert Pruefungen</td><td>/kurse/</td></tr>"
                    "</table>"
                    "<h3>Technische Abbildung</h3>"
                    "<p>Rollen werden in zwei Strukturen gespeichert:</p>"
                    "<ul>"
                    "<li><strong>Django Group</strong> – traegt den Rollennamen (superadmin, trainer, ...)</li>"
                    "<li><strong>UserProfile</strong> – verbindet Nutzer + Organisation + Rolle + aktiv-Flag</li>"
                    "</ul>"
                    "<p>Das <code>RollenMixin</code> prueft in <code>dispatch()</code>: "
                    "Superuser darf immer rein; sonst muss <code>UserProfile.filter(rolle=..., aktiv=True).exists()</code> True ergeben.</p>"
                    "<h3>Demo-Zugaenge</h3>"
                    "<p>Alle Demo-Nutzer haben das Passwort <code>ChangeMe123!</code>. "
                "Benutzernamen: <code>superadmin</code>, <code>exam_operator</code>, <code>trainer</code>, "
                "<code>examiner</code>, <code>learner</code>.</p>"
                ),
                "uebung": {
                    "frage": "Welche Rolle erstellt Fragenkataloge und Pruefungen?",
                    "antworten": [
                        ("Trainer", True),
                        ("Lernender", False),
                        ("Pruefer (Examiner)", False),
                    ],
                    "erklaerung": "Trainer pflegen alle Kursinhalte und Pruefungsstrukturen ihrer Organisation.",
                },
                "material": (
                    "Rollenmatrix.txt",
                    (
                        "ABoroLMS Rollenmatrix\n"
                        "=====================\n\n"
                        "Funktion                         SA  OA  TR  EX  LE\n"
                        "-------------------------------- --- --- --- --- ---\n"
                        "Alle Orgs verwalten              X\n"
                        "Eigene Org-Einstellungen         X   X\n"
                        "Mitglieder einladen              X   X\n"
                        "Kurse erstellen/bearbeiten       X   X   X\n"
                        "Fragenkatalog/Pruefung anlegen   X   X   X\n"
                        "Freitext-Antworten bewerten      X   X   X   X\n"
                        "An Kursen teilnehmen             X   X   X   X   X\n"
                        "Pruefung ablegen                 X   X   X   X   X\n"
                        "Zertifikat herunterladen         X   X   X   X   X\n\n"
                        "SA=Super-Admin  OA=Org-Admin  TR=Trainer  EX=Pruefer  LE=Lernender\n"
                    ),
                ),
            },
            {
                "titel": "Org-Admin: Organisation erstellen und verwalten",
                "typ": Lektion.Typ.TEXT,
                "dauer": 8,
                "ist_vorschau": False,
                "inhalt": (
                    "<h2>Org-Admin: Organisation erstellen und verwalten</h2>"
                    "<h3>Organisation selbst registrieren</h3>"
                    "<p>Jeder eingeloggte Nutzer kann unter <code>/organisationen/signup/</code> "
                    "eine eigene Organisation anlegen. Er wird dabei automatisch Org-Admin. "
                    "Name, Slug (URL-Bezeichner), Kontakt-E-Mail und optionale Website werden abgefragt.</p>"
                    "<h3>OrgAdmin-Dashboard</h3>"
                    "<p>Das Dashboard unter <code>/organisationen/&lt;slug&gt;/</code> zeigt vier KPIs:</p>"
                    "<ul>"
                    "<li><strong>Mitglieder:</strong> Aktive UserProfile-Eintraege der Org (vs. Lizenzlimit)</li>"
                    "<li><strong>Kurse:</strong> Anzahl Kurse der Org (vs. Lizenzlimit)</li>"
                    "<li><strong>Bezahlte Einschreibungen:</strong> Lernende, die Zugriff haben</li>"
                    "<li><strong>Gesamtumsatz:</strong> Summe aller bestaedigten Zahlungen (EUR)</li>"
                    "</ul>"
                    "<h3>Mitgliederverwaltung und Einladungen</h3>"
                    "<p>Unter <code>/organisationen/&lt;slug&gt;/mitglieder/</code> sieht der Org-Admin alle aktiven Mitglieder. "
                    "Neue Mitglieder werden per Einladung hinzugefuegt: E-Mail-Adresse + Rolle eingeben, "
                    "Einladungstoken wird erstellt (7 Tage gueltig). "
                    "Der Eingeladene oeffnet den Link und verknuepft sein Konto.</p>"
                    "<h3>Lizenzlimits</h3>"
                    "<p>Je nach Lizenztyp (Basic / Pro / Enterprise) gelten Grenzen:</p>"
                    "<ul>"
                    "<li>Kurs erstellen: Wird <code>max_kurse</code> ueberschritten, erscheint eine Fehlermeldung.</li>"
                    "<li>Einladung versenden: Wird <code>max_nutzer</code> ueberschritten, ist die Einladung gesperrt.</li>"
                    "<li>Wert 0 bei max_nutzer oder max_kurse bedeutet unbegrenzt.</li>"
                    "</ul>"
                    "<h3>Superadmin-Uebersicht</h3>"
                    "<p>Unter <code>/superadmin/organisationen/</code> sieht der Super-Admin alle registrierten Organisationen "
                    "mit Lizenz-Badge, Mitglieder- und Kurszahl sowie Aktivstatus. "
                    "Lizenzaenderungen nimmt er im Django-Admin vor.</p>"
                ),
                "uebung": {
                    "frage": "Was passiert, wenn max_nutzer einer Organisation erreicht ist?",
                    "antworten": [
                        ("Weitere Einladungen werden gesperrt, bis die Lizenz upgegradet wird.", True),
                        ("Bestehende Nutzer werden automatisch entfernt.", False),
                        ("Der gesamte Kurs wird deaktiviert.", False),
                    ],
                    "erklaerung": "Lizenzlimits werden bei Einladung und Kurserstellung geprueft – bestehende Daten bleiben unveraendert.",
                },
                "material": None,
            },
        ],
    },
    {
        "titel": "Kurse und Lerninterface",
        "lektionen": [
            {
                "titel": "Kursaufbau: Abschnitte, Lektionen und Inhaltstypen",
                "typ": Lektion.Typ.TEXT,
                "dauer": 8,
                "ist_vorschau": False,
                "inhalt": (
                    "<h2>Kursaufbau: Abschnitte, Lektionen und Inhaltstypen</h2>"
                    "<p>Ein Kurs ist dreistufig aufgebaut: <strong>Kurs → Abschnitte → Lektionen</strong>. "
                    "Abschnitte gruppieren thematisch zusammengehoerende Lektionen und haben eine Reihenfolge. "
                    "Lektionen koennen vier Typen haben:</p>"
                    "<ul>"
                    "<li><strong>VIDEO</strong> – Upload (MP4, WebM, MOV, M4V bis zum Server-Limit) oder externe URL (YouTube, Vimeo). "
                    "HTML5-Video-Player eingebettet, Platzhalter bei fehlender Datei.</li>"
                    "<li><strong>TEXT</strong> – Rich-Text-Inhalt ueber den Quill-Editor, ideal fuer Erklaerungen und Zusammenfassungen.</li>"
                    "<li><strong>DOKUMENT</strong> – PDF oder anderes Dokument zum Download.</li>"
                    "<li><strong>QUIZ</strong> – Lektion mit Uebungsfragen (Multiple-Choice, inline bewertet).</li>"
                    "</ul>"
                    "<h3>Begleitmaterialien</h3>"
                    "<p>Jede Lektion kann beliebig viele Begleitmaterialien haben – Dateien zum Herunterladen, "
                    "z.B. Merkblaetter, Checklisten oder Skripte. Sie erscheinen am Ende der Lektion.</p>"
                    "<h3>Uebungsfragen</h3>"
                    "<p>Jede Lektion kann Multiple-Choice-Uebungsfragen tragen. "
                    "Nach dem Absenden sieht der Lernende sofort, welche Antworten richtig waren und liest die Erklaerung. "
                    "Das Ergebnis der Uebung beeinflusst den Lernfortschritt nicht – es dient nur der Selbstkontrolle.</p>"
                    "<h3>Trainer-Interface</h3>"
                    "<p>Trainer verwalten Kurse unter <code>/trainer/kurse/</code>. "
                    "Auf der Bearbeitungsseite koennen sie Abschnitte und Lektionen inline hinzufuegen, "
                    "Begleitmaterialien hochladen und Uebungsfragen anlegen – alles ohne Seitenwechsel.</p>"
                ),
                "uebung": {
                    "frage": "Welche Lektionstypen unterstuetzt ABoroLMS?",
                    "antworten": [
                        ("VIDEO, TEXT, DOKUMENT und QUIZ", True),
                        ("Nur PDF-Uploads", False),
                        ("Nur externe YouTube-Links", False),
                    ],
                    "erklaerung": "Alle vier Typen stehen zur Verfuegung; Videos koennen hochgeladen oder als URL eingebunden werden.",
                },
                "material": None,
            },
            {
                "titel": "Einschreibung, Zugriff und Lernfortschritt",
                "typ": Lektion.Typ.TEXT,
                "dauer": 7,
                "ist_vorschau": False,
                "inhalt": (
                    "<h2>Einschreibung, Zugriff und Lernfortschritt</h2>"
                    "<h3>Kostenlose vs. kostenpflichtige Kurse</h3>"
                    "<p>Jeder Kurs hat ein Flag <code>ist_kostenlos</code> und ein Feld <code>preis</code> (EUR). "
                    "Kostenlose Kurse erhalten beim Klick auf 'Einschreiben' sofort eine Einschreibung mit <code>bezahlt=True</code>. "
                    "Kostenpflichtige Kurse leiten auf die Checkout-Seite um.</p>"
                    "<h3>Zugriffspruefung</h3>"
                    "<p>Die Funktion <code>kurszugriff_bezahlt(user, kurs)</code> prueft:</p>"
                    "<ol>"
                    "<li>Ist der Kurs kostenlos oder Preis = 0 → direkt Zugriff.</li>"
                    "<li>Existiert eine Einschreibung mit <code>bezahlt=True</code> → Zugriff.</li>"
                    "<li>Sonst → Weiterleitung zum Checkout.</li>"
                    "</ol>"
                    "<h3>Fortschritt speichern</h3>"
                    "<p>Beim Klick auf 'Lektion abschliessen' legt ABoroLMS einen <code>LektionsFortschritt</code>-Eintrag an "
                    "(Einschreibung + Lektion + Zeitstempel). "
                    "Danach berechnet <code>einschreibung.aktualisiere_fortschritt()</code> den Prozentwert neu "
                    "(abgeschlossene Lektionen / Gesamtlektionen * 100). "
                    "Dieser Wert ist im Dashboard und in der Kursliste sichtbar.</p>"
                    "<h3>Vorschau-Lektionen</h3>"
                    "<p>Lektionen mit <code>ist_vorschau=True</code> sind in der Kursdetailansicht fuer alle sichtbar, "
                    "auch ohne Einschreibung. Das ermoeglicht eine Kursvorschau ohne Kaufzwang.</p>"
                    "<h3>Kurs-Abschlusspruefung</h3>"
                    "<p>Ein Kurs kann optional mit einer Pruefung verknuepft sein. "
                    "Nach dem letzten Lektionsabschluss erscheint ein Link zur Zertifikatspruefung – "
                    "bestanden bedeutet automatisch ein Zertifikat.</p>"
                ),
                "uebung": {
                    "frage": "Wie wird der Lernfortschritt eines Nutzers berechnet?",
                    "antworten": [
                        ("Abgeschlossene Lektionen geteilt durch Gesamtlektionen des Kurses, in Prozent.", True),
                        ("Durch die Anzahl korrekt beantworteter Uebungsfragen.", False),
                        ("Nur durch manuelle Eingabe des Trainers.", False),
                    ],
                    "erklaerung": "aktualisiere_fortschritt() zaehlt LektionsFortschritt-Eintraege und teilt durch die Gesamtzahl.",
                },
                "material": None,
            },
        ],
    },
    {
        "titel": "Pruefungssystem",
        "lektionen": [
            {
                "titel": "Fragenkataloge und die sechs Fragetypen",
                "typ": Lektion.Typ.TEXT,
                "dauer": 9,
                "ist_vorschau": False,
                "inhalt": (
                    "<h2>Fragenkataloge und die sechs Fragetypen</h2>"
                    "<p>Ein <strong>Fragenkatalog</strong> ist ein Container fuer Fragen einer Organisation. "
                    "Trainer erstellen ihn unter <code>/trainer/fragenkataloge/</code> "
                    "und befuellen ihn manuell oder per CSV-Import.</p>"
                    "<h3>Die sechs Fragetypen</h3>"
                    "<ul>"
                    "<li><strong>SC – Single Choice:</strong> Genau eine richtige Antwort unter mehreren Optionen.</li>"
                    "<li><strong>MC – Multiple Choice:</strong> Mehrere Antworten koennen richtig sein; alle muessen korrekt angekreuzt werden.</li>"
                    "<li><strong>WF – Wahr/Falsch:</strong> Vereinfachter SC mit zwei Optionen.</li>"
                    "<li><strong>FT – Freitext:</strong> Offene Texteingabe; Auswertung durch einen Pruefer (Examiner).</li>"
                    "<li><strong>ZO – Zuordnung:</strong> Linke Elemente werden den richtigen rechten Elementen per Dropdown zugeordnet.</li>"
                    "<li><strong>SZ – Szenario (Case Study):</strong> Uebergeordnete Kontextfrage mit Teilfragen verschiedener Typen.</li>"
                    "</ul>"
                    "<h3>CSV-Import</h3>"
                    "<p>Grosse Fragemengen lassen sich per CSV-Datei importieren. Trennzeichen ist das Semikolon. "
                    "Pflichtfelder: <code>typ</code> und <code>fragetext</code>. "
                    "Fuer SC/MC/WF: Spalten <code>antwort_1</code> bis <code>antwort_8</code> und <code>korrekt_1</code> bis <code>korrekt_8</code> (0 oder 1). "
                    "Fuer ZO: Spalten <code>links_1</code>/<code>rechts_1</code> bis <code>links_5</code>/<code>rechts_5</code>.</p>"
                    "<h3>Fragen-Attribute</h3>"
                    "<p>Jede Frage hat: Typ, Fragetext (Rich-Text), optionale Erklaerung, Schwierigkeit (Leicht/Mittel/Schwer), "
                    "Punkte, Tags und optional eine Elternfrage (fuer Szenarien). "
                    "Antwortoptionen koennen zufaellig sortiert werden – konfigurierbar je Pruefung.</p>"
                ),
                "uebung": {
                    "frage": "Welcher Fragetyp erfordert manuelle Bewertung durch einen Pruefer?",
                    "antworten": [
                        ("FT – Freitext", True),
                        ("SC – Single Choice", False),
                        ("WF – Wahr/Falsch", False),
                    ],
                    "erklaerung": "Freitextantworten landen in der Examiner-Queue und werden manuell mit Punkten und Kommentar bewertet.",
                },
                "material": (
                    "CSV_Import_Format.txt",
                    (
                        "ABoroLMS CSV-Import Format fuer Fragenkataloge\n"
                        "================================================\n\n"
                        "Trennzeichen: Semikolon  |  Kodierung: UTF-8\n\n"
                        "Pflichtfelder:\n"
                        "  typ        -> SC | MC | WF | FT | ZO\n"
                        "  fragetext  -> Fragetext als Klartext\n\n"
                        "Optionale Felder:\n"
                        "  punkte       -> Zahl (Standard: 1)\n"
                        "  schwierigkeit -> L | M | S (Standard: M)\n\n"
                        "SC/MC/WF: antwort_1..antwort_8, korrekt_1..korrekt_8 (0 oder 1)\n"
                        "ZO:       links_1..links_5, rechts_1..rechts_5\n\n"
                        "Beispiel (SC):\n"
                        "typ;fragetext;antwort_1;korrekt_1;antwort_2;korrekt_2\n"
                        "SC;Wer betreibt ABoroLMS?;Der Kunde selbst;1;Anthropic;0\n"
                    ),
                ),
            },
            {
                "titel": "Pruefungsablauf und automatische Auswertung",
                "typ": Lektion.Typ.TEXT,
                "dauer": 9,
                "ist_vorschau": False,
                "inhalt": (
                    "<h2>Pruefungsablauf und automatische Auswertung</h2>"
                    "<h3>Pruefung konfigurieren</h3>"
                    "<p>Trainer erstellen eine Pruefung unter <code>/trainer/pruefungen/neu/</code>. "
                    "Konfigurationsmoeglichkeiten:</p>"
                    "<ul>"
                    "<li><strong>Fragenkatalog:</strong> Quelle der Fragen</li>"
                    "<li><strong>Anzahl Fragen:</strong> Wie viele Fragen pro Versuch gezogen werden</li>"
                    "<li><strong>Zeitlimit:</strong> Optional, in Minuten</li>"
                    "<li><strong>Bestehensgrenze:</strong> Prozent der Punkte, ab der bestanden gilt (z.B. 70%)</li>"
                    "<li><strong>Max. Versuche:</strong> Leer = unbegrenzt</li>"
                    "<li><strong>Zufaellige Reihenfolge:</strong> Fragen und Antworten individuell mischen</li>"
                    "<li><strong>Kein Zurueck:</strong> Verhindert das Navigieren zu bereits beantworteten Fragen</li>"
                    "</ul>"
                    "<h3>Pruefungsversuch</h3>"
                    "<p>Beim Start wird ein <code>PruefungsVersuch</code> angelegt mit "
                    "Versuchnummer, Startzeit, Status (<em>LAUFEND</em>) und einer JSON-Liste der Fragen-IDs. "
                    "Antworten werden als <code>TeilnehmerAntwort</code> gespeichert.</p>"
                    "<h3>Automatische Auswertung</h3>"
                    "<p>Nach dem Abgeben ruft ABoroLMS <code>werte_versuch_aus()</code> auf:</p>"
                    "<ul>"
                    "<li><strong>SC/WF:</strong> Genau eine korrekte Antwort gewaehlt → volle Punkte</li>"
                    "<li><strong>MC:</strong> Exakt alle richtigen angekreuzt → volle Punkte</li>"
                    "<li><strong>ZO:</strong> Punkte anteilig nach korrekten Zuordnungen</li>"
                    "<li><strong>FT:</strong> Wartet auf manuelle Bewertung → Status <em>AUSSTEHEND</em></li>"
                    "</ul>"
                    "<p>Status nach Auswertung: <em>ABGESCHLOSSEN</em> (alle bewertet) "
                    "oder <em>AUSSTEHEND</em> (Freitext offen). "
                    "Wenn bestanden und abgeschlossen, wird automatisch ein Zertifikat ausgestellt.</p>"
                    "<h3>Examiner-Queue</h3>"
                    "<p>Offene Freitextantworten erscheinen unter <code>/examiner/queue/</code>. "
                    "Der Pruefer sieht Frage, Antworttext und Musterloesung, vergibt Punkte und Kommentar. "
                    "Nach Bewertung der letzten FT-Antwort wird der Versuch automatisch finalisiert.</p>"
                ),
                "uebung": {
                    "frage": "Was passiert nach dem Abgeben einer Pruefung mit Freitextfragen?",
                    "antworten": [
                        ("Der Versuch bekommt Status 'Ausstehend' bis alle Freitexte bewertet wurden.", True),
                        ("Die Freitextantworten werden automatisch als korrekt gewertet.", False),
                        ("Die Pruefung wird sofort als nicht bestanden markiert.", False),
                    ],
                    "erklaerung": "Freitext-Bewertung erfolgt manuell; erst danach wird der Versuch finalisiert und ggf. ein Zertifikat ausgestellt.",
                },
                "material": None,
            },
        ],
    },
    {
        "titel": "Zahlungen und Auszahlungen",
        "lektionen": [
            {
                "titel": "Zahlungsarten, Checkout und Demo-Modus",
                "typ": Lektion.Typ.TEXT,
                "dauer": 7,
                "ist_vorschau": False,
                "inhalt": (
                    "<h2>Zahlungsarten, Checkout und Demo-Modus</h2>"
                    "<p>ABoroLMS unterstuetzt vier Zahlungsarten, die im Django-Admin unter "
                    "<em>Zahlungseinstellungen</em> aktiviert und mit API-Keys versehen werden:</p>"
                    "<ul>"
                    "<li><strong>Stripe:</strong> Kreditkarte/SEPA via Stripe Checkout Session (API-Key erforderlich)</li>"
                    "<li><strong>Google Pay:</strong> Mobiles Bezahlen ueber Stripe-Integration</li>"
                    "<li><strong>PayPal:</strong> PayPal-Order-API (Client-ID + Secret erforderlich)</li>"
                    "<li><strong>Ueberweisung:</strong> Manuell; Kontoinhaber, IBAN, BIC werden im Checkout angezeigt</li>"
                    "</ul>"
                    "<h3>Checkout-Ablauf</h3>"
                    "<p>Klick auf 'Einschreiben' bei einem kostenpflichtigen Kurs leitet auf "
                    "<code>/kurse/&lt;slug&gt;/checkout/</code> um. "
                    "Der Lernende waehlt eine Zahlungsart, bestaetigt und wird anschliessend "
                    "auf die Statusseite weitergeleitet. "
                    "Nach Bestaetigung wird <code>einschreibung.bezahlt = True</code> gesetzt.</p>"
                    "<h3>Demo-Modus</h3>"
                    "<p>Mit <code>PAYMENT_DEMO_AUTOCONFIRM = True</code> in den Settings "
                    "oder <code>demo_autoconfirm</code> in den Zahlungseinstellungen "
                    "werden alle Zahlungen sofort als bezahlt markiert – "
                    "ideal fuer Tests ohne echte Zahlungsanbieter. "
                    "In der Produktion deaktivieren und echte Webhooks konfigurieren.</p>"
                    "<h3>Hinweis zu Provider-Integrationen</h3>"
                    "<p>Stripe, PayPal und Google Pay sind als Zahlungsarten vorbereitet (Modelle, Settings, UI), "
                    "aber die echte API-Integration mit Webhooks ist ein geplanter naechster Schritt. "
                    "Ueberweisung (manuell) und Demo-Autoconfirm funktionieren vollstaendig.</p>"
                ),
                "uebung": {
                    "frage": "Was bewirkt PAYMENT_DEMO_AUTOCONFIRM = True?",
                    "antworten": [
                        ("Alle Zahlungen werden sofort als bezahlt markiert – kein echter Zahlungsanbieter noetig.", True),
                        ("Die Zahlungsseite wird vollstaendig deaktiviert.", False),
                        ("Lernende koennen nur per Ueberweisung zahlen.", False),
                    ],
                    "erklaerung": "Demo-Autoconfirm ist ausschliesslich fuer Testzwecke gedacht und muss in der Produktion deaktiviert werden.",
                },
                "material": None,
            },
            {
                "titel": "85/15-Aufteilung und Auszahlungsverfolgung",
                "typ": Lektion.Typ.TEXT,
                "dauer": 7,
                "ist_vorschau": False,
                "inhalt": (
                    "<h2>85/15-Aufteilung und Auszahlungsverfolgung</h2>"
                    "<h3>Automatische Aufteilung</h3>"
                    "<p>Bei jeder bestaedigten Zahlung berechnet ABoroLMS automatisch:</p>"
                    "<ul>"
                    "<li><strong>Plattformgebuehr (15%):</strong> Betrag fuer den Plattformbetreiber</li>"
                    "<li><strong>Trainer-Anteil (85%):</strong> Betrag fuer den Kursersteller</li>"
                    "</ul>"
                    "<p>Der Prozentsatz ist in <code>PLATFORM_COMMISSION_PERCENT</code> konfigurierbar. "
                    "Die Methode <code>Zahlung.berechne_aufteilung(betrag)</code> liefert beide Werte als Decimal.</p>"
                    "<h3>Auszahlungsstatus</h3>"
                    "<p>Jede Zahlung traegt einen <code>auszahlungsstatus</code>:</p>"
                    "<ul>"
                    "<li><strong>OFFEN:</strong> Trainer-Anteil noch nicht ausgezahlt</li>"
                    "<li><strong>GEMELDET:</strong> Auszahlung wurde angestossen (Benachrichtigung verschickt)</li>"
                    "<li><strong>AUSGEZAHLT:</strong> Betrag wurde ueberwiesen, Datum gespeichert</li>"
                    "</ul>"
                    "<h3>Superadmin-Auszahlungsuebersicht</h3>"
                    "<p>Unter <code>/superadmin/auszahlungen/</code> sieht der Super-Admin alle Trainer "
                    "mit offenen Betraegen. Er kann dort den Auszahlungsstatus auf 'Gemeldet' oder 'Ausgezahlt' setzen. "
                    "Der OrgAdmin-Dashboard zeigt den Trainer-Anteil ebenfalls (aber ohne Statusaenderung).</p>"
                    "<h3>Demo-Werte</h3>"
                    "<p>Der Demo-Kurs kostet 49 EUR. Davon gehen 7,35 EUR an die Plattform "
                    "und 41,65 EUR an den Trainer. Die Demo-Zahlung ist bereits fuer den Learner-Nutzer vorbelegt.</p>"
                ),
                "uebung": {
                    "frage": "Wie gross ist der Trainer-Anteil bei einem Kurspreis von 100 EUR (Standardeinstellung)?",
                    "antworten": [
                        ("85 EUR", True),
                        ("50 EUR", False),
                        ("100 EUR", False),
                    ],
                    "erklaerung": "85 % gehen an den Trainer, 15 % behaelt die Plattform als Gebuehr ein.",
                },
                "material": (
                    "Zahlungsintegration_Checkliste.txt",
                    (
                        "ABoroLMS Zahlungsintegration – Checkliste\n"
                        "==========================================\n\n"
                        "Demo-Betrieb (sofort nutzbar):\n"
                        "  [x] PAYMENT_DEMO_AUTOCONFIRM = True in Settings\n"
                        "  [x] Zahlungseinstellungen im Admin: demo_autoconfirm aktivieren\n"
                        "  [x] Ueberweisung: IBAN, BIC, Kontoinhaber eintragen\n\n"
                        "Produktionsbetrieb (erfordert API-Keys):\n"
                        "  [ ] Stripe: stripe_aktiv=True, API-Keys eintragen, Webhook konfigurieren\n"
                        "  [ ] PayPal: paypal_aktiv=True, Client-ID + Secret eintragen\n"
                        "  [ ] Google Pay: google_pay_aktiv=True (ueber Stripe)\n"
                        "  [ ] PAYMENT_DEMO_AUTOCONFIRM = False\n\n"
                        "Auszahlungen:\n"
                        "  Trainer-Anteil 85 %, Plattform 15 % (aenderbar ueber PLATFORM_COMMISSION_PERCENT)\n"
                        "  Status: OFFEN -> GEMELDET -> AUSGEZAHLT (manuell im Superadmin)\n"
                    ),
                ),
            },
        ],
    },
    {
        "titel": "Zertifikate (Phase 4)",
        "lektionen": [
            {
                "titel": "Automatische Zertifikatsausstellung",
                "typ": Lektion.Typ.TEXT,
                "dauer": 7,
                "ist_vorschau": False,
                "inhalt": (
                    "<h2>Automatische Zertifikatsausstellung</h2>"
                    "<p>Sobald ein Pruefungsversuch abgeschlossen und bestanden ist, "
                    "stellt ABoroLMS automatisch ein Zertifikat aus – "
                    "ohne manuelles Eingreifen.</p>"
                    "<h3>Technischer Ablauf</h3>"
                    "<ol>"
                    "<li><code>werte_versuch_aus(versuch)</code> berechnet Punkte und Prozent.</li>"
                    "<li>Wenn <code>versuch.bestanden == True</code> und Status ist <em>ABGESCHLOSSEN</em>, "
                    "wird <code>stelle_zertifikat_aus(versuch)</code> aufgerufen.</li>"
                    "<li><code>Zertifikat.objects.get_or_create(nutzer=..., pruefungsversuch=...)</code> "
                    "erstellt das Zertifikat idempotent – kein Duplikat bei Mehrfachaufruf.</li>"
                    "<li>Das Zertifikat erhaelt einen eindeutigen UUID-Code, der fuer die Verifikations-URL genutzt wird.</li>"
                    "</ol>"
                    "<h3>Zertifikat-Modell</h3>"
                    "<p>Ein <code>Zertifikat</code>-Objekt verbindet:</p>"
                    "<ul>"
                    "<li><code>nutzer</code> – Wer hat bestanden?</li>"
                    "<li><code>pruefungsversuch</code> – Welcher Versuch hat das Zertifikat ausgeloest?</li>"
                    "<li><code>code</code> – Eindeutiger UUID, nicht editierbar</li>"
                    "<li><code>ausgestellt_am</code> – Zeitstempel (auto)</li>"
                    "<li><code>ist_widerrufen</code> – Kann der Super-Admin im Admin setzen</li>"
                    "</ul>"
                    "<h3>Im Dashboard und Ergebnisbildschirm</h3>"
                    "<p>Nach der Pruefung erscheint direkt auf der Ergebnisseite "
                    "ein 'Zertifikat PDF' und 'Verifizieren'-Button. "
                    "Im Dashboard sind die letzten drei Zertifikate sichtbar, "
                    "unter <code>/zertifikate/</code> alle auf einmal.</p>"
                ),
                "uebung": {
                    "frage": "Wann wird ein Zertifikat automatisch ausgestellt?",
                    "antworten": [
                        ("Wenn der Pruefungsversuch abgeschlossen und bestanden ist.", True),
                        ("Bei jeder Einschreibung in einen Kurs.", False),
                        ("Wenn der Trainer es manuell im Admin anlegt.", False),
                    ],
                    "erklaerung": "stelle_zertifikat_aus() wird automatisch am Ende von werte_versuch_aus() aufgerufen, wenn bestanden=True.",
                },
                "material": None,
            },
            {
                "titel": "PDF-Download, QR-Code und oeffentliche Verifikation",
                "typ": Lektion.Typ.TEXT,
                "dauer": 7,
                "ist_vorschau": False,
                "inhalt": (
                    "<h2>PDF-Download, QR-Code und oeffentliche Verifikation</h2>"
                    "<h3>PDF-Generierung mit WeasyPrint</h3>"
                    "<p>Unter <code>/zertifikate/&lt;uuid&gt;/pdf/</code> generiert ABoroLMS ein A4-Querformat-PDF. "
                    "Die Gestaltung kommt aus dem Django-Template <code>certificates/pdf.html</code> "
                    "mit vollstaendiger Inline-CSS-Formatierung (keine externen CDN-Ressourcen). "
                    "WeasyPrint rendert daraus ein druckbares PDF mit den Farben und dem Logo der Organisation.</p>"
                    "<h3>Windows-Hinweis</h3>"
                    "<p>WeasyPrint benoetigt unter Windows die <strong>GTK3-Runtime</strong>. "
                    "Ohne diese Bibliotheken erscheint beim PDF-Abruf eine klare Fehlermeldung mit Installationslink. "
                    "Unter Linux (Produktionsumgebung) sind die GTK-Bibliotheken standardmaessig verfuegbar.</p>"
                    "<h3>QR-Code-Einbettung</h3>"
                    "<p>Beim PDF-Export wird per <code>qrcode</code>-Library ein QR-Code generiert, "
                    "als PNG in Base64 kodiert und direkt in das HTML-Template eingebettet (<code>data:image/png;base64,...</code>). "
                    "Der QR-Code zeigt auf die oeffentliche Verifikations-URL.</p>"
                    "<h3>Oeffentliche Verifikation</h3>"
                    "<p>Die URL <code>/zertifikate/verify/&lt;uuid&gt;/</code> ist ohne Login zugaenglich. "
                    "Dritte koennen damit ein Zertifikat pruefen: "
                    "Ist es gueltig? Fuer wen wurde es ausgestellt? Wann? Mit welchem Ergebnis? "
                    "Bei widerrufenen Zertifikaten erscheint ein Hinweis 'Nicht mehr gueltig'.</p>"
                    "<h3>Sicherheit</h3>"
                    "<p>Der PDF-Download ist nur fuer den Zertifikatsinhaber zugreifbar (<code>nutzer=request.user</code>). "
                    "Die Verifikationsseite ist oeffentlich, zeigt aber nur Informationen zum Zertifikat, "
                    "keine weiteren Nutzerdaten.</p>"
                ),
                "uebung": {
                    "frage": "Wer darf das Zertifikat als PDF herunterladen?",
                    "antworten": [
                        ("Nur der Zertifikatsinhaber selbst (eingeloggt).", True),
                        ("Jeder, der die UUID kennt.", False),
                        ("Nur der Super-Admin.", False),
                    ],
                    "erklaerung": "Der PDF-Download prueft nutzer=request.user; die Verifikationsseite ist dagegen oeffentlich.",
                },
                "material": None,
            },
            {
                "titel": "Zertifikats-Design pro Organisation individualisieren",
                "typ": Lektion.Typ.TEXT,
                "dauer": 6,
                "ist_vorschau": False,
                "inhalt": (
                    "<h2>Zertifikats-Design pro Organisation individualisieren</h2>"
                    "<p>Jede Organisation kann das Layout ihrer Zertifikate eigenstaendig gestalten. "
                    "Das <strong>ZertifikatDesign</strong>-Modell speichert organisationsspezifische Einstellungen, "
                    "die das PDF-Template dynamisch anwendet.</p>"
                    "<h3>Konfigurierbare Design-Felder</h3>"
                    "<ul>"
                    "<li><strong>Hauptfarbe</strong> – Rahmen, Titel und Organisationsname im Zertifikat (Standard: ABoroLMS-Blau #12315f)</li>"
                    "<li><strong>Akzentfarbe</strong> – Name des Inhabers, Trennlinie und Eckverzierungen (Standard: ABoroLMS-Orange #f28c28)</li>"
                    "<li><strong>Anzeigename</strong> – Optionale Ueberschreibung des Organisationsnamens auf dem Zertifikat</li>"
                    "<li><strong>Fusszeile</strong> – Beliebiger Zusatztext in der unteren Ecke (z.B. Standort, Rechtsform)</li>"
                    "<li><strong>Unterschriftenzeile</strong> – Beschriftung unter einer Linie, z.B. 'Geschaeftsfuehrung'</li>"
                    "<li><strong>Logo</strong> – PNG oder JPG, wird oben im Zertifikat eingebettet (Base64 fuer PDF-Export)</li>"
                    "</ul>"
                    "<h3>Technische Umsetzung</h3>"
                    "<p>Das Modell <code>ZertifikatDesign</code> hat eine OneToOne-Beziehung zu <code>Organisation</code>. "
                    "Beim PDF-Export laedt <code>generiere_zertifikat_pdf()</code> das Design per "
                    "<code>get_or_create(organisation=org)</code> – wenn noch kein Design existiert, "
                    "werden die Standardwerte (ABoroLMS-Branding) verwendet. "
                    "Die Farben werden als Template-Variablen direkt in den <code>&lt;style&gt;</code>-Block eingebettet.</p>"
                    "<h3>Zugang fuer den Org-Admin</h3>"
                    "<p>Der Org-Admin erreicht das Design-Formular unter "
                    "<code>/organisationen/&lt;slug&gt;/zertifikat-design/</code> "
                    "oder ueber den Button 'Zertifikat-Design' im OrgAdmin-Dashboard. "
                    "Eine Farbvorschau zeigt in Echtzeit, wie die Farbwahl auf das Zertifikat wirkt.</p>"
                    "<h3>Super-Admin und Django-Admin</h3>"
                    "<p>Der Super-Admin kann alle <code>ZertifikatDesign</code>-Objekte im Django-Admin einsehen und bearbeiten. "
                    "Damit lassen sich Designs auch fuer Organisationen setzen, deren Org-Admin sich noch nicht eingerichtet hat.</p>"
                ),
                "uebung": {
                    "frage": "Welches Modell speichert das Zertifikats-Design einer Organisation?",
                    "antworten": [
                        ("ZertifikatDesign (OneToOne zu Organisation)", True),
                        ("Das Zertifikat-Modell selbst speichert alle Design-Felder.", False),
                        ("Design-Einstellungen sind nur im Django-Admin konfigurierbar, nicht im Modell.", False),
                    ],
                    "erklaerung": "ZertifikatDesign hat eine OneToOne-Beziehung zur Organisation; get_or_create stellt sicher, dass immer ein Standarddesign existiert.",
                },
                "material": (
                    "Zertifikat_Design_Referenz.txt",
                    (
                        "ABoroLMS – Zertifikats-Design Referenz\n"
                        "========================================\n\n"
                        "Modell: certificates.ZertifikatDesign\n"
                        "Beziehung: OneToOneField -> organisations.Organisation\n\n"
                        "Felder:\n"
                        "  primary_color    -> Hauptfarbe (Standard: #12315f)\n"
                        "  secondary_color  -> Akzentfarbe (Standard: #f28c28)\n"
                        "  org_display_name -> Anzeigename (leer = Organisationsname)\n"
                        "  footer_text      -> Fusszeilen-Zusatztext\n"
                        "  signature_line   -> Unterschriftenzeile\n"
                        "  logo             -> ImageField -> upload_to='zertifikat_logos/'\n\n"
                        "Design-URL fuer Org-Admin:\n"
                        "  /organisationen/<slug>/zertifikat-design/\n\n"
                        "PDF-Service (services.py):\n"
                        "  design, _ = ZertifikatDesign.objects.get_or_create(organisation=org)\n"
                        "  Farben werden als Template-Variablen in das PDF-Template uebergeben.\n"
                        "  Logo wird als Base64-Daten-URL eingebettet (kein externer Datei-Zugriff noetig).\n"
                    ),
                ),
            },
        ],
    },
    {
        "titel": "SaaS und Administration",
        "lektionen": [
            {
                "titel": "Org-Admin: E-Mail, Design und eigene Startseite",
                "typ": Lektion.Typ.TEXT,
                "dauer": 8,
                "ist_vorschau": False,
                "inhalt": (
                    "<h2>Org-Admin: E-Mail, Design und eigene Startseite</h2>"
                    "<p>Jede Organisation kann ABoroLMS vollstaendig individuell gestalten – "
                    "ohne Eingriff des Plattform-Betreibers. Der Org-Admin findet alle Einstellungen "
                    "im OrgAdmin-Dashboard ueber die Schaltflaechen oben rechts.</p>"
                    "<h3>E-Mail-Konfiguration (/organisationen/&lt;slug&gt;/email-konfiguration/)</h3>"
                    "<p>Jede Organisation kann einen eigenen SMTP-Server eintragen. "
                    "Alle automatischen E-Mails (Anmeldedaten, Kaufbestaetigung, Rechnungen) "
                    "werden dann ueber diesen Server versendet statt ueber den Plattform-Standard.</p>"
                    "<ul>"
                    "<li><strong>Absendername + E-Mail</strong> – z.B. 'Meine Firma Academy &lt;academy@meinefirma.de&gt;'</li>"
                    "<li><strong>Antwort-E-Mail (Reply-To)</strong> – zweite Adresse fuer Support-Antworten</li>"
                    "<li><strong>SMTP-Host, Port, User, Passwort</strong> – Serververbindung</li>"
                    "<li><strong>TLS (Port 587) oder SSL (Port 465)</strong> – Verschluesselung; nie beide gleichzeitig</li>"
                    "<li><strong>Aktivierungsschalter</strong> – deaktiviert nutzt die Org den Plattform-SMTP</li>"
                    "</ul>"
                    "<h3>Organisations-Design (/organisationen/&lt;slug&gt;/design/)</h3>"
                    "<p>Das Modell <code>OrganisationDesign</code> steuert Farben und Logo, "
                    "die fuer alle eingeloggten Nutzer dieser Organisation im gesamten LMS sichtbar sind.</p>"
                    "<ul>"
                    "<li><strong>Primaerfarbe</strong> – Navigation, Ueberschriften, Rahmen (CSS: <code>--aboro-blue</code>)</li>"
                    "<li><strong>Akzentfarbe</strong> – Buttons, Fortschrittsbalken (CSS: <code>--aboro-orange</code>)</li>"
                    "<li><strong>Navigations-Farbe</strong> – Hintergrundfarbe der Navbar</li>"
                    "<li><strong>Seiten-Hintergrundfarbe</strong> – Seitenbackground</li>"
                    "<li><strong>Logo</strong> – Wird in der Navbar angezeigt und ersetzt den Organisations-Textnamen</li>"
                    "<li><strong>Favicon</strong> – Browser-Tab-Icon</li>"
                    "<li><strong>Eigenes CSS</strong> – Vollstaendige CSS-Freiheit fuer erfahrene Nutzer</li>"
                    "</ul>"
                    "<p>Die Farben werden als CSS-Variablen-Override direkt im <code>&lt;head&gt;</code> des Base-Templates injiziert. "
                    "Kein Template muss geklont werden.</p>"
                    "<h3>Eigene Startseite (/organisationen/&lt;slug&gt;/startseite/)</h3>"
                    "<p>Unter <code>/o/&lt;slug&gt;/</code> hat jede Organisation eine oeffentliche Landing Page. "
                    "Diese kann per WYSIWYG-Editor (Quill) frei gestaltet werden.</p>"
                    "<ul>"
                    "<li><strong>Hero-Bereich</strong> – Grosses Bild, Ueberschrift, Unterzeile und CTA-Button</li>"
                    "<li><strong>WYSIWYG-Inhalt</strong> – Texte, Bilder, Tabellen, Listen frei positionierbar</li>"
                    "<li><strong>Kurse</strong> – Die 6 neuesten Kurse werden automatisch angezeigt</li>"
                    "<li><strong>Aktivierungsschalter</strong> – Solange deaktiviert, ist die Seite nicht sichtbar</li>"
                    "</ul>"
                    "<p>Die Startseiten-URL kann als eigener Einstiegspunkt beworben werden, z.B. "
                    "auf Visitenkarten oder in E-Mail-Signaturen.</p>"
                ),
                "uebung": {
                    "frage": "Was passiert, wenn eine Organisation keinen eigenen SMTP aktiviert hat?",
                    "antworten": [
                        ("Alle E-Mails gehen ueber den Plattform-Standard-SMTP.", True),
                        ("E-Mails koennen gar nicht versendet werden.", False),
                        ("Nur der Superadmin kann E-Mails versenden.", False),
                    ],
                    "erklaerung": "Der org-spezifische SMTP ist optional; wenn nicht aktiv, faellt das System auf den konfigurierten Plattform-SMTP zurueck.",
                },
                "material": (
                    "Org_Konfiguration_Checkliste.txt",
                    (
                        "ABoroLMS – Organisations-Konfiguration Checkliste\n"
                        "===================================================\n\n"
                        "E-Mail-Konfiguration:\n"
                        "  URL: /organisationen/<slug>/email-konfiguration/\n"
                        "  Felder: absender_name, absender_email, antwort_email\n"
                        "          smtp_host, smtp_port, smtp_user, smtp_password\n"
                        "          smtp_use_tls (587) ODER smtp_use_ssl (465)\n"
                        "  Tipp: Gmail -> App-Passwort verwenden (2FA aktiv)\n\n"
                        "Organisations-Design:\n"
                        "  URL: /organisationen/<slug>/design/\n"
                        "  Felder: primary_color  -> CSS --aboro-blue\n"
                        "          secondary_color -> CSS --aboro-orange\n"
                        "          navbar_farbe    -> CSS --aboro-blue-dark\n"
                        "          hintergrund_farbe -> CSS --aboro-bg\n"
                        "          logo, favicon, custom_css\n"
                        "  Gilt fuer: Navbar, Kurskatalog, Kursseiten, Dashboard\n\n"
                        "Eigene Startseite:\n"
                        "  URL: /organisationen/<slug>/startseite/ (Editor)\n"
                        "       /o/<slug>/ (oeffentliche Ansicht)\n"
                        "  Felder: aktiv, hero_titel, hero_untertitel,\n"
                        "          hero_bild, hero_button_text, inhalt (WYSIWYG)\n"
                        "  Automatisch: letzte 6 Kurse werden eingeblendet\n\n"
                        "Zertifikats-Design:\n"
                        "  URL: /organisationen/<slug>/zertifikat-design/\n"
                        "  Felder: primary_color, secondary_color, logo, footer_text,\n"
                        "          org_display_name, signature_line\n"
                    ),
                ),
            },
            {
                "titel": "Superadmin: Plattformuebersicht und Auszahlungen",
                "typ": Lektion.Typ.TEXT,
                "dauer": 7,
                "ist_vorschau": False,
                "inhalt": (
                    "<h2>Superadmin: Plattformuebersicht und Auszahlungen</h2>"
                    "<p>Der Super-Admin sieht im Navigations-Dropdown <em>Superadmin</em> zwei Bereiche:</p>"
                    "<h3>Organisationsuebersicht</h3>"
                    "<p>Unter <code>/superadmin/organisationen/</code> sind alle registrierten Mandanten sichtbar:</p>"
                    "<ul>"
                    "<li>Name und Slug</li>"
                    "<li>Lizenz-Badge (Basic / Pro / Enterprise, farblich markiert)</li>"
                    "<li>Mitgliederanzahl und Kurszahl (inkl. Lizenzlimit)</li>"
                    "<li>Aktivstatus und Link zum OrgAdmin-Dashboard</li>"
                    "</ul>"
                    "<p>Lizenztyp und Limits werden im Django-Admin unter <em>Organisationen</em> geaendert.</p>"
                    "<h3>Auszahlungsuebersicht</h3>"
                    "<p>Unter <code>/superadmin/auszahlungen/</code> sieht der Super-Admin alle Trainer "
                    "mit offenem Auszahlungsbetrag. "
                    "Er kann den Status auf 'Gemeldet' oder 'Ausgezahlt' setzen und so die Buchhaltung abbilden. "
                    "Gezahlte Betraege werden mit Datum gespeichert.</p>"
                    "<h3>Django-Admin</h3>"
                    "<p>Der vollstaendige Django-Admin unter <code>/admin/</code> erlaubt dem Super-Admin "
                    "direkten Zugriff auf alle Modelle: Nutzer, Organisationen, Kurse, Pruefungen, "
                    "Zertifikate (inkl. Widerruf), Zahlungen und Einladungen.</p>"
                    "<p><strong>Tipp:</strong> Fuer die Produktion den Admin-Pfad absichern "
                    "(z.B. durch IP-Whitelist oder separaten Subdomain-Proxy).</p>"
                ),
                "uebung": {
                    "frage": "Wo aendert der Super-Admin den Lizenztyp einer Organisation?",
                    "antworten": [
                        ("Im Django-Admin unter Organisationen.", True),
                        ("Im OrgAdmin-Dashboard direkt.", False),
                        ("Per CSV-Dateiupload.", False),
                    ],
                    "erklaerung": "Lizenzaenderungen sind Administrations-Aufgaben und laufen ueber den Django-Admin.",
                },
                "material": None,
            },
            {
                "titel": "Installationsskripte und naechste Schritte",
                "typ": Lektion.Typ.TEXT,
                "dauer": 6,
                "ist_vorschau": False,
                "inhalt": (
                    "<h2>Installationsskripte und naechste Schritte</h2>"
                    "<h3>Geplante Installationsarten</h3>"
                    "<p>ABoroLMS ist als Selfhosting-Produkt geplant. Die Installationsskripte werden auf GitHub bereitgestellt:</p>"
                    "<ul>"
                    "<li><strong>Linux + Apache2:</strong> Bash-Skript fuer Debian/Ubuntu mit Gunicorn und Apache2 als Reverse Proxy</li>"
                    "<li><strong>Linux + Nginx:</strong> Alternative mit Nginx und systemd-Service</li>"
                    "<li><strong>Windows + IIS:</strong> PowerShell-Skript fuer Windows Server mit IIS als Proxy</li>"
                    "</ul>"
                    "<h3>Produktions-Checkliste</h3>"
                    "<ul>"
                    "<li>SECRET_KEY sicher setzen (lange Zufallszeichenkette)</li>"
                    "<li>DEBUG = False in Produktion</li>"
                    "<li>ALLOWED_HOSTS auf echte Domain(en) begrenzen</li>"
                    "<li>PostgreSQL statt SQLite verwenden</li>"
                    "<li>PAYMENT_DEMO_AUTOCONFIRM = False</li>"
                    "<li>GTK3-Runtime installieren (fuer WeasyPrint-PDF-Export)</li>"
                    "<li>MEDIA_ROOT auf persistentes Verzeichnis setzen</li>"
                    "<li>E-Mail-Backend konfigurieren (SMTP) fuer Einladungen</li>"
                    "</ul>"
                    "<h3>Offene Punkte und Roadmap</h3>"
                    "<ul>"
                    "<li>Echte Stripe/PayPal-Integration mit Webhooks</li>"
                    "<li>E-Mail-Versand fuer Einladungen (Token-Link per Mail)</li>"
                    "<li>Einladungs-Annahme-View fuer eingeladene Nutzer</li>"
                    "<li>Kursabschluss-Zertifikate (ohne Pruefung, nur Fortschritt 100%)</li>"
                    "<li>Installationsskripte fuer Linux und Windows</li>"
                    "</ul>"
                    "<h3>Demo zuruecksetzen</h3>"
                    "<p>Mit <code>python manage.py create_demo_data</code> werden alle Demo-Inhalte "
                    "zurueckgesetzt und neu erstellt. "
                    "Bestehende Nutzer und die Demo-Organisation bleiben erhalten; "
                    "Kursinhalte, Fragen und Pruefungen werden aktualisiert.</p>"
                ),
                "uebung": {
                    "frage": "Welche Datenbank wird fuer den Produktionsbetrieb empfohlen?",
                    "antworten": [
                        ("PostgreSQL", True),
                        ("SQLite (Standard Django)", False),
                        ("MongoDB", False),
                    ],
                    "erklaerung": "SQLite ist fuer Entwicklung und Demo geeignet; fuer Produktion empfiehlt sich PostgreSQL wegen Stabilitaet und Gleichzeitigkeit.",
                },
                "material": (
                    "Produktions_Checkliste.txt",
                    (
                        "ABoroLMS Produktions-Checkliste\n"
                        "================================\n\n"
                        "Sicherheit:\n"
                        "  [ ] SECRET_KEY = lange, zufaellige Zeichenkette (mind. 50 Zeichen)\n"
                        "  [ ] DEBUG = False\n"
                        "  [ ] ALLOWED_HOSTS = ['deine-domain.de']\n"
                        "  [ ] Admin-Pfad absichern (IP-Whitelist oder anderer Pfad)\n\n"
                        "Datenbank:\n"
                        "  [ ] PostgreSQL konfigurieren (psycopg2-binary installiert)\n"
                        "  [ ] Migrationen ausfuehren: python manage.py migrate\n\n"
                        "Medien und Statik:\n"
                        "  [ ] MEDIA_ROOT auf persistentes Verzeichnis setzen\n"
                        "  [ ] python manage.py collectstatic\n"
                        "  [ ] Webserver so konfigurieren, dass /media/ und /static/ direkt ausgeliefert werden\n\n"
                        "E-Mail:\n"
                        "  [ ] EMAIL_BACKEND = django.core.mail.backends.smtp.EmailBackend\n"
                        "  [ ] SMTP-Server, Port, User und Passwort setzen\n\n"
                        "Zahlungen:\n"
                        "  [ ] PAYMENT_DEMO_AUTOCONFIRM = False\n"
                        "  [ ] Stripe API-Keys + Webhook eintragen\n"
                        "  [ ] PayPal Client-ID + Secret eintragen (optional)\n\n"
                        "PDF-Export:\n"
                        "  [ ] GTK3-Runtime installieren (Linux: apt install libpango-1.0-0)\n"
                        "  [ ] WeasyPrint-Test: python -c 'from weasyprint import HTML'\n"
                    ),
                ),
            },
        ],
    },
]

# ---------------------------------------------------------------------------
# Zertifikatspruefung: 13 Fragen, 10 werden gezogen
# ---------------------------------------------------------------------------
PRUEFUNGSFRAGEN = [
    {
        "typ": Frage.Typ.SINGLE_CHOICE,
        "text": "Was beschreibt das Betriebsmodell von ABoroLMS am besten?",
        "erklaerung": "Richtig ist Selfhosting: Der Betreiber installiert ABoroLMS auf einem eigenen Server und kontrolliert die gespeicherten Daten. Die Anwendung wird im Browser genutzt. Eine ausschliessliche Bereitstellung als fremdgehosteter Cloud-Dienst oder Desktop-Anwendung beschreibt dieses Betriebsmodell nicht.",
        "punkte": 1,
        "antworten": [
            ("Selfhosting auf eigenem Server mit vollstaendiger Datenkontrolle.", True),
            ("Rein cloudbasiert, Daten liegen bei ABoroSoft.", False),
            ("Nur als Desktop-Applikation ohne Browser nutzbar.", False),
            ("Monatliches Abonnement ohne eigene Installation.", False),
        ],
    },
    {
        "typ": Frage.Typ.MULTIPLE_CHOICE,
        "text": "Welche Apps gehoeren zur ABoroLMS-Kernarchitektur?",
        "erklaerung": "accounts verwaltet Nutzer und Rollen, certificates die Zertifikate und deren PDF-Ausgabe, payments die Zahlungen und Umsatzaufteilung. wordpress ist keine Django-App dieser Plattform. Fuer die volle Punktzahl muessen alle drei richtigen Antworten und keine falsche Antwort gewaehlt sein; die automatische Bewertung vergibt keine Teilpunkte.",
        "punkte": 2,
        "antworten": [
            ("accounts – Nutzer, Rollen, UserProfile", True),
            ("certificates – Zertifikate und PDF-Export", True),
            ("payments – Zahlungsarten und 85/15-Aufteilung", True),
            ("wordpress – CMS fuer Blog-Beitraege", False),
        ],
    },
    {
        "typ": Frage.Typ.SINGLE_CHOICE,
        "text": "Welche Rolle erstellt Fragenkataloge und konfiguriert Pruefungen?",
        "erklaerung": "Diese Aufgaben gehoeren zur Trainerrolle. Pruefer bewerten insbesondere offene Antworten; Lernende bearbeiten Kurse und Pruefungen. Gemeint ist die fachlich zustaendige Rolle, auch wenn hoeher berechtigte Administratoren ebenfalls Zugriff haben koennen.",
        "punkte": 1,
        "antworten": [
            ("Trainer", True),
            ("Lernender", False),
            ("Pruefer", False),
            ("AnonymousUser", False),
        ],
    },
    {
        "typ": Frage.Typ.WAHR_FALSCH,
        "text": "Ein Nutzer darf in verschiedenen Organisationen unterschiedliche Rollen haben.",
        "erklaerung": "Die Aussage ist wahr. UserProfile verknuepft einen Nutzer mit einer Organisation und einer Rolle. Deshalb kann dieselbe Person beispielsweise Trainer in Organisation A und Lernender in Organisation B sein. Die Berechtigung muss im jeweiligen Organisationskontext geprueft werden.",
        "punkte": 1,
        "antworten": [
            ("Wahr", True),
            ("Falsch", False),
        ],
    },
    {
        "typ": Frage.Typ.MULTIPLE_CHOICE,
        "text": "Welche Aussagen zum Lernfortschritt sind korrekt?",
        "erklaerung": "Richtig sind der Prozentwert aus abgeschlossenen und gesamten Lektionen sowie der eigene Fortschritt je Einschreibung. Ein Abschluss erzeugt einen Fortschrittseintrag und loescht keine Lektion. Das Beantworten einer Uebungsfrage allein schliesst keine Lektion ab. Nur die vollstaendig richtige Auswahl erhaelt die zwei Punkte.",
        "punkte": 2,
        "antworten": [
            ("Der Fortschritt wird als Prozentwert (abgeschlossene/Gesamt-Lektionen) gespeichert.", True),
            ("Lektionsabschluss loescht die Lektion aus dem Kurs.", False),
            ("Jede Einschreibung hat einen eigenen Fortschritts-Zaehlstand.", True),
            ("Uebungsfragen beeinflussen den Kursfortschritt direkt.", False),
        ],
    },
    {
        "typ": Frage.Typ.SINGLE_CHOICE,
        "text": "Wie berechnet ABoroLMS den Trainer-Anteil bei einem Kurspreis von 200 EUR?",
        "erklaerung": "Bei der hier zugrunde gelegten Aufteilung 85/15 betraegt der Trainer-Anteil 200 EUR mal 0,85 = 170 EUR. Die verbleibenden 30 EUR sind der Plattform-Anteil. Die Frage bezieht sich auf diese Aufteilung, nicht auf einen abweichend konfigurierten Provisionssatz.",
        "punkte": 2,
        "antworten": [
            ("170 EUR (85 %)", True),
            ("100 EUR (50 %)", False),
            ("200 EUR (100 %)", False),
            ("30 EUR (15 %)", False),
        ],
    },
    {
        "typ": Frage.Typ.SINGLE_CHOICE,
        "text": "Wann wird ein Zertifikat automatisch ausgestellt?",
        "erklaerung": "Erforderlich sind ein abgeschlossener und bestandener Pruefungsversuch. Offene Freitext- oder Szenariobewertungen muessen zuvor erledigt sein. Einschreibung und Zeitablauf allein belegen keinen Pruefungserfolg; eine manuelle Anlage ist kein automatischer Ausstellungszeitpunkt.",
        "punkte": 1,
        "antworten": [
            ("Wenn der Pruefungsversuch abgeschlossen und bestanden ist.", True),
            ("Bei jeder Einschreibung in einen Kurs.", False),
            ("Wenn der Trainer es manuell im Django-Admin anlegt.", False),
            ("Nach Ablauf des Zeitlimits.", False),
        ],
    },
    {
        "typ": Frage.Typ.MULTIPLE_CHOICE,
        "text": "Welche Fragetypen werden von ABoroLMS unterstuetzt?",
        "erklaerung": "SC (Single Choice), FT (Freitext) und ZO (Zuordnung) sind unterstuetzte Fragetypen und hier auszuwaehlen. BI ist kein angebotener Fragetyp. Zusaetzlich existieren Multiple Choice, Wahr/Falsch und Szenario. Die automatische Bewertung gibt die volle Punktzahl nur fuer alle richtigen Optionen ohne falsche Auswahl.",
        "punkte": 2,
        "antworten": [
            ("SC – Single Choice", True),
            ("FT – Freitext", True),
            ("ZO – Zuordnung", True),
            ("BI – Bilderkennung durch KI", False),
        ],
    },
    {
        "typ": Frage.Typ.FREITEXT,
        "text": (
            "Erklaere in eigenen Worten, wie ABoroLMS Mandantenfaehigkeit technisch umsetzt – "
            "ohne separate Datenbanken je Organisation zu benoetigen."
        ),
        "erklaerung": "Erwartet wird eine gemeinsame Datenbank mit gemeinsamem Schema. Organisationsbezogene Objekte sind ueber Fremdschluessel direkt oder indirekt einer Organisation zugeordnet. UserProfile verbindet Nutzer, Organisation und Rolle. Abfragen und Berechtigungspruefungen begrenzen den Zugriff auf die aktive Organisation; allein eine Organisations-ID oder ein URL-Slug bietet noch keine Zugriffssicherheit. Sinngemaesse Beschreibungen und passende Beispiele sind ausreichend, exakte Klassenbezeichnungen sind nicht erforderlich.",
        "bewertungshinweis": "<p>1 Punkt: gemeinsame Datenbank und gemeinsames Schema statt eigener Datenbank je Mandant.</p><p>1 Punkt: Zuordnung von Daten zur Organisation ueber Beziehungen/Fremdschluessel; die Mitgliedschaft bzw. Rolle des Nutzers ist organisationsbezogen.</p><p>1 Punkt: organisationsbezogene Filter und Berechtigungspruefungen verhindern den Zugriff auf fremde Daten.</p><p>Je Kriterium 0,5 Punkte bei teilweise richtiger, aber unvollstaendiger Beschreibung; 0 Punkte bei fehlender oder falscher Aussage. Maximal 3 Punkte. Gleichwertige Formulierungen anerkennen, denselben Aspekt nicht doppelt bewerten.</p>",
        "punkte": 3,
        "antworten": [],
    },
    {
        "typ": Frage.Typ.ZUORDNUNG,
        "text": "Ordne jede Rolle ihrer Hauptzustaendigkeit zu.",
        "erklaerung": "Super-Admins betreiben die gesamte Plattform; Org-Admins verwalten ihre Organisation und deren Mitglieder. Trainer erstellen Lern- und Pruefungsinhalte, Pruefer bewerten offene Antworten, Lernende absolvieren Kurse und Pruefungen. Bewertet wird die Hauptzustaendigkeit, auch wenn Rollen kombiniert werden koennen. Bei fuenf Paaren und drei Gesamtpunkten ergibt jedes korrekte Paar 0,6 Punkte.",
        "punkte": 3,
        "zuordnungen": [
            ("Super-Admin", "Plattform betreiben und alle Daten verwalten"),
            ("Org-Admin", "Mitglieder einladen und Organisation verwalten"),
            ("Trainer", "Kurse und Fragenkataloge erstellen"),
            ("Pruefer", "Freitextantworten manuell bewerten"),
            ("Lernender", "An Kursen teilnehmen und Pruefungen ablegen"),
        ],
    },
    {
        "typ": Frage.Typ.SINGLE_CHOICE,
        "text": "Was passiert, wenn das Nutzerlimit (max_nutzer) einer Organisation erreicht ist?",
        "erklaerung": "Die Limitpruefung verhindert weitere Einladungen. Bereits vorhandene Nutzer und Kurse werden dadurch nicht geloescht oder deaktiviert. Eine Erhoehung des Limits muss administrativ erfolgen; es gibt kein automatisches Lizenz-Upgrade.",
        "punkte": 1,
        "antworten": [
            ("Weitere Einladungen werden gesperrt, bestehende Nutzer bleiben unveraendert.", True),
            ("Alle Nutzer verlieren sofort ihren Zugang.", False),
            ("Der Kurs wird automatisch deaktiviert.", False),
            ("Der Org-Admin erhaelt automatisch einen Pro-Upgrade.", False),
        ],
    },
    {
        "typ": Frage.Typ.WAHR_FALSCH,
        "text": "Die oeffentliche Zertifikats-Verifikationsseite erfordert einen Login.",
        "erklaerung": "Die Aussage ist falsch. Die oeffentliche Verifikation erlaubt Dritten, ein Zertifikat ueber dessen Verifikationslink zu pruefen. Sie ist vom geschuetzten persoenlichen PDF-Download zu unterscheiden, fuer den eine Zugriffspruefung erfolgt.",
        "punkte": 1,
        "antworten": [
            ("Falsch", True),
            ("Wahr", False),
        ],
    },
    {
        "typ": Frage.Typ.SINGLE_CHOICE,
        "text": "Welches Modell speichert das individuelle Zertifikats-Design einer Organisation in ABoroLMS?",
        "erklaerung": "ZertifikatDesign ist ueber eine OneToOne-Beziehung mit der Organisation verbunden. Dadurch hat jede Organisation einen eigenen Design-Datensatz, beispielsweise fuer Farben und Unterschriften. Dafuer werden weder separate Datenbanktabellen je Organisation noch ausschliesslich CSS-Dateien verwendet.",
        "punkte": 1,
        "antworten": [
            ("ZertifikatDesign mit OneToOneField zu Organisation", True),
            ("Das Zertifikat-Modell selbst hat alle Design-Felder.", False),
            ("Design wird ausschliesslich per CSS-Datei konfiguriert.", False),
            ("Jede Organisation hat eine eigene Datenbank-Tabelle fuer das Design.", False),
        ],
    },
]


class Command(BaseCommand):
    help = "Erstellt / aktualisiert die Demo-Organisation mit vollstaendigen LMS-Inhalten."

    def handle(self, *args, **options):
        if not django_settings.DEBUG and not getattr(django_settings, "DEMO_DATA_ALLOW_PRODUCTION", False):
            raise CommandError(
                "Demo-Daten duerfen nur in der Entwicklungsumgebung (DEBUG=True) oder mit DEMO_DATA_ALLOW_PRODUCTION=True erstellt werden."
            )
        self._setup_gruppen_und_nutzer()
        organisation = self._setup_organisation()
        self._setup_zahlungseinstellungen()
        self._setup_org_konfiguration(organisation)
        kurs = self._setup_kurs(organisation)
        katalog, pruefung = self._setup_pruefung(organisation, kurs)
        self._setup_kursinhalte(kurs)
        self._setup_learner_zugang(kurs)
        self._setup_pruefungsfragen(katalog)
        self.stdout.write(self.style.SUCCESS("Demo-Daten wurden erstellt / aktualisiert."))

    # ------------------------------------------------------------------
    def _setup_gruppen_und_nutzer(self):
        User = get_user_model()
        for role in Rolle:
            Group.objects.get_or_create(name=role.value)

        superadmin, _ = User.objects.get_or_create(
            username="superadmin",
            defaults={
                "email": "superadmin@example.com",
                "first_name": "Super",
                "last_name": "Admin",
                "is_staff": True,
                "is_superuser": True,
            },
        )
        superadmin.is_staff = True
        superadmin.is_superuser = True
        superadmin.set_password("ChangeMe123!")
        superadmin.save()
        superadmin.groups.add(Group.objects.get(name=Rolle.SUPERADMIN.value))

        User.objects.filter(username="orgadmin").delete()
        for username, rolle in [
            ("exam_operator", Rolle.EXAM_OPERATOR),
            ("trainer", Rolle.TRAINER),
            ("examiner", Rolle.EXAMINER),
            ("learner", Rolle.LEARNER),
        ]:
            user, _ = User.objects.get_or_create(
                username=username,
                defaults={"email": f"{username}@example.com", "first_name": username.title()},
            )
            user.set_password("ChangeMe123!")
            user.save(update_fields=["password"])
            user.groups.add(Group.objects.get(name=rolle.value))

    # ------------------------------------------------------------------
    def _setup_organisation(self):
        User = get_user_model()
        organisation, _ = Organisation.objects.get_or_create(
            slug="demo-organisation",
            defaults={
                "name": "Demo Organisation",
                "kontakt_email": "demo@aborosoft.de",
                "lizenz_typ": LizenzTyp.PRO,
                "max_nutzer": 100,
                "max_kurse": 25,
            },
        )
        for username, rolle in [
            ("exam_operator", Rolle.EXAM_OPERATOR),
            ("trainer", Rolle.TRAINER),
            ("examiner", Rolle.EXAMINER),
            ("learner", Rolle.LEARNER),
        ]:
            user = User.objects.get(username=username)
            UserProfile.objects.get_or_create(nutzer=user, organisation=organisation, rolle=rolle)
        return organisation

    # ------------------------------------------------------------------
    def _setup_zahlungseinstellungen(self):
        settings = Zahlungseinstellungen.load()
        settings.stripe_aktiv = True
        settings.google_pay_aktiv = True
        settings.paypal_aktiv = True
        settings.ueberweisung_aktiv = True
        settings.demo_autoconfirm = True
        settings.kontoinhaber = "ABoroSoft"
        settings.iban = "DE02120300000000202051"
        settings.bic = "BYLADEM1001"
        settings.bankname = "Demo Bank"
        settings.save()

    # ------------------------------------------------------------------
    def _setup_org_konfiguration(self, organisation):
        OrganisationDesign.objects.get_or_create(
            organisation=organisation,
            defaults={
                "primary_color": "#12315f",
                "secondary_color": "#f28c28",
                "navbar_farbe": "#0c2448",
                "hintergrund_farbe": "#f6f8fb",
            },
        )
        OrganisationEmailKonfiguration.objects.get_or_create(
            organisation=organisation,
            defaults={
                "aktiv": False,
                "absender_name": "Demo Organisation Academy",
                "absender_email": "academy@demo-organisation.de",
                "antwort_email": "support@demo-organisation.de",
                "smtp_host": "smtp.beispiel.de",
                "smtp_port": 587,
                "smtp_user": "academy@demo-organisation.de",
                "smtp_use_tls": True,
            },
        )
        seite, _ = OrganisationStartseite.objects.get_or_create(organisation=organisation)
        seite.aktiv = True
        seite.hero_titel = "Willkommen bei der Demo Organisation"
        seite.hero_untertitel = (
            "Entdecken Sie alle Funktionen von ABoroLMS – "
            "Kurse, Pruefungen, Zertifikate und mehr."
        )
        seite.hero_button_text = "Jetzt Kurs starten"
        seite.save()

    # ------------------------------------------------------------------
    def _setup_kurs(self, organisation):
        User = get_user_model()
        trainer = User.objects.get(username="trainer")
        kurs, _ = Kurs.objects.get_or_create(
            slug="aborolms-komplett",
            defaults={
                "titel": "ABoroLMS Komplett – Lernplattform erkunden",
                "organisation": organisation,
                "erstellt_von": trainer,
                "sprache": "de",
                "niveau": Niveau.ANFAENGER,
            },
        )
        kurs.titel = "ABoroLMS Komplett – Lernplattform erkunden"
        kurs.beschreibung = quill_html(
            "<p>Dieser Kurs vermittelt alle Funktionen von ABoroLMS: Architektur, Rollen, "
            "Kurssystem, Pruefungsystem mit 6 Fragetypen, Zahlungen mit 85/15-Aufteilung, "
            "automatische Zertifikate mit PDF und QR-Code sowie die SaaS-Organisations&shy;verwaltung.</p>"
            "<p>Jede Lektion erklaert ein konkretes Feature des LMS – praxisnah, mit Uebungsfragen "
            "und Begleitmaterialien. Am Ende wartet eine Zertifikatspruefung.</p>"
        )
        kurs.ist_veroeffentlicht = True
        kurs.ist_kostenlos = False
        kurs.preis = 49
        kurs.niveau = Niveau.ANFAENGER
        kurs.save()
        return kurs

    # ------------------------------------------------------------------
    def _setup_pruefung(self, organisation, kurs):
        User = get_user_model()
        trainer = User.objects.get(username="trainer")
        katalog, _ = Fragenkatalog.objects.get_or_create(
            titel="ABoroLMS Zertifikatsfragen",
            organisation=organisation,
            defaults={
                "beschreibung": "Offizieller Fragenkatalog fuer die ABoroLMS-Grundlagenzertifizierung.",
                "erstellt_von": trainer,
            },
        )
        pruefung, _ = Pruefung.objects.get_or_create(
            titel="ABoroLMS Grundlagen Zertifikatspruefung",
            organisation=organisation,
            defaults={
                "fragenkatalog": katalog,
                "anzahl_fragen": 10,
                "zeitlimit_minuten": 25,
                "bestehensgrenze_prozent": 70,
                "max_versuche": None,
                "zufaellige_fragenreihenfolge": True,
                "zufaellige_antwortfolge": True,
                "ist_aktiv": True,
            },
        )
        pruefung.beschreibung = (
            "Bestehe diese Pruefung mit mindestens 70 %, um dein ABoroLMS-Grundlagenzertifikat zu erhalten. "
            "10 von 12 Fragen werden zufaellig gezogen – darunter Single Choice, Multiple Choice, "
            "Wahr/Falsch, Freitext und Zuordnung."
        )
        pruefung.anzahl_fragen = 10
        pruefung.zeitlimit_minuten = 25
        pruefung.save(update_fields=["beschreibung", "anzahl_fragen", "zeitlimit_minuten"])
        if kurs.pruefung_id != pruefung.id:
            kurs.pruefung = pruefung
            kurs.save(update_fields=["pruefung"])
        return katalog, pruefung

    # ------------------------------------------------------------------
    def _setup_kursinhalte(self, kurs):
        # Bestehende Inhalte loeschen und neu aufbauen fuer sauberes Update
        kurs.abschnitte.all().delete()

        for abschnitt_pos, abschnitt_data in enumerate(KURSINHALTE, start=1):
            abschnitt = Abschnitt.objects.create(
                kurs=kurs,
                titel=abschnitt_data["titel"],
                reihenfolge=abschnitt_pos,
            )
            for lektion_pos, lek in enumerate(abschnitt_data["lektionen"], start=1):
                lektion = Lektion.objects.create(
                    abschnitt=abschnitt,
                    titel=lek["titel"],
                    typ=lek["typ"],
                    inhalt=quill_html(lek["inhalt"]),
                    dauer_minuten=lek["dauer"],
                    ist_vorschau=lek["ist_vorschau"],
                    reihenfolge=lektion_pos,
                )
                if lek.get("uebung"):
                    u = lek["uebung"]
                    frage = Uebungsfrage.objects.create(
                        lektion=lektion,
                        frage=u["frage"],
                        erklaerung=u["erklaerung"],
                        reihenfolge=1,
                        aktiv=True,
                    )
                    for i, (text, korrekt) in enumerate(u["antworten"], start=1):
                        Uebungsantwort.objects.create(
                            frage=frage,
                            antwort=text,
                            ist_korrekt=korrekt,
                            reihenfolge=i,
                        )
                if lek.get("material"):
                    dateiname, inhalt = lek["material"]
                    material = Begleitmaterial.objects.create(
                        lektion=lektion,
                        titel=dateiname.replace(".txt", "").replace("_", " "),
                        reihenfolge=1,
                    )
                    material.datei.save(dateiname, ContentFile(inhalt.encode("utf-8")), save=True)

    # ------------------------------------------------------------------
    def _setup_learner_zugang(self, kurs):
        User = get_user_model()
        learner = User.objects.get(username="learner")
        einschreibung, _ = Einschreibung.objects.get_or_create(
            nutzer=learner, kurs=kurs, defaults={"bezahlt": True}
        )
        if not einschreibung.bezahlt:
            einschreibung.bezahlt = True
            einschreibung.save(update_fields=["bezahlt"])

        if Zahlungseinstellungen.load().payment_aktiv and not Zahlung.objects.filter(nutzer=learner, kurs=kurs, status=Zahlungsstatus.BEZAHLT).exists():
            zahlung = erstelle_zahlung(kurs, learner, Zahlungsart.STRIPE)
            bestaetige_zahlung(zahlung, provider_referenz="demo-paid-course-access")

    # ------------------------------------------------------------------
    def _setup_pruefungsfragen(self, katalog):
        # Bestehende Fragen loeschen und neu aufbauen
        katalog.fragen.all().delete()

        for daten in PRUEFUNGSFRAGEN:
            frage = Frage.objects.create(
                fragenkatalog=katalog,
                typ=daten["typ"],
                fragetext=quill_html("<p>" + daten["text"] + "</p>"),
                erklaerung=quill_html("<p>" + daten["erklaerung"] + "</p>"),
                bewertungshinweis=quill_html(daten.get("bewertungshinweis", "")),
                punkte=daten["punkte"],
                schwierigkeit=Frage.Schwierigkeit.MITTEL,
            )
            if daten["typ"] == Frage.Typ.ZUORDNUNG:
                for i, (links, rechts) in enumerate(daten.get("zuordnungen", []), start=1):
                    ZuordnungsPaar.objects.create(
                        frage=frage,
                        linkes_element=links,
                        rechtes_element=rechts,
                        reihenfolge=i,
                    )
            else:
                for i, (text, korrekt) in enumerate(daten.get("antworten", []), start=1):
                    Antwort.objects.create(
                        frage=frage,
                        antworttext=text,
                        ist_korrekt=korrekt,
                        reihenfolge=i,
                    )
