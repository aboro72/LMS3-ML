from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404
from django.shortcuts import redirect
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, TemplateView, UpdateView

from .forms import OrganisationLoginForm, ProfilForm, RegisterForm
from .models import Rolle, UserProfile
from apps.organisations.models import Einladung, Organisation
from apps.exams.models import PruefungsAnmeldung, PruefungsFreigabe, PruefungsVersuch
from allauth.account.views import LoginView as AllauthLoginView


class HomeView(TemplateView):
    template_name = "home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["demo_mode"] = settings.DEBUG
        return context


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "accounts/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = self.request.user.profile.select_related("organisation").filter(aktiv=True)
        if getattr(self.request, "tenant_org", None) and not self.request.user.is_superuser:
            profile = profile.filter(organisation=self.request.tenant_org)
        context["profile"] = profile
        einschreibungen = (
            self.request.user.einschreibung_set.select_related("kurs", "kurs__organisation")
            .order_by("-eingeschrieben_am")
            if self.request.user.is_authenticated
            else []
        )
        zertifikate = (
            self.request.user.zertifikate.filter(ist_widerrufen=False)
            .select_related("pruefungsversuch__pruefung", "einschreibung__kurs")
            .order_by("-ausgestellt_am")
        )
        if getattr(self.request, "tenant_org", None) and not self.request.user.is_superuser:
            einschreibungen = einschreibungen.filter(kurs__organisation=self.request.tenant_org)
            zertifikate = zertifikate.filter(einschreibung__kurs__organisation=self.request.tenant_org)
        context["einschreibungen"] = einschreibungen
        context["zertifikate"] = zertifikate[:3]

        learner_invitations = Einladung.objects.none()
        learner_registrations = PruefungsAnmeldung.objects.none()
        learner_releases = PruefungsFreigabe.objects.none()
        learner_attempts = PruefungsVersuch.objects.none()
        if self.request.user.is_authenticated:
            learner_invitations = Einladung.objects.filter(
                email__iexact=self.request.user.email,
                rolle=Rolle.LEARNER,
                pruefung__isnull=False,
                akzeptiert_am__isnull=True,
                abgelaufen_am__gt=timezone.now(),
            ).select_related("organisation", "pruefung").order_by("-erstellt_am")
            learner_registrations = PruefungsAnmeldung.objects.filter(
                nutzer=self.request.user,
            ).select_related("pruefung").order_by("-angemeldet_am")
            learner_releases = PruefungsFreigabe.objects.filter(
                nutzer=self.request.user,
                widerrufen_am__isnull=True,
            ).select_related("pruefung").order_by("-freigegeben_am")
            learner_attempts = PruefungsVersuch.objects.filter(
                nutzer=self.request.user,
            ).select_related("pruefung").order_by("-gestartet_am")
        context["learner_exam_invitations"] = learner_invitations
        context["learner_exam_registrations"] = learner_registrations
        context["learner_exam_releases"] = learner_releases
        context["learner_exam_attempts"] = learner_attempts[:100]

        trainer_org_ids = self.request.user.profile.filter(
            rolle=Rolle.TRAINER, aktiv=True
        ).values_list("organisation_id", flat=True)
        trainer_attempts = PruefungsVersuch.objects.filter(
            pruefung__organisation_id__in=trainer_org_ids,
        ).select_related("nutzer", "pruefung").order_by("-gestartet_am")
        context["trainer_exam_attempts"] = trainer_attempts[:100]
        context["trainer_exam_counts"] = {
            "laufend": trainer_attempts.filter(status=PruefungsVersuch.Status.LAUFEND).count(),
            "ausstehend": trainer_attempts.filter(status=PruefungsVersuch.Status.AUSSTEHEND).count(),
            "bestanden": trainer_attempts.filter(
                status=PruefungsVersuch.Status.ABGESCHLOSSEN, bestanden=True
            ).count(),
            "nicht_bestanden": trainer_attempts.filter(
                status__in=[
                    PruefungsVersuch.Status.ABGESCHLOSSEN,
                    PruefungsVersuch.Status.ABGELAUFEN,
                    PruefungsVersuch.Status.ABGEBROCHEN,
                ], bestanden=False
            ).count(),
        }
        return context

    def get(self, request, *args, **kwargs):
        from .context_processors import rollen_context
        roles = rollen_context(request)
        if settings.SINGLE_SYSTEM_MODE and not (
            roles.get("ist_exam_operator")
            or roles.get("ist_superadmin")
            or roles.get("ist_trainer")
            or roles.get("ist_learner")
        ):
            return redirect("single_system_startseite")
        return super().get(request, *args, **kwargs)


