import json
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View
from django.utils import timezone
from django.views.generic import CreateView, ListView, TemplateView
from django_quill.quill import Quill

from apps.accounts.mixins import RollenMixin
from apps.accounts.models import Rolle, UserProfile
from apps.payments.models import Zahlung, Zahlungsstatus

from .forms import (
    EinladungForm,
    OrganisationDesignForm,
    OrganisationEmailKonfigForm,
    OrganisationSignupForm,
    OrganisationStartseiteForm,
    OrganisationWeiterleitungForm,
)
from .models import (
    Einladung,
    Organisation,
    OrganisationDesign,
    OrganisationEmailKonfiguration,
    OrganisationStartseite,
)


# --------------------------------------------------------------------------- #
# Hilfsmethode: Organisation für Org-Admin laden
# --------------------------------------------------------------------------- #
def _get_org_for_admin(request, slug):
    if request.user.is_superuser or (request.user.is_authenticated and request.user.groups.filter(name=Rolle.SUPERADMIN).exists()):
        return get_object_or_404(Organisation, slug=slug)
    org_ids = request.user.profile.filter(
        rolle=Rolle.ORG_ADMIN, aktiv=True
    ).values_list("organisation_id", flat=True)
    return get_object_or_404(Organisation, slug=slug, id__in=org_ids)


def _get_org_for_inviter(request, slug):
    """Org-Admins may invite all roles; trainers may invite learners for their own org."""
    if request.user.is_superuser or (request.user.is_authenticated and request.user.groups.filter(name=Rolle.SUPERADMIN).exists()):
        return get_object_or_404(Organisation, slug=slug)
    org_ids = request.user.profile.filter(
        rolle__in=[Rolle.ORG_ADMIN, Rolle.TRAINER], aktiv=True
    ).values_list("organisation_id", flat=True)
    return get_object_or_404(Organisation, slug=slug, id__in=org_ids)


def _ist_trainer_ohne_org_admin(user, org):
    return not user.is_superuser and user.profile.filter(
        organisation=org, rolle=Rolle.TRAINER, aktiv=True
    ).exists() and not user.profile.filter(
        organisation=org, rolle=Rolle.ORG_ADMIN, aktiv=True
    ).exists()


# --------------------------------------------------------------------------- #
# Org-Signup
# --------------------------------------------------------------------------- #
class OrganisationSignupView(LoginRequiredMixin, CreateView):
    form_class = OrganisationSignupForm
    template_name = "organisations/signup.html"

    def form_valid(self, form):
        org = form.save()
        UserProfile.objects.create(nutzer=self.request.user, organisation=org, rolle=Rolle.ORG_ADMIN)
        from apps.courses.models import KursKategorie
        KursKategorie.standardkategorien_anlegen(org)
        messages.success(self.request, f"Organisation '{org.name}' wurde erstellt.")
        return redirect("org_admin_dashboard", slug=org.slug)


# --------------------------------------------------------------------------- #
# Org-Admin Dashboard
# --------------------------------------------------------------------------- #
class OrgAdminDashboardView(RollenMixin, TemplateView):
    rolle = Rolle.ORG_ADMIN
    template_name = "organisations/org_admin.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from apps.courses.models import Einschreibung, Kurs

        org = _get_org_for_admin(self.request, self.kwargs["slug"])
        nutzer_count = (
            UserProfile.objects.filter(organisation=org, aktiv=True)
            .values("nutzer").distinct().count()
        )
        kurs_count = Kurs.objects.filter(organisation=org).count()
        einschreibungen_count = Einschreibung.objects.filter(
            kurs__organisation=org, bezahlt=True
        ).count()
        umsatz = (
            Zahlung.objects.filter(kurs__organisation=org, status=Zahlungsstatus.BEZAHLT)
            .aggregate(total=Sum("betrag_brutto"))["total"] or 0
        )
        trainer_anteil = (
            Zahlung.objects.filter(kurs__organisation=org, status=Zahlungsstatus.BEZAHLT)
            .aggregate(total=Sum("trainer_anteil"))["total"] or 0
        )
        top_kurse = (
            Kurs.objects.filter(organisation=org, ist_veroeffentlicht=True)
            .annotate(anmeldungen=Count("einschreibung"))
            .order_by("-anmeldungen")[:5]
        )
        context.update({
            "org": org,
            "tenant_org": org,
            "nutzer_count": nutzer_count,
            "kurs_count": kurs_count,
            "einschreibungen_count": einschreibungen_count,
            "umsatz": umsatz,
            "trainer_anteil": trainer_anteil,
            "plattform_anteil": umsatz - trainer_anteil,
            "top_kurse": top_kurse,
        })
        return context


