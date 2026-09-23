from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Avg, Count, Prefetch, Q, Sum
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, TemplateView, UpdateView

from apps.accounts.mixins import RollenMixin
from apps.accounts.models import Rolle
from apps.organisations.models import Organisation, OrganisationDesign

from .forms import (
    AbschnittForm,
    BegleitmaterialForm,
    KursBewertungForm,
    KursKategorieForm,
    KursForm,
    LektionForm,
    LektionMedienForm,
    LernpfadForm,
    LernpfadKursForm,
    UebungsantwortForm,
    UebungsfrageForm,
)
from .video_thumbnails import generate_lesson_video_thumbnail

from .models import (
    Abschnitt,
    Begleitmaterial,
    Einschreibung,
    Kurs,
    KursBewertung,
    KursKategorie,
    Lektion,
    Lernpfad,
    LernpfadEinschreibung,
    LernpfadKurs,
    LektionsFortschritt,
    Uebungsantwort,
    Uebungsfrage,
)

def trainer_course_queryset(user):
    queryset = Kurs.objects.select_related("organisation", "erstellt_von")
    if not user.is_authenticated:
        return queryset.none()
    if user.is_superuser:
        return queryset
    organisation_ids = user.profile.filter(rolle=Rolle.TRAINER, aktiv=True).values_list("organisation_id", flat=True)
    return queryset.filter(organisation_id__in=organisation_ids)


def kurszugriff_bezahlt(user, kurs):
    if kurs.ist_kostenlos or kurs.preis <= 0:
        return True
    if not user.is_authenticated:
        return False
    return Einschreibung.objects.filter(nutzer=user, kurs=kurs, bezahlt=True).exists()


def get_tenant_org(slug):
    if not slug:
        return None
    if settings.SINGLE_SYSTEM_MODE:
        from django.http import Http404
        raise Http404("Mandantenpfade sind im Einzelsystem deaktiviert.")
    return get_object_or_404(Organisation, slug=slug, aktiv=True)


def ensure_learning_paths_enabled():
    if settings.SINGLE_SYSTEM_MODE:
        from django.http import Http404
        raise Http404("Lernpfade sind im ML-Einzelsystem nicht aktiviert.")


class LearningPathsEnabledMixin:
    def dispatch(self, request, *args, **kwargs):
        ensure_learning_paths_enabled()
        return super().dispatch(request, *args, **kwargs)


def scope_to_active_org(queryset, request):
    active_org = getattr(request, "tenant_org", None)
    if active_org and request.user.is_authenticated and not request.user.is_superuser:
        return queryset.filter(organisation=active_org)
    return queryset


def tenant_reverse(name, obj, **kwargs):
    if obj and getattr(obj, "organisation", None):
        tenant_name = f"tenant_{name}"
        return reverse(tenant_name, kwargs={"org_slug": obj.organisation.slug, **kwargs})
    return reverse(name, kwargs=kwargs)


def tenant_context(org):
    if not org:
        return {}
    try:
        org_design = org.design
    except OrganisationDesign.DoesNotExist:
        org_design = None
    return {"tenant_org": org, "meine_org": org, "org_design": org_design}


class DashboardCourseMixin(LoginRequiredMixin):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["einschreibungen"] = (
            Einschreibung.objects.filter(nutzer=self.request.user)
            .select_related("kurs", "kurs__organisation")
            .order_by("-eingeschrieben_am")
        )
        return context