class RegisterView(CreateView):
    form_class = RegisterForm
    template_name = "accounts/register.html"
    success_url = reverse_lazy("account_login")

    def form_valid(self, form):
        response = super().form_valid(form)
        if settings.SINGLE_SYSTEM_MODE:
            from apps.organisations.single_system import system_organisation
            UserProfile.objects.get_or_create(nutzer=self.object, organisation=system_organisation(), rolle=Rolle.LEARNER)
        return response


class OrganisationRegisterView(CreateView):
    form_class = RegisterForm
    template_name = "accounts/register.html"
    success_url = reverse_lazy("home")

    def dispatch(self, request, *args, **kwargs):
        if settings.SINGLE_SYSTEM_MODE:
            raise Http404("Mandantenregistrierung ist im Einzelsystem deaktiviert.")
        self.organisation = get_object_or_404(Organisation, slug=kwargs["org_slug"], aktiv=True)
        request.tenant_org = self.organisation
        request.session["active_organisation_id"] = self.organisation.pk
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        response = super().form_valid(form)
        UserProfile.objects.get_or_create(
            nutzer=self.object, organisation=self.organisation,
            rolle=Rolle.LEARNER, defaults={"aktiv": True},
        )
        return redirect("tenant_course_catalog", org_slug=self.organisation.slug)


class OrganisationLoginView(AllauthLoginView):
    form_class = OrganisationLoginForm
    template_name = "account/login.html"

    def dispatch(self, request, *args, **kwargs):
        if settings.SINGLE_SYSTEM_MODE:
            raise Http404("Mandanten-Login ist im Einzelsystem deaktiviert.")
        self.organisation = get_object_or_404(Organisation, slug=kwargs["org_slug"], aktiv=True)
        request.tenant_org = self.organisation
        request.session["active_organisation_id"] = self.organisation.pk
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse_lazy("org_public_home", kwargs={"slug": self.organisation.slug})


class ProfilView(LoginRequiredMixin, UpdateView):
    form_class = ProfilForm
    template_name = "accounts/profile.html"
    success_url = reverse_lazy("dashboard")

    def get_object(self):
        return self.request.user