# --------------------------------------------------------------------------- #
# Mitgliederverwaltung
# --------------------------------------------------------------------------- #
class OrgMemberListView(LoginRequiredMixin, ListView):
    template_name = "organisations/members.html"
    context_object_name = "mitglieder"

    def dispatch(self, request, *args, **kwargs):
        self.org = _get_org_for_inviter(request, kwargs["slug"])
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return UserProfile.objects.filter(
            organisation=self.org, aktiv=True
        ).select_related("nutzer").order_by("rolle", "nutzer__username")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["org"] = self.org
        context["ist_trainer_einladender"] = _ist_trainer_ohne_org_admin(self.request.user, self.org)
        context["einladung_form"] = EinladungForm(
            organisation=self.org, ist_trainer=context["ist_trainer_einladender"]
        )
        context["offene_einladungen"] = Einladung.objects.filter(
            organisation=self.org, akzeptiert_am__isnull=True
        ).order_by("-erstellt_am")
        return context


class OrgEinladungCreateView(LoginRequiredMixin, View):

    def post(self, request, slug):
        org = _get_org_for_inviter(request, slug)
        ist_trainer = _ist_trainer_ohne_org_admin(request.user, org)
        if not settings.SINGLE_SYSTEM_MODE and org.max_nutzer and org.max_nutzer > 0:
            aktuell = (
                UserProfile.objects.filter(organisation=org, aktiv=True)
                .values("nutzer").distinct().count()
            )
            if aktuell >= org.max_nutzer:
                messages.error(
                    request,
                    f"Nutzerlimit ({org.max_nutzer}) der Lizenz erreicht. "
                    "Bitte upgraden Sie Ihre Lizenz.",
                )
                return redirect("org_members", slug=slug)

        form = EinladungForm(request.POST, organisation=org, ist_trainer=ist_trainer)
        if form.is_valid():
            einladung = Einladung.objects.create(
                organisation=org,
                email=form.cleaned_data["email"],
                rolle=form.cleaned_data["rolle"],
                eingeladen_von=request.user,
                pruefung=form.cleaned_data["pruefung"],
            )
            try:
                from apps.payments.services import log_audit
                log_audit(
                    actor=request.user,
                    organisation=org,
                    action="einladung_erstellt",
                    obj=einladung,
                    message=f"Einladung fuer {einladung.email} erstellt.",
                    metadata={"rolle": einladung.rolle, "pruefung_id": einladung.pruefung_id},
                )
            except Exception:
                pass
            einladungslink = request.build_absolute_uri(
                reverse("org_invitation_accept", kwargs={"token": einladung.token})
            )
            try:
                from .email import fuelle_emailvorlage, sende_org_email
                pruefung_hinweis = (
                    f"\nSie werden nach dem Annehmen direkt zur Zertifikatspruefung „{einladung.pruefung.titel}“ angemeldet."
                    if einladung.pruefung_id else ""
                )
                config, _ = OrganisationEmailKonfiguration.objects.get_or_create(organisation=org)
                sende_org_email(org,
                    fuelle_emailvorlage(config.einladung_betreff, organisation=org.name),
                    fuelle_emailvorlage(config.einladung_text, organisation=org.name, einladungslink=einladungslink) + pruefung_hinweis,
                    einladung.email)
            except Exception:
                messages.warning(request, "Einladung wurde erstellt, konnte aber nicht per E-Mail versendet werden. Der Link ist in der Liste offener Einladungen verfügbar.")
            else:
                messages.success(request, f"Einladung fuer {form.cleaned_data['email']} wurde per E-Mail versendet.")
        else:
            messages.error(request, "Einladung konnte nicht erstellt werden.")
        return redirect("org_members", slug=slug)


# --------------------------------------------------------------------------- #
class OrgEmailKonfigView(RollenMixin, View):
    rolle = Rolle.ORG_ADMIN

    def _ctx(self, org, form):
        return {"form": form, "org": org, "tenant_org": org}

    def get(self, request, slug):
        org = _get_org_for_admin(request, slug)
        config, _ = OrganisationEmailKonfiguration.objects.get_or_create(organisation=org)
        return render(request, "organisations/email_config.html",
                      self._ctx(org, OrganisationEmailKonfigForm(instance=config)))

    def post(self, request, slug):
        org = _get_org_for_admin(request, slug)
        config, _ = OrganisationEmailKonfiguration.objects.get_or_create(organisation=org)
        form = OrganisationEmailKonfigForm(request.POST, instance=config)
        if form.is_valid():
            form.save()
            messages.success(request, "E-Mail-Konfiguration wurde gespeichert.")
            return redirect("org_email_config", slug=slug)
        return render(request, "organisations/email_config.html", self._ctx(org, form))