class KursKatalogView(ListView):
    model = Kurs
    template_name = "courses/catalog.html"
    context_object_name = "kurse"
    paginate_by = 12

    def dispatch(self, request, *args, **kwargs):
        if (
            settings.SINGLE_SYSTEM_MODE
        ):
            raise Http404("Der öffentliche Kurskatalog ist im ML-Prüfungsportal nicht aktiviert.")
        self.tenant_org = get_tenant_org(kwargs.get("org_slug")) if kwargs.get("org_slug") else None
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        queryset = (
            Kurs.objects.filter(ist_veroeffentlicht=True, organisation__aktiv=True)
            .select_related("organisation", "erstellt_von")
            .prefetch_related("abschnitte__lektionen", "bewertungen")
        )
        query = self.request.GET.get("q", "").strip()
        niveau = self.request.GET.get("niveau", "").strip()
        sprache = self.request.GET.get("sprache", "").strip()
        preis = self.request.GET.get("preis", "").strip()
        if self.tenant_org:
            queryset = queryset.filter(organisation=self.tenant_org)
        if getattr(self.request, "tenant_org", None) and self.request.user.is_authenticated and not self.request.user.is_superuser:
            queryset = queryset.filter(organisation=self.request.tenant_org)
        if query:
            queryset = queryset.filter(Q(titel__icontains=query) | Q(beschreibung__icontains=query))
        if niveau:
            queryset = queryset.filter(niveau=niveau)
        if sprache:
            queryset = queryset.filter(sprache=sprache)
        if preis == "kostenlos":
            queryset = queryset.filter(ist_kostenlos=True)
        elif preis == "bezahlt":
            queryset = queryset.filter(ist_kostenlos=False)
        if self.request.GET.get("kategorie"):
            queryset = queryset.filter(kategorie_id=self.request.GET["kategorie"])
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["filter"] = self.request.GET
        context["niveau_choices"] = Kurs._meta.get_field("niveau").choices
        context["kategorie_choices"] = KursKategorie.objects.filter(
            organisation=self.tenant_org
        ).select_related("parent") if self.tenant_org else KursKategorie.objects.all().select_related("parent")
        context.update(tenant_context(self.tenant_org))
        return context


class KursDetailView(DetailView):
    model = Kurs
    template_name = "courses/detail.html"
    context_object_name = "kurs"
    slug_url_kwarg = "slug"

    def dispatch(self, request, *args, **kwargs):
        self.tenant_org = get_tenant_org(kwargs.get("org_slug")) if kwargs.get("org_slug") else None
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        queryset = (
            Kurs.objects.filter(ist_veroeffentlicht=True, organisation__aktiv=True)
            .select_related("organisation", "erstellt_von")
            .prefetch_related("abschnitte__lektionen", "bewertungen")
        )
        if self.tenant_org:
            queryset = queryset.filter(organisation=self.tenant_org)
        if getattr(self.request, "tenant_org", None) and self.request.user.is_authenticated and not self.request.user.is_superuser:
            queryset = queryset.filter(organisation=self.request.tenant_org)
        return queryset

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from apps.payments.services import lade_zahlungseinstellungen, payments_enabled
        context["payment_aktiv"] = payments_enabled() and lade_zahlungseinstellungen(self.object.organisation).payment_aktiv
        if self.request.user.is_authenticated:
            context["einschreibung"] = Einschreibung.objects.filter(
                nutzer=self.request.user,
                kurs=self.object,
                bezahlt=True,
            ).first()
        context.update(tenant_context(self.object.organisation))
        return context


class EinschreibenView(LoginRequiredMixin, View):
    def post(self, request, slug, org_slug=None):
        queryset = Kurs.objects.filter(slug=slug, ist_veroeffentlicht=True, organisation__aktiv=True)
        if org_slug:
            queryset = queryset.filter(organisation__slug=org_slug)
        queryset = scope_to_active_org(queryset, request)
        kurs = get_object_or_404(queryset)
        if not kurs.ist_kostenlos and kurs.preis > 0:
            from apps.payments.services import payments_enabled
            if not payments_enabled():
                messages.error(request, "Kostenpflichtige Kurse sind in dieser Installation nicht aktiviert.")
                return redirect("course_detail", slug=kurs.slug)
            return redirect("course_checkout", slug=kurs.slug)
        Einschreibung.objects.update_or_create(nutzer=request.user, kurs=kurs, defaults={"bezahlt": True})
        if kurs.pruefung_id:
            from apps.exams.models import PruefungsAnmeldung
            PruefungsAnmeldung.objects.get_or_create(nutzer=request.user, pruefung=kurs.pruefung)
        messages.success(request, "Du bist in den Kurs eingeschrieben.")
        if org_slug:
            return redirect("tenant_course_learn", org_slug=kurs.organisation.slug, slug=kurs.slug)
        return redirect("course_learn", slug=kurs.slug)