ROLE_HELP_PAGES = {
    "superadmin": {
        "title": "Super-Admin Hilfe",
        "badge": "Plattformbetrieb",
        "intro": "Der Super-Admin betreibt die gesamte Plattform, prueft Organisationen, Zahlungsfluesse und globale Einstellungen.",
        "quick_cards": [
            {"title": "Ueberblick", "text": "Alle Mandanten, Kurse, Zahlungen und kritischen Einstellungen im Blick behalten."},
            {"title": "Kontrolle", "text": "Lizenz-, Zahlungs- und Audit-Funktionen regelmaessig pruefen."},
            {"title": "Support", "text": "Bei Problemen Rollen, Einschreibungen und Zahlungsstatus nachvollziehen."},
        ],
        "sections": [
            {"title": "Wichtige Bereiche", "text": "Diese Bereiche sind fuer den Plattformbetrieb zentral.", "items": [
                {"title": "Organisationen", "text": "Zeigt alle Mandanten mit Mitglieder- und Kursanzahl. Von hier aus erkennst du schnell, welche Organisation aktiv genutzt wird.", "url_name": "superadmin_orgs", "link_text": "Organisationen oeffnen"},
                {"title": "Zahlungseinstellungen", "text": "Aktiviere oder deaktiviere Zahlungsarten und den globalen Zahlungsschalter.", "url_name": "superadmin_payment_settings", "link_text": "Zahlungen konfigurieren"},
                {"title": "Auszahlungen", "text": "Kontrolliere bezahlte Kurse, offene Ueberweisungen und Trainer-Anteile.", "url_name": "superadmin_payouts", "link_text": "Auszahlungen ansehen"},
                {"title": "Audit-Log", "text": "Zeigt wichtige Systemereignisse wie Zahlungsbestaetigungen, Einladungen und Auszahlungsmarkierungen.", "url_name": "superadmin_audit_log", "link_text": "Audit-Log oeffnen"},
            ]},
            {"title": "Empfohlener Ablauf", "text": "So pruefst du eine Demo oder Installation systematisch.", "items": [
                {"title": "1. Mandantenstatus pruefen", "text": "Starte bei den Organisationen und pruefe Aktivstatus, Lizenzlimit, Mitglieder und Kursmenge."},
                {"title": "2. Zahlungsfluss kontrollieren", "text": "Pruefe Zahlungseinstellungen, offene Bankueberweisungen und bestaetigte Zahlungen."},
                {"title": "3. Supportfall nachvollziehen", "text": "Bei Nutzerproblemen pruefst du Rolle, Organisation, Einschreibung und Zahlung in dieser Reihenfolge."},
            ]},
        ],
        "faqs": [
            {"question": "Warum sehe ich manche Org-Admin-Funktionen nicht?", "answer": "Superuser sehen globale Bereiche. Organisationsspezifische Menues haengen an einem aktiven UserProfile in einer Organisation."},
            {"question": "Wann ist ein Kurs freigeschaltet?", "answer": "Kostenlose Kurse werden beim Start automatisch eingeschrieben. Kostenpflichtige Kurse brauchen eine bezahlte Einschreibung."},
            {"question": "Wo erkenne ich Zahlungsprobleme?", "answer": "In Auszahlungen und Audit-Log. Bankueberweisungen koennen manuell bestaetigt werden."},
        ],
    },
    "org_admin": {
        "title": "Org-Admin Hilfe",
        "badge": "Organisation verwalten",
        "intro": "Org-Admins verwalten Mitglieder, Einladungen, Design, Startseite und Organisationskommunikation.",
        "quick_cards": [
            {"title": "Mitglieder", "text": "Nutzer einladen, Rollen vergeben und aktive Profile pruefen."},
            {"title": "Auftritt", "text": "Logo, Farben, Startseite und Zertifikat-Design pflegen."},
            {"title": "Limits", "text": "Lizenzgrenzen fuer Nutzer und Kurse im Blick behalten."},
        ],
        "sections": [
            {"title": "Wichtige Bereiche", "text": "Diese Funktionen betreffen deine Organisation.", "items": [
                {"title": "Organisations-Dashboard", "text": "Kennzahlen zu Mitgliedern, Kursen, Einschreibungen und Umsatz deiner Organisation.", "url_name_with_org": "org_admin_dashboard", "link_text": "Dashboard oeffnen"},
                {"title": "Mitglieder", "text": "Zeigt aktive Mitglieder und offene Einladungen. Neue Nutzer bekommen hier ihre Rolle.", "url_name_with_org": "org_members", "link_text": "Mitglieder verwalten"},
                {"title": "Design", "text": "Farben, Logo und visuelle Grundlagen fuer Katalog, Kursseiten und Navigation.", "url_name_with_org": "org_design", "link_text": "Design bearbeiten"},
                {"title": "Startseite", "text": "Pflege die oeffentliche Seite deiner Organisation mit Hero, Inhalt und Button.", "url_name_with_org": "org_startseite", "link_text": "Startseite bearbeiten"},
                {"title": "E-Mail", "text": "SMTP- und Absenderdaten fuer Einladungen und Systemmails.", "url_name_with_org": "org_email_config", "link_text": "E-Mail konfigurieren"},
            ]},
            {"title": "Empfohlener Ablauf", "text": "Damit eine Organisation startklar ist.", "items": [
                {"title": "1. Grunddaten und Design pruefen", "text": "Logo, Farben und Startseite setzen, damit Lernende die Organisation wiedererkennen."},
                {"title": "2. Rollen einladen", "text": "Trainer zuerst einladen, danach Pruefer und Lernende. Jede Einladung ist an eine E-Mail und Rolle gebunden."},
                {"title": "3. Inhalte kontrollieren", "text": "Nach Kurserstellung im Katalog pruefen, ob Kurse veroeffentlicht und richtig bepreist sind."},
            ]},
        ],
        "faqs": [
            {"question": "Warum kann ich keinen Nutzer mehr einladen?", "answer": "Das Nutzerlimit der Lizenz kann erreicht sein. Super-Admins koennen die Lizenz im Adminbereich anpassen."},
            {"question": "Warum sieht ein Trainer keine Kurse?", "answer": "Der Trainer braucht ein aktives Trainer-Profil in genau der Organisation, zu der die Kurse gehoeren."},
            {"question": "Welche Rolle braucht ein Pruefer?", "answer": "Fuer die Bewertungsqueue braucht der Nutzer die Rolle Pruefer oder eine hoeher berechtigte Rolle."},
        ],
    },
    "trainer": {
        "title": "Trainer Hilfe",
        "badge": "Kurse und Pruefungen erstellen",
        "intro": "Trainer bauen Kurse, Lektionen, Begleitmaterial, Uebungsfragen, Fragenkataloge und Pruefungen.",
        "quick_cards": [
            {"title": "Kurse", "text": "Kursdaten, Abschnitte, Lektionen und Medien pflegen."},
            {"title": "Pruefungen", "text": "Fragenkataloge erstellen und Pruefungen konfigurieren."},
        ],
        "sections": [
            {"title": "Wichtige Bereiche", "text": "Hier findet die taegliche Trainerarbeit statt.", "items": [
                {"title": "Kursverwaltung", "text": "Kurse erstellen, veroeffentlichen, Abschnitte und Lektionen pflegen. Videos werden als Lektionsmedium hochgeladen; Begleitmaterial ist fuer PDF, DOC, TXT oder ZIP gedacht.", "url_name": "trainer_course_list", "link_text": "Kurse verwalten"},
                {"title": "Lernpfade", "text": "Strukturierte Kursreihen erstellen: Grunddaten speichern, Kurse hinzufuegen, Reihenfolge setzen und veroeffentlichen.", "url_name": "trainer_learning_path_list", "link_text": "Lernpfade verwalten"},
                {"title": "Fragenkataloge", "text": "Sammlung von Fragen, Antworten, Freitexten und Zuordnungen fuer spaetere Pruefungen.", "url_name": "trainer_catalog_list", "link_text": "Fragenkataloge oeffnen"},
                {"title": "Pruefungen", "text": "Definiert Anzahl Fragen, Zeitlimit, Bestehensgrenze, Zufallslogik und Versuchsanzahl.", "url_name": "trainer_exam_list", "link_text": "Pruefungen verwalten"},
            ]},
            {"title": "Empfohlener Kursaufbau", "text": "Ein sauberer Kurs entsteht in dieser Reihenfolge.", "items": [
                {"title": "1. Kursgrunddaten", "text": "Titel, Slug, Beschreibung, Organisation, Preis und Veroeffentlichung setzen."},
                {"title": "2. Abschnitte und Lektionen", "text": "Abschnitte strukturieren das Thema. Lektionen koennen Video, Text, Dokument oder Mini-Quiz sein."},
                {"title": "3. Medien hochladen", "text": "Fuer Videos den Block Video/Dokument der Lektion aktualisieren nutzen. Aus hochgeladenen Videos wird automatisch ein Thumbnail erzeugt."},
                {"title": "4. Pruefung verbinden", "text": "Fragenkatalog und Pruefung erstellen, danach dem Kurs zuordnen."},
                {"title": "5. Lernpfad erstellen", "text": "Unter Trainer > Lernpfade eine Kursreihe anlegen, vorhandene Kurse hinzufuegen und die Reihenfolge festlegen."},
            ]},
        ],
        "csv_template_file": "downloads/fragenkatalog_csv_vorlage.xlsx",
        "csv_example": "typ;fragetext;erklaerung;schwierigkeit;punkte;antwort_1;korrekt_1;antwort_2;korrekt_2;antwort_3;korrekt_3;antwort_4;korrekt_4;antwort_5;korrekt_5;antwort_6;korrekt_6;antwort_7;korrekt_7;antwort_8;korrekt_8;links_1;rechts_1;links_2;rechts_2;links_3;rechts_3;links_4;rechts_4;links_5;rechts_5\nSC;Welche Farbe hat ein Stoppschild?;Rot ist die richtige Antwort.;L;1;Rot;1;Blau;0;Gruen;0;;;;;;;;;;;;;;;;;;;;\nMC;Welche Werte sind Boolean-Werte?;True und False sind boolesche Werte.;M;2;True;1;False;1;Vielleicht;0;;;;;;;;;;;;;;;;;;;;\nWF;Python ist eine Programmiersprache.;Die Aussage ist wahr.;L;1;Wahr;1;Falsch;0;;;;;;;;;;;;;;;;;;;;;;\nFT;Erklaere kurz den Unterschied zwischen HTTP und HTTPS.;Musterloesung fuer die manuelle Bewertung.;M;5;;;;;;;;;;;;;;;;;;;;;;;;;;\nZO;Ordne die Begriffe zu.;Jedes linke Element braucht ein rechtes Element.;M;3;;;;;;;;;;;;;;;;;HTTP;Protokoll;HTML;Markup-Sprache;;;;;;\nSZ;Kunde meldet Ausfall im Helpdesk.;Szenario-Text, danach koennen Teilfragen manuell angelegt werden.;S;1;;;;;;;;;;;;;;;;;;;;;;;;;;",
        "faqs": [
            {"question": "Warum wird mein Video als Begleitmaterial abgelehnt?", "answer": "Videos gehoeren zur Lektion selbst. Oeffne bei der Lektion Video/Dokument der Lektion aktualisieren und lade dort MP4, WebM, MOV oder M4V hoch."},
            {"question": "Wann sehen Lernende den Kurs?", "answer": "Der Kurs muss veroeffentlicht sein und die Organisation muss aktiv sein."},
            {"question": "Wie erstelle ich einen Lernpfad?", "answer": "Im Trainer-Menue Lernpfade oeffnen, Lernpfad erstellen, Grunddaten speichern und danach im Editor Kurse hinzufuegen. Erst wenn Veroeffentlicht aktiv ist, erscheint der Lernpfad fuer Lernende."},
            {"question": "Wie entsteht das Video-Thumbnail?", "answer": "Beim Speichern eines hochgeladenen Videos erzeugt ffmpeg automatisch ein JPG aus dem Frame bei Sekunde 3."},
        ],
    },
    "examiner": {
        "title": "Pruefer Hilfe",
        "badge": "Antworten bewerten",
        "intro": "Pruefer bearbeiten manuelle Freitextantworten und sorgen dafuer, dass Pruefungsergebnisse korrekt abgeschlossen werden.",
        "quick_cards": [
            {"title": "Queue", "text": "Offene manuelle Bewertungen an einem Ort."},
            {"title": "Fairness", "text": "Antwort, Musterloesung und Punkte nachvollziehbar bewerten."},
            {"title": "Abschluss", "text": "Nach Bewertung kann ein Ergebnis final werden und Zertifikate ausloesen."},
        ],
        "sections": [
            {"title": "Wichtige Bereiche", "text": "Pruefer arbeiten hauptsaechlich in der Queue.", "items": [
                {"title": "Pruefer-Queue", "text": "Listet offene Freitextantworten, die manuell bewertet werden muessen.", "url_name": "examiner_queue", "link_text": "Queue oeffnen"},
                {"title": "Pruefungsdetail", "text": "Zeigt die Pruefung aus Sicht der Teilnehmenden und hilft beim Nachvollziehen der Aufgabe."},
                {"title": "Zertifikate", "text": "Nach bestandener Pruefung koennen Zertifikate erzeugt und verifiziert werden."},
            ]},
            {"title": "Bewertungsablauf", "text": "So bleibt die Bewertung nachvollziehbar.", "items": [
                {"title": "1. Antwort lesen", "text": "Freitextantwort vollstaendig lesen und mit der erwarteten Loesung vergleichen."},
                {"title": "2. Punkte vergeben", "text": "Teilpunkte vergeben, wenn die Antwort wesentliche Aspekte enthaelt."},
                {"title": "3. Ergebnis speichern", "text": "Nach dem Speichern wird die Antwort aus der offenen Queue entfernt."},
            ]},
        ],
        "faqs": [
            {"question": "Warum ist die Queue leer?", "answer": "Entweder gibt es keine offenen Freitextantworten oder deine Rolle ist nicht in der betreffenden Organisation aktiv."},
            {"question": "Kann ein Pruefer Kurse bearbeiten?", "answer": "Nur mit zusaetzlicher Trainer- oder Org-Admin-Rolle. Pruefer allein bewerten Antworten."},
            {"question": "Wann wird ein Zertifikat erstellt?", "answer": "Wenn die Pruefung vollstaendig bewertet ist und die Bestehensgrenze erreicht wurde."},
        ],
    },
    "exam_operator": {
        "title": "Prüfungsoperator Hilfe",
        "badge": "Zertifikatsprüfungen konfigurieren",
        "intro": "Prüfungsoperatoren verwalten Zertifikatsfragen, Prüfungsparameter und die verbindlichen PDF-Vorgaben.",
        "quick_cards": [
            {"title": "Fragenkataloge", "text": "Fragen per Hand oder CSV anlegen, suchen und aktivieren.", "url_name": "trainer_catalog_list", "link_text": "Kataloge öffnen"},
            {"title": "Prüfungsregeln", "text": "Fragenzahl, Zeitlimit und Bestehensgrenze festlegen."},
            {"title": "PDF-Vorgaben", "text": "Prüflings- und Lösungsbogen verbindlich konfigurieren."},
        ],
        "sections": [],
        "faqs": [
            {"question": "Kann ein Trainer Zertifikatsfragen ändern?", "answer": "Nein. Fragenkataloge und Parameter werden ausschließlich durch Prüfungsoperatoren gepflegt."},
            {"question": "Was passiert mit deaktivierten Fragen?", "answer": "Sie werden nicht für neue Prüfungen gezogen. Bereits laufende Versuche bleiben unverändert."},
        ],
    },
    "learner": {
        "title": "Lernenden Hilfe",
        "badge": "Kurse absolvieren",
        "intro": "Lernende schreiben sich in Kurse ein, bearbeiten Lektionen, absolvieren Pruefungen und laden Zertifikate herunter.",
        "quick_cards": [
            {"title": "Starten", "text": "Kostenlose Kurse direkt starten, bezahlte Kurse nach Freischaltung nutzen."},
            {"title": "Lernen", "text": "Videos, Texte, Dokumente und Uebungsfragen durcharbeiten."},
            {"title": "Nachweisen", "text": "Pruefung bestehen und Zertifikat herunterladen."},
        ],
        "sections": [
            {"title": "Wichtige Bereiche", "text": "Diese Seiten brauchst du am haeufigsten.", "items": [
                {"title": "Katalog", "text": "Alle veroeffentlichten Kurse finden, filtern und Kursdetails oeffnen.", "url_name": "course_catalog", "link_text": "Kurse ansehen"},
                {"title": "Lernpfade", "text": "Mehrere Kurse in einer sinnvollen Reihenfolge bearbeiten.", "url_name": "learning_path_list", "link_text": "Lernpfade ansehen"},
                {"title": "Dashboard", "text": "Zeigt deine Organisationen, Einschreibungen, Fortschritt und aktuelle Zertifikate.", "url_name": "dashboard", "link_text": "Dashboard oeffnen"},
                {"title": "Zertifikate", "text": "Bestandene Zertifikate einsehen und als PDF herunterladen.", "url_name": "cert_list", "link_text": "Zertifikate oeffnen"},
            ]},
            {"title": "Lernablauf", "text": "Vom Kursstart bis zum Zertifikat.", "items": [
                {"title": "1. Kurs auswaehlen", "text": "Im Katalog einen Kurs oeffnen. Kostenlose Kurse starten sofort nach dem Login."},
                {"title": "2. Lektionen bearbeiten", "text": "In der Lernansicht die Lektionen nacheinander oeffnen und Fortschritt markieren."},
                {"title": "3. Uebungsfragen nutzen", "text": "Mini-Quizfragen helfen beim Wiederholen und zaehlen nicht als Zertifikatspruefung."},
                {"title": "4. Pruefung absolvieren", "text": "Wenn eine Abschlusspruefung vorhanden ist, kannst du sie aus dem Kursdetail starten."},
            ]},
        ],
        "faqs": [
            {"question": "Warum werde ich zum Login geschickt?", "answer": "Lernfortschritt, Einschreibungen und Zertifikate sind kontobezogen. Deshalb brauchst du ein angemeldetes Konto."},
            {"question": "Warum kann ich einen bezahlten Kurs nicht starten?", "answer": "Der Kurs ist erst nach bestaetigter Zahlung freigeschaltet. Kostenlose Kurse werden automatisch freigeschaltet."},
            {"question": "Wo finde ich mein Zertifikat?", "answer": "Nach bestandener Pruefung erscheint es im Dashboard und unter Zertifikate."},
        ],
    },
}