# --------------------------------------------------------------------------- #
# Organisations-Design (Kurs-Katalog und Kurs-Seiten)
# --------------------------------------------------------------------------- #
class OrgDesignView(RollenMixin, View):
    rolle = Rolle.ORG_ADMIN

    def _ctx(self, org, form):
        return {"form": form, "org": org}

    def get(self, request, slug):
        org = _get_org_for_admin(request, slug)
        design, _ = OrganisationDesign.objects.get_or_create(organisation=org)
        return render(request, "organisations/design_editor.html",
                      self._ctx(org, OrganisationDesignForm(instance=design)))

    def post(self, request, slug):
        org = _get_org_for_admin(request, slug)
        design, _ = OrganisationDesign.objects.get_or_create(organisation=org)
        form = OrganisationDesignForm(request.POST, request.FILES, instance=design)
        if form.is_valid():
            form.save()
            messages.success(request, "Design gespeichert.")
            return redirect("org_design", slug=slug)
        return render(request, "organisations/design_editor.html", self._ctx(org, form))


# --------------------------------------------------------------------------- #
# Organisations-Startseite (WYSIWYG)
# --------------------------------------------------------------------------- #
class OrgStartseiteView(RollenMixin, View):
    rolle = Rolle.ORG_ADMIN

    def _ctx(self, org, form, weiterleitung_form=None):
        return {
            "form": form,
            "weiterleitung_form": weiterleitung_form or OrganisationWeiterleitungForm(instance=org),
            "org": org,
            "tenant_org": org,
        }

    def get(self, request, slug):
        org = _get_org_for_admin(request, slug)
        seite, _ = OrganisationStartseite.objects.get_or_create(organisation=org)
        return render(request, "organisations/startseite_editor.html",
                      self._ctx(org, OrganisationStartseiteForm(instance=seite)))

    def post(self, request, slug):
        org = _get_org_for_admin(request, slug)
        seite, _ = OrganisationStartseite.objects.get_or_create(organisation=org)
        form = OrganisationStartseiteForm(request.POST, request.FILES, instance=seite)
        weiterleitung_form = OrganisationWeiterleitungForm(request.POST, instance=org)
        if form.is_valid() and weiterleitung_form.is_valid():
            form.save()
            weiterleitung_form.save()
            messages.success(request, "Startseite gespeichert.")
            return redirect("org_startseite", slug=slug)
        return render(request, "organisations/startseite_editor.html", self._ctx(org, form, weiterleitung_form))


class OrgStartseitePageBuilderView(RollenMixin, View):
    rolle = Rolle.ORG_ADMIN

    def _ctx(self, org, seite):
        try:
            builder_html = seite.inhalt.html
        except Exception:
            builder_html = ""
        return {
            "org": org,
            "tenant_org": org,
            "seite": seite,
            "builder_html": builder_html or "",
            "weiterleitung_form": OrganisationWeiterleitungForm(instance=org),
        }

    def get(self, request, slug):
        org = _get_org_for_admin(request, slug)
        seite, _ = OrganisationStartseite.objects.get_or_create(organisation=org)
        return render(request, "organisations/startseite_pagebuilder.html", self._ctx(org, seite))

    def post(self, request, slug):
        org = _get_org_for_admin(request, slug)
        seite, _ = OrganisationStartseite.objects.get_or_create(organisation=org)
        weiterleitung_form = OrganisationWeiterleitungForm(request.POST, instance=org)
        if not weiterleitung_form.is_valid():
            messages.error(request, "Weiterleitungs-URL konnte nicht gespeichert werden.")
            context = self._ctx(org, seite)
            context["weiterleitung_form"] = weiterleitung_form
            return render(request, "organisations/startseite_pagebuilder.html", context)

        seite.aktiv = request.POST.get("aktiv") == "on"
        seite.hero_titel = request.POST.get("hero_titel", "").strip()
        seite.hero_untertitel = request.POST.get("hero_untertitel", "").strip()
        seite.hero_button_text = request.POST.get("hero_button_text", "").strip() or "Kurse entdecken"
        if request.FILES.get("hero_bild"):
            seite.hero_bild = request.FILES["hero_bild"]
        html = request.POST.get("builder_html", "").strip()
        seite.inhalt = Quill(json.dumps({"delta": "", "html": html}))
        seite.save()
        weiterleitung_form.save()
        messages.success(request, "PageBuilder-Inhalt gespeichert.")
        return redirect("org_startseite_pagebuilder", slug=org.slug)


# --------------------------------------------------------------------------- #
# Öffentliche Organisations-Startseite
# --------------------------------------------------------------------------- #
class OffentlicheStartseiteRedirectView(View):
    def get(self, request, slug):
        return redirect("org_public_home", slug=slug, permanent=True)