class KursLernenView(LoginRequiredMixin, DetailView):
    model = Kurs
    template_name = "courses/learn.html"
    context_object_name = "kurs"
    slug_url_kwarg = "slug"

    def get_queryset(self):
        queryset = Kurs.objects.filter(ist_veroeffentlicht=True)
        if self.tenant_org:
            queryset = queryset.filter(organisation=self.tenant_org)
        queryset = scope_to_active_org(queryset, self.request)
        return queryset.prefetch_related(
            Prefetch(
                "abschnitte",
                queryset=Abschnitt.objects.prefetch_related(
                    "lektionen__materialien",
                    "lektionen__uebungsfragen__antworten",
                ),
            )
        )

    def dispatch(self, request, *args, **kwargs):
        self.tenant_org = get_tenant_org(kwargs.get("org_slug")) if kwargs.get("org_slug") else None
        self.object = self.get_object()
        if not kurszugriff_bezahlt(request.user, self.object):
            from apps.payments.services import payments_enabled
            if not payments_enabled():
                messages.error(request, "Dieser kostenpflichtige Kurs ist in dieser Installation nicht freigeschaltet.")
                return redirect("course_detail", slug=self.object.slug)
            messages.warning(request, "Bitte bezahle den Kurs, um unbegrenzten Zugriff zu erhalten.")
            return redirect("course_checkout", slug=self.object.slug)
        self.einschreibung, _ = Einschreibung.objects.update_or_create(
            nutzer=request.user,
            kurs=self.object,
            defaults={"bezahlt": True},
        )
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        erste_lektion = Lektion.objects.filter(abschnitt__kurs=self.object).order_by(
            "abschnitt__reihenfolge",
            "reihenfolge",
        ).first()
        context["lektion"] = erste_lektion
        context.update(self._learning_context(erste_lektion))
        context.update(tenant_context(self.object.organisation))
        return context

    def _learning_context(self, lektion):
        abgeschlossene_ids = set(
            LektionsFortschritt.objects.filter(einschreibung=self.einschreibung).values_list(
                "lektion_id",
                flat=True,
            )
        )
        return {
            "einschreibung": self.einschreibung,
            "abgeschlossene_ids": abgeschlossene_ids,
            "vorherige_lektion": None,
            "naechste_lektion": self._naechste_lektion(lektion),
            "uebung_ergebnis": self.request.session.pop(f"lesson_exercise_{lektion.id}", None) if lektion else None,
        }

    def _naechste_lektion(self, lektion):
        if not lektion:
            return None
        lektionen = list(
            Lektion.objects.filter(abschnitt__kurs=self.object).order_by("abschnitt__reihenfolge", "reihenfolge")
        )
        try:
            index = lektionen.index(lektion)
        except ValueError:
            return None
        return lektionen[index + 1] if index + 1 < len(lektionen) else None


class LektionDetailView(KursLernenView):
    def get_context_data(self, **kwargs):
        context = {"kurs": self.object, "object": self.object}
        lektion = get_object_or_404(Lektion, id=self.kwargs["lektion_id"], abschnitt__kurs=self.object)
        lektionen = list(
            Lektion.objects.filter(abschnitt__kurs=self.object).order_by("abschnitt__reihenfolge", "reihenfolge")
        )
        index = lektionen.index(lektion)
        context["lektion"] = lektion
        context.update(tenant_context(self.object.organisation))
        context.update(
            {
                **self._learning_context(lektion),
                "vorherige_lektion": lektionen[index - 1] if index > 0 else None,
                "naechste_lektion": lektionen[index + 1] if index + 1 < len(lektionen) else None,
            }
        )
        return context