class RoleHelpView(LoginRequiredMixin, TemplateView):
    template_name = "accounts/role_help.html"

    def dispatch(self, request, *args, **kwargs):
        allowed_role = self._default_role()
        requested_role = kwargs.get("role")
        if requested_role and requested_role != allowed_role:
            return redirect("role_help_detail", role=allowed_role)
        self.active_role = allowed_role
        return super().dispatch(request, *args, **kwargs)

    def _default_role(self):
        user = self.request.user
        if user.is_superuser or user.groups.filter(name=Rolle.SUPERADMIN).exists():
            return "superadmin"
        profile_role = user.profile.filter(aktiv=True).values_list("rolle", flat=True).first()
        return profile_role or "learner"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["active_role"] = self.active_role
        context["active_help"] = ROLE_HELP_PAGES[self.active_role]
        if settings.SINGLE_SYSTEM_MODE and self.active_role == "superadmin":
            context["active_help"] = {"title": "Systemverwaltung", "badge": "Einzelinstallation", "intro": "Benutzer, Rollen, Design und E-Mail-Einstellungen dieser Installation verwalten.", "quick_cards": [], "sections": [{"title": "Verwaltung", "items": [{"title": "Benutzer und Einladungen", "url_name": "system_members", "link_text": "Benutzer verwalten"}, {"title": "Design", "url_name": "system_design", "link_text": "Design bearbeiten"}, {"title": "E-Mail", "url_name": "system_email", "link_text": "E-Mail konfigurieren"}]}], "faqs": []}
        return context