class OffentlicheStartseiteView(TemplateView):
    template_name = "organisations/public_home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from apps.courses.models import Kurs

        org = get_object_or_404(Organisation, slug=self.kwargs["slug"], aktiv=True)
        try:
            startseite = org.startseite if org.startseite.aktiv else None
        except OrganisationStartseite.DoesNotExist:
            startseite = None
        try:
            org_design = org.design
        except OrganisationDesign.DoesNotExist:
            org_design = None

        kurse = (
            Kurs.objects.filter(organisation=org, ist_veroeffentlicht=True)
            .order_by("-erstellt_am")[:6]
        )
        context.update({
            "org": org,
            "tenant_org": org,
            "meine_org": org,
            "startseite": startseite,
            "org_design": org_design,
            "kurse": kurse,
        })
        return context


class SingleSystemStartseiteView(OffentlicheStartseiteView):
    """Zentrale Startseite ohne sichtbaren Organisations-Slug."""

    def get_context_data(self, **kwargs):
        self.kwargs["slug"] = settings.SINGLE_SYSTEM_ORGANISATION_SLUG
        if not Organisation.objects.filter(slug=self.kwargs["slug"], aktiv=True).exists():
            fallback = Organisation.objects.filter(aktiv=True).order_by("pk").first()
            if fallback:
                self.kwargs["slug"] = fallback.slug
        return super().get_context_data(**kwargs)


class SingleSystemStartseiteEditorView(OrgStartseiteView):
    """Optionaler Pagebuilder unter /startseite ohne Mandantenpräfix."""

    def _slug(self):
        configured = Organisation.objects.filter(slug=settings.SINGLE_SYSTEM_ORGANISATION_SLUG, aktiv=True).first()
        return (configured or Organisation.objects.filter(aktiv=True).order_by("pk").first()).slug

    def get(self, request):
        return super().get(request, self._slug())

    def post(self, request):
        return super().post(request, self._slug())


class SingleSystemPageBuilderView(OrgStartseitePageBuilderView):
    def _slug(self):
        configured = Organisation.objects.filter(slug=settings.SINGLE_SYSTEM_ORGANISATION_SLUG, aktiv=True).first()
        return (configured or Organisation.objects.filter(aktiv=True).order_by("pk").first()).slug

    def get(self, request):
        return super().get(request, self._slug())

    def post(self, request):
        return super().post(request, self._slug())


# --------------------------------------------------------------------------- #
# Superadmin-Übersicht
# --------------------------------------------------------------------------- #
class SuperadminOrganisationenView(LoginRequiredMixin, ListView):
    template_name = "organisations/superadmin_overview.html"
    context_object_name = "organisationen"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return Organisation.objects.annotate(
            mitglieder_count=Count("userprofile", distinct=True),
            kurs_count=Count("kurs", distinct=True),
        ).order_by("name")


class EinladungAnnehmenView(LoginRequiredMixin, View):
    def get(self, request, token):
        einladung = get_object_or_404(Einladung, token=token, akzeptiert_am__isnull=True)
        if einladung.ist_abgelaufen:
            messages.error(request, "Diese Einladung ist abgelaufen.")
            return redirect("dashboard")
        if request.user.email and request.user.email.lower() != einladung.email.lower():
            messages.error(request, "Diese Einladung ist fuer eine andere E-Mail-Adresse ausgestellt.")
            return redirect("dashboard")
        if not settings.SINGLE_SYSTEM_MODE and einladung.organisation.max_nutzer and einladung.organisation.max_nutzer > 0:
            aktuell = UserProfile.objects.filter(
                organisation=einladung.organisation,
                aktiv=True,
            ).values("nutzer").distinct().count()
            if aktuell >= einladung.organisation.max_nutzer:
                messages.error(request, "Das Nutzerlimit dieser Organisation ist erreicht.")
                return redirect("dashboard")
        UserProfile.objects.get_or_create(
            nutzer=request.user,
            organisation=einladung.organisation,
            rolle=einladung.rolle,
            defaults={"aktiv": True},
        )
        einladung.akzeptiert_am = timezone.now()
        einladung.save(update_fields=["akzeptiert_am"])
        if einladung.pruefung_id and einladung.rolle == Rolle.LEARNER:
            from apps.exams.models import PruefungsAnmeldung
            PruefungsAnmeldung.objects.get_or_create(
                nutzer=request.user, pruefung=einladung.pruefung
            )
        try:
            from apps.payments.services import log_audit
            log_audit(
                actor=request.user,
                organisation=einladung.organisation,
                action="einladung_angenommen",
                obj=einladung,
                message=f"Einladung fuer {einladung.email} wurde angenommen.",
                metadata={"rolle": einladung.rolle},
            )
        except Exception:
            pass
        messages.success(request, "Dein Benutzerzugang wurde freigeschaltet.")
        return redirect("org_admin_dashboard", slug=einladung.organisation.slug) if einladung.rolle == Rolle.ORG_ADMIN else redirect("dashboard")