class LektionAbschliessenView(LoginRequiredMixin, View):
    def post(self, request, slug, lektion_id, org_slug=None):
        queryset = Kurs.objects.filter(slug=slug, ist_veroeffentlicht=True)
        if org_slug:
            queryset = queryset.filter(organisation__slug=org_slug)
        queryset = scope_to_active_org(queryset, request)
        kurs = get_object_or_404(queryset)
        if not kurszugriff_bezahlt(request.user, kurs):
            return redirect("course_checkout", slug=kurs.slug)
        einschreibung, _ = Einschreibung.objects.get_or_create(nutzer=request.user, kurs=kurs)
        lektion = get_object_or_404(Lektion, id=lektion_id, abschnitt__kurs=kurs)
        LektionsFortschritt.objects.get_or_create(einschreibung=einschreibung, lektion=lektion)
        einschreibung.aktualisiere_fortschritt()
        messages.success(request, "Lektion wurde als abgeschlossen markiert.")
        if org_slug:
            return redirect("tenant_course_lesson", org_slug=kurs.organisation.slug, slug=kurs.slug, lektion_id=lektion.id)
        return redirect("course_lesson", slug=kurs.slug, lektion_id=lektion.id)


class LektionUebungPruefenView(LoginRequiredMixin, View):
    def post(self, request, slug, lektion_id, org_slug=None):
        queryset = Kurs.objects.filter(slug=slug, ist_veroeffentlicht=True)
        if org_slug:
            queryset = queryset.filter(organisation__slug=org_slug)
        queryset = scope_to_active_org(queryset, request)
        kurs = get_object_or_404(queryset)
        get_object_or_404(Einschreibung, nutzer=request.user, kurs=kurs, bezahlt=True)
        lektion = get_object_or_404(Lektion, id=lektion_id, abschnitt__kurs=kurs)
        fragen = list(lektion.uebungsfragen.filter(aktiv=True).prefetch_related("antworten"))
        richtig = 0
        details = []
        for frage in fragen:
            ausgewaehlt = set(request.POST.getlist(f"uebungsfrage_{frage.id}"))
            korrekt = {str(antwort.id) for antwort in frage.antworten.filter(ist_korrekt=True)}
            ist_richtig = ausgewaehlt == korrekt
            if ist_richtig:
                richtig += 1
            details.append(
                {
                    "frage": frage.frage,
                    "ist_richtig": ist_richtig,
                    "erklaerung": frage.erklaerung,
                }
            )
        request.session[f"lesson_exercise_{lektion.id}"] = {
            "richtig": richtig,
            "gesamt": len(fragen),
            "details": details,
        }
        if org_slug:
            return redirect("tenant_course_lesson", org_slug=kurs.organisation.slug, slug=kurs.slug, lektion_id=lektion.id)
        return redirect("course_lesson", slug=kurs.slug, lektion_id=lektion.id)


class TrainerKursListView(RollenMixin, ListView):
    rolle = Rolle.TRAINER
    model = Kurs
    template_name = "courses/trainer/course_list.html"
    context_object_name = "kurse"

    def get_queryset(self):
        return trainer_course_queryset(self.request.user)


class TrainerKategorieListView(RollenMixin, ListView):
    rolle = Rolle.TRAINER
    template_name = "courses/trainer/category_list.html"
    context_object_name = "kategorien"

    def get_queryset(self):
        if self.request.user.is_superuser:
            return KursKategorie.objects.select_related("organisation", "parent")
        org_ids = self.request.user.profile.filter(rolle=Rolle.TRAINER, aktiv=True).values_list("organisation_id", flat=True)
        return KursKategorie.objects.filter(organisation_id__in=org_ids).select_related("organisation", "parent")


class TrainerKategorieCreateView(RollenMixin, CreateView):
    rolle = Rolle.TRAINER
    form_class = KursKategorieForm
    template_name = "courses/trainer/category_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_success_url(self):
        return reverse("trainer_category_list")


class TrainerKursCreateView(RollenMixin, CreateView):
    rolle = Rolle.TRAINER
    model = Kurs
    form_class = KursForm
    template_name = "courses/trainer/course_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        org = form.cleaned_data.get("organisation")
        if org and org.ist_demo_organisation:
            from apps.exams.models import Pruefung
            if Kurs.objects.filter(organisation=org).count() + Pruefung.objects.filter(organisation=org).count() >= org.demo_inhalte_startbestand + 3:
                form.add_error(None, "In der Demo-Organisation koennen zusaetzlich hoechstens drei Kurse oder Zertifikatspruefungen angelegt werden.")
                return self.form_invalid(form)
        if org and org.max_kurse and org.max_kurse > 0:
            if Kurs.objects.filter(organisation=org).count() >= org.max_kurse:
                messages.error(
                    self.request,
                    f"Kurslimit ({org.max_kurse}) dieser Organisation erreicht. "
                    "Bitte upgraden Sie die Lizenz.",
                )
                return self.form_invalid(form)
        form.instance.erstellt_von = self.request.user
        messages.success(self.request, "Kurs wurde erstellt.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("trainer_course_edit", kwargs={"slug": self.object.slug})


class TrainerKursUpdateView(RollenMixin, UpdateView):
    rolle = Rolle.TRAINER
    model = Kurs
    form_class = KursForm
    template_name = "courses/trainer/course_form.html"
    slug_url_kwarg = "slug"

    def get_queryset(self):
        return trainer_course_queryset(self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, "Kurs wurde gespeichert.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("trainer_course_edit", kwargs={"slug": self.object.slug})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["abschnitt_form"] = AbschnittForm()
        context["lektion_form"] = LektionForm()
        context["material_form"] = BegleitmaterialForm()
        context["uebungsfrage_form"] = UebungsfrageForm()
        context["uebungsantwort_form"] = UebungsantwortForm()
        context["abschnitte"] = self.object.abschnitte.prefetch_related(
            "lektionen__materialien",
            "lektionen__uebungsfragen__antworten",
        )
        return context


class TrainerAbschnittCreateView(RollenMixin, View):
    rolle = Rolle.TRAINER

    def post(self, request, slug):
        kurs = get_object_or_404(trainer_course_queryset(request.user), slug=slug)
        form = AbschnittForm(request.POST)
        if form.is_valid():
            abschnitt = form.save(commit=False)
            abschnitt.kurs = kurs
            abschnitt.save()
            messages.success(request, "Abschnitt wurde erstellt.")
        else:
            messages.error(request, "Abschnitt konnte nicht erstellt werden.")
        return redirect("trainer_course_edit", slug=kurs.slug)


class TrainerLektionCreateView(RollenMixin, View):
    rolle = Rolle.TRAINER

    def post(self, request, slug, abschnitt_id):
        kurs = get_object_or_404(trainer_course_queryset(request.user), slug=slug)
        abschnitt = get_object_or_404(Abschnitt, id=abschnitt_id, kurs=kurs)
        form = LektionForm(request.POST, request.FILES)
        if form.is_valid():
            lektion = form.save(commit=False)
            lektion.abschnitt = abschnitt
            lektion.save()
            thumbnail_created = generate_lesson_video_thumbnail(lektion)
            if thumbnail_created:
                messages.success(request, "Lektion wurde erstellt und Video-Thumbnail erzeugt.")
            else:
                messages.success(request, "Lektion wurde erstellt.")
        else:
            messages.error(request, "Lektion konnte nicht erstellt werden: " + "; ".join(f"{field}: {errors}" for field, errors in form.errors.items()))
        return redirect("trainer_course_edit", slug=kurs.slug)


class TrainerLektionMedienUpdateView(RollenMixin, View):
    rolle = Rolle.TRAINER

    def post(self, request, slug, lektion_id):
        kurs = get_object_or_404(trainer_course_queryset(request.user), slug=slug)
        lektion = get_object_or_404(Lektion, id=lektion_id, abschnitt__kurs=kurs)
        form = LektionMedienForm(request.POST, request.FILES, instance=lektion)
        if form.is_valid():
            lektion = form.save()
            thumbnail_created = generate_lesson_video_thumbnail(lektion)
            if thumbnail_created:
                messages.success(request, "Lektionsmedium wurde gespeichert und Video-Thumbnail erzeugt.")
            else:
                messages.success(request, "Lektionsmedium wurde gespeichert.")
        else:
            messages.error(request, "Lektionsmedium konnte nicht gespeichert werden: " + "; ".join(f"{field}: {errors}" for field, errors in form.errors.items()))
        return redirect("trainer_course_edit", slug=kurs.slug)


class TrainerMaterialCreateView(RollenMixin, View):
    rolle = Rolle.TRAINER

    def post(self, request, slug, lektion_id):
        kurs = get_object_or_404(trainer_course_queryset(request.user), slug=slug)
        lektion = get_object_or_404(Lektion, id=lektion_id, abschnitt__kurs=kurs)
        form = BegleitmaterialForm(request.POST, request.FILES)
        if form.is_valid():
            material = form.save(commit=False)
            material.lektion = lektion
            material.save()
            messages.success(request, "Begleitmaterial wurde hochgeladen.")
        else:
            messages.error(request, "Begleitmaterial konnte nicht gespeichert werden: " + "; ".join(f"{field}: {errors}" for field, errors in form.errors.items()))
        return redirect("trainer_course_edit", slug=kurs.slug)


class TrainerUebungsfrageCreateView(RollenMixin, View):
    rolle = Rolle.TRAINER

    def post(self, request, slug, lektion_id):
        kurs = get_object_or_404(trainer_course_queryset(request.user), slug=slug)
        lektion = get_object_or_404(Lektion, id=lektion_id, abschnitt__kurs=kurs)
        form = UebungsfrageForm(request.POST)
        if form.is_valid():
            frage = form.save(commit=False)
            frage.lektion = lektion
            frage.save()
            messages.success(request, "Uebungsfrage wurde erstellt.")
        else:
            messages.error(request, "Uebungsfrage konnte nicht gespeichert werden.")
        return redirect("trainer_course_edit", slug=kurs.slug)


class TrainerUebungsantwortCreateView(RollenMixin, View):
    rolle = Rolle.TRAINER

    def post(self, request, slug, frage_id):
        kurs = get_object_or_404(trainer_course_queryset(request.user), slug=slug)
        frage = get_object_or_404(Uebungsfrage, id=frage_id, lektion__abschnitt__kurs=kurs)
        form = UebungsantwortForm(request.POST)
        if form.is_valid():
            antwort = form.save(commit=False)
            antwort.frage = frage
            antwort.save()
            messages.success(request, "Uebungsantwort wurde erstellt.")
        else:
            messages.error(request, "Uebungsantwort konnte nicht gespeichert werden.")
        return redirect("trainer_course_edit", slug=kurs.slug)


class KursBewertungCreateView(LoginRequiredMixin, View):
    def post(self, request, slug):
        kurs = get_object_or_404(Kurs, slug=slug, ist_veroeffentlicht=True, organisation__aktiv=True)
        if not Einschreibung.objects.filter(nutzer=request.user, kurs=kurs, bezahlt=True).exists():
            messages.error(request, "Nur eingeschriebene Nutzer koennen diesen Kurs bewerten.")
            return redirect("course_detail", slug=kurs.slug)
        form = KursBewertungForm(request.POST)
        if form.is_valid():
            KursBewertung.objects.update_or_create(
                kurs=kurs,
                nutzer=request.user,
                defaults=form.cleaned_data,
            )
            messages.success(request, "Bewertung wurde gespeichert.")
        else:
            messages.error(request, "Bewertung konnte nicht gespeichert werden.")
        return redirect("course_detail", slug=kurs.slug)


class LernpfadListView(ListView):
    model = Lernpfad
    template_name = "courses/learning_path_list.html"
    context_object_name = "lernpfade"
    paginate_by = 12

    def dispatch(self, request, *args, **kwargs):
        ensure_learning_paths_enabled()
        self.tenant_org = get_tenant_org(kwargs.get("org_slug")) if kwargs.get("org_slug") else None
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        queryset = Lernpfad.objects.filter(
            ist_veroeffentlicht=True,
            organisation__aktiv=True,
        ).select_related("organisation").prefetch_related("pfad_kurse__kurs")
        if self.tenant_org:
            queryset = queryset.filter(organisation=self.tenant_org)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(tenant_context(self.tenant_org))
        return context


class LernpfadDetailView(DetailView):
    model = Lernpfad
    template_name = "courses/learning_path_detail.html"
    context_object_name = "lernpfad"
    slug_url_kwarg = "slug"

    def dispatch(self, request, *args, **kwargs):
        ensure_learning_paths_enabled()
        self.tenant_org = get_tenant_org(kwargs.get("org_slug")) if kwargs.get("org_slug") else None
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        queryset = Lernpfad.objects.filter(
            ist_veroeffentlicht=True,
            organisation__aktiv=True,
        ).select_related("organisation").prefetch_related("pfad_kurse__kurs")
        if self.tenant_org:
            queryset = queryset.filter(organisation=self.tenant_org)
        return queryset

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        einschreibung = None
        if self.request.user.is_authenticated:
            einschreibung = LernpfadEinschreibung.objects.filter(
                nutzer=self.request.user,
                lernpfad=self.object,
            ).first()
        context["einschreibung"] = einschreibung
        context.update(tenant_context(self.object.organisation))
        return context


class LernpfadEinschreibenView(LearningPathsEnabledMixin, LoginRequiredMixin, View):
    def post(self, request, slug, org_slug=None):
        queryset = Lernpfad.objects.filter(slug=slug, ist_veroeffentlicht=True, organisation__aktiv=True)
        if org_slug:
            queryset = queryset.filter(organisation__slug=org_slug)
        lernpfad = get_object_or_404(queryset)
        LernpfadEinschreibung.objects.get_or_create(nutzer=request.user, lernpfad=lernpfad)
        for pfad_kurs in lernpfad.pfad_kurse.select_related("kurs"):
            if pfad_kurs.kurs.ist_kostenlos or pfad_kurs.kurs.preis <= 0:
                Einschreibung.objects.update_or_create(
                    nutzer=request.user,
                    kurs=pfad_kurs.kurs,
                    defaults={"bezahlt": True},
                )
        messages.success(request, "Du bist in den Lernpfad eingeschrieben.")
        if org_slug:
            return redirect("tenant_learning_path_detail", org_slug=lernpfad.organisation.slug, slug=lernpfad.slug)
        return redirect("learning_path_detail", slug=lernpfad.slug)


class TrainerUmsatzDashboardView(RollenMixin, TemplateView):
    rolle = Rolle.TRAINER
    template_name = "courses/trainer/revenue_dashboard.html"

    def dispatch(self, request, *args, **kwargs):
        if settings.SINGLE_SYSTEM_MODE:
            raise Http404("Das Umsatzdashboard ist im ML-Prüfungsportal nicht aktiviert.")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from apps.payments.models import Zahlung, Zahlungsstatus

        zahlungen = Zahlung.objects.filter(trainer=self.request.user, status=Zahlungsstatus.BEZAHLT)
        context["summe_brutto"] = zahlungen.aggregate(total=Sum("betrag_brutto"))["total"] or 0
        context["summe_trainer"] = zahlungen.aggregate(total=Sum("trainer_anteil"))["total"] or 0
        context["zahlungen_count"] = zahlungen.count()
        context["kurs_summen"] = (
            zahlungen.values("kurs__titel")
            .annotate(brutto=Sum("betrag_brutto"), trainer=Sum("trainer_anteil"), anzahl=Count("id"))
            .order_by("-trainer")
        )
        context["letzte_zahlungen"] = zahlungen.select_related("kurs", "nutzer").order_by("-bezahlt_am")[:10]
        return context


def trainer_learning_path_queryset(user):
    queryset = Lernpfad.objects.select_related("organisation", "erstellt_von").prefetch_related("pfad_kurse__kurs")
    if not user.is_authenticated:
        return queryset.none()
    if user.is_superuser:
        return queryset
    organisation_ids = user.profile.filter(rolle=Rolle.TRAINER, aktiv=True).values_list("organisation_id", flat=True)
    return queryset.filter(organisation_id__in=organisation_ids)


class TrainerLernpfadListView(LearningPathsEnabledMixin, RollenMixin, ListView):
    rolle = Rolle.TRAINER
    template_name = "courses/trainer/learning_path_list.html"
    context_object_name = "lernpfade"

    def get_queryset(self):
        return trainer_learning_path_queryset(self.request.user).order_by("organisation__name", "titel")


class TrainerLernpfadCreateView(LearningPathsEnabledMixin, RollenMixin, CreateView):
    rolle = Rolle.TRAINER
    form_class = LernpfadForm
    template_name = "courses/trainer/learning_path_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.erstellt_von = self.request.user
        messages.success(self.request, "Lernpfad wurde erstellt.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("trainer_learning_path_edit", kwargs={"slug": self.object.slug})


class TrainerLernpfadUpdateView(LearningPathsEnabledMixin, RollenMixin, UpdateView):
    rolle = Rolle.TRAINER
    form_class = LernpfadForm
    template_name = "courses/trainer/learning_path_form.html"
    slug_url_kwarg = "slug"

    def get_queryset(self):
        return trainer_learning_path_queryset(self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["kurs_form"] = LernpfadKursForm(lernpfad=self.object)
        context["pfad_kurse"] = self.object.pfad_kurse.select_related("kurs").order_by("reihenfolge", "kurs__titel")
        return context

    def form_valid(self, form):
        messages.success(self.request, "Lernpfad wurde gespeichert.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("trainer_learning_path_edit", kwargs={"slug": self.object.slug})


class TrainerLernpfadKursCreateView(LearningPathsEnabledMixin, RollenMixin, View):
    rolle = Rolle.TRAINER

    def post(self, request, slug):
        lernpfad = get_object_or_404(trainer_learning_path_queryset(request.user), slug=slug)
        form = LernpfadKursForm(request.POST, lernpfad=lernpfad)
        if form.is_valid():
            link = form.save(commit=False)
            link.lernpfad = lernpfad
            link.save()
            messages.success(request, "Kurs wurde dem Lernpfad hinzugefuegt.")
        else:
            messages.error(request, "Kurs konnte nicht hinzugefuegt werden: " + "; ".join(f"{field}: {errors}" for field, errors in form.errors.items()))
        return redirect("trainer_learning_path_edit", slug=lernpfad.slug)


class TrainerLernpfadKursDeleteView(LearningPathsEnabledMixin, RollenMixin, View):
    rolle = Rolle.TRAINER

    def post(self, request, slug, link_id):
        lernpfad = get_object_or_404(trainer_learning_path_queryset(request.user), slug=slug)
        link = get_object_or_404(LernpfadKurs, id=link_id, lernpfad=lernpfad)
        link.delete()
        messages.success(request, "Kurs wurde aus dem Lernpfad entfernt.")
        return redirect("trainer_learning_path_edit", slug=lernpfad.slug)
