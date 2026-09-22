import json

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Avg, Count
from django.core.files.base import ContentFile
from django.http import FileResponse, Http404, HttpResponse, HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.crypto import salted_hmac
from django.views import View
from django.views.generic import CreateView, DeleteView, DetailView, FormView, ListView, TemplateView, UpdateView

from apps.accounts.mixins import OperatorMixin, RollenMixin
from apps.accounts.models import Rolle

from .forms import (
    AntwortForm,
    CSVImportForm,
    FrageForm,
    FragenkatalogForm,
    FreitextBewertungForm,
    PruefungForm,
    PruefungsThemenquoteFormSet,
    PruefungsFreigabeForm,
    ZuordnungsPaarForm,
)
from .models import Antwort, Frage, Fragenkatalog, FragenTag, Pruefung, PruefungsAnmeldung, PruefungsFreigabe, PruefungsbogenArchiv, PruefungsVersuch, TeilnehmerAntwort, ZuordnungsPaar
from .pdf import generiere_pruefungsbogen_pdf
from .services import (NichtGenugFragenInThema, MaxVersucheErreicht, aktive_sekunden, bestaetige_aktivitaet,
                       pausiere_pruefung, pruefe_zeitlimit, setze_pruefung_fort, speichere_antwort,
                       starte_pruefung, waehle_pruefungsfragen, werte_versuch_aus, restliche_sekunden)


class TrainerOderOperatorMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if request.user.is_superuser or request.user.groups.filter(name=Rolle.SUPERADMIN).exists():
            return super().dispatch(request, *args, **kwargs)
        if request.user.profile.filter(rolle__in=[Rolle.TRAINER, Rolle.EXAM_OPERATOR], aktiv=True).exists():
            return super().dispatch(request, *args, **kwargs)
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied


def trainer_catalog_queryset(user):
    queryset = Fragenkatalog.objects.select_related("organisation", "erstellt_von")
    if not user.is_authenticated:
        return queryset.none()
    if user.is_superuser:
        return queryset
    organisation_ids = user.profile.filter(rolle__in=[Rolle.TRAINER, Rolle.EXAM_OPERATOR], aktiv=True).values_list("organisation_id", flat=True)
    return queryset.filter(organisation_id__in=organisation_ids)


def trainer_exam_queryset(user):
    queryset = Pruefung.objects.select_related("organisation", "fragenkatalog")
    if not user.is_authenticated:
        return queryset.none()
    if user.is_superuser:
        return queryset
    organisation_ids = user.profile.filter(rolle__in=[Rolle.TRAINER, Rolle.EXAM_OPERATOR], aktiv=True).values_list("organisation_id", flat=True)
    return queryset.filter(organisation_id__in=organisation_ids)


class TrainerFragenkatalogListView(TrainerOderOperatorMixin, ListView):
    template_name = "exams/trainer/catalog_list.html"
    context_object_name = "kataloge"

    def get_queryset(self):
        queryset = trainer_catalog_queryset(self.request.user)
        query = self.request.GET.get("q", "").strip()
        if query:
            queryset = queryset.filter(titel__icontains=query)
        return queryset


class TrainerFragenkatalogCreateView(RollenMixin, CreateView):
    rolle = Rolle.EXAM_OPERATOR
    form_class = FragenkatalogForm
    template_name = "exams/trainer/catalog_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.erstellt_von = self.request.user
        messages.success(self.request, "Fragenkatalog wurde erstellt.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("trainer_catalog_edit", kwargs={"pk": self.object.pk})


class TrainerFragenkatalogUpdateView(RollenMixin, UpdateView):
    rolle = Rolle.EXAM_OPERATOR
    form_class = FragenkatalogForm
    template_name = "exams/trainer/catalog_form.html"

    def get_queryset(self):
        return trainer_catalog_queryset(self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_success_url(self):
        return reverse("trainer_catalog_edit", kwargs={"pk": self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        frage_query = self.request.GET.get("q", "").strip()
        fragen_status = self.request.GET.get("aktiv", "alle")
        fragen = self.object.fragen.prefetch_related("antworten", "zuordnungen", "tags")
        if frage_query:
            from django.db.models import Q
            fragen = fragen.filter(Q(fragetext__icontains=frage_query) | Q(id__icontains=frage_query) | Q(erklaerung__icontains=frage_query))
        if fragen_status == "aktiv":
            fragen = fragen.filter(aktiv=True)
        elif fragen_status == "inaktiv":
            fragen = fragen.filter(aktiv=False)
        context["fragen"] = fragen
        context["frage_query"] = frage_query
        context["fragen_status"] = fragen_status
        frage_form = FrageForm(fragenkatalog=self.object)
        frage_form.fields["themen"].widget.attrs["list"] = "vorhandene-themen"
        context["frage_form"] = frage_form
        context["themen"] = FragenTag.objects.filter(
            organisation=self.object.organisation,
            frage__fragenkatalog=self.object,
        ).distinct().order_by("name")
        context["antwort_form"] = AntwortForm()
        context["zuordnung_form"] = ZuordnungsPaarForm()
        context["csv_form"] = CSVImportForm()
        return context


class TrainerFragenkatalogDeleteView(RollenMixin, DeleteView):
    rolle = Rolle.EXAM_OPERATOR
    model = Fragenkatalog
    template_name = "exams/trainer/catalog_confirm_delete.html"

    def get_queryset(self):
        return trainer_catalog_queryset(self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["fragen_anzahl"] = self.object.fragen.count()
        context["pruefungen_anzahl"] = Pruefung.objects.filter(fragenkatalog=self.object).count()
        return context

    def get_success_url(self):
        return reverse("trainer_catalog_list")

    def form_valid(self, form):
        titel = self.object.titel
        response = super().form_valid(form)
        messages.success(self.request, f"Fragenkatalog „{titel}“ wurde gelöscht.")
        return response


class FrageAktivToggleView(RollenMixin, View):
    rolle = Rolle.EXAM_OPERATOR

    def post(self, request, frage_id):
        frage = get_object_or_404(Frage, pk=frage_id, fragenkatalog__in=trainer_catalog_queryset(request.user))
        frage.aktiv = not frage.aktiv
        frage.save(update_fields=["aktiv"])
        messages.success(request, f"Frage #{frage.pk} ist jetzt {'aktiv' if frage.aktiv else 'inaktiv'}.")
        return redirect(f"{reverse('trainer_catalog_edit', kwargs={'pk': frage.fragenkatalog_id})}?q={request.POST.get('q', '')}&aktiv={request.POST.get('aktiv', 'alle')}")


class TrainerFrageCreateView(RollenMixin, View):
    rolle = Rolle.EXAM_OPERATOR

    def get_katalog(self):
        return get_object_or_404(trainer_catalog_queryset(self.request.user), id=self.kwargs["katalog_id"])

    def get_context(self, katalog, form=None):
        form = form or FrageForm(fragenkatalog=katalog)
        form.fields["themen"].widget.attrs["list"] = "vorhandene-themen"
        return {
            "katalog": katalog,
            "form": form,
            "themen": FragenTag.objects.filter(
                organisation=katalog.organisation,
                frage__fragenkatalog=katalog,
            ).distinct().order_by("name"),
        }

    def get(self, request, *args, **kwargs):
        katalog = self.get_katalog()
        return render(request, "exams/trainer/question_create.html", self.get_context(katalog))

    def _is_correct(self, value):
        return str(value or "").strip().lower() in {"1", "true", "wahr", "richtig", "ja", "yes", "x", "on"}

    def _save_entries(self, frage, post_data):
        if frage.typ in [Frage.Typ.SINGLE_CHOICE, Frage.Typ.MULTIPLE_CHOICE, Frage.Typ.WAHR_FALSCH]:
            for index in range(1, 9):
                antworttext = post_data.get(f"antwort_{index}", "").strip()
                if antworttext:
                    Antwort.objects.create(
                        frage=frage,
                        antworttext=antworttext,
                        ist_korrekt=self._is_correct(post_data.get(f"korrekt_{index}")),
                        reihenfolge=index,
                    )
        elif frage.typ == Frage.Typ.ZUORDNUNG:
            for index in range(1, 6):
                links = post_data.get(f"links_{index}", "").strip()
                rechts = post_data.get(f"rechts_{index}", "").strip()
                if links and rechts:
                    ZuordnungsPaar.objects.create(
                        frage=frage,
                        linkes_element=links,
                        rechtes_element=rechts,
                        reihenfolge=index,
                    )

    def post(self, request, katalog_id):
        katalog = self.get_katalog()
        form = FrageForm(request.POST, fragenkatalog=katalog)
        if form.is_valid():
            frage = form.save(commit=False)
            frage.fragenkatalog = katalog
            frage.save()
            form.save_m2m()
            form.save_themen(frage)
            self._save_entries(frage, request.POST)
            messages.success(request, "Frage wurde mit Antworten erstellt.")
            if "weitere_frage" in request.POST:
                return redirect("trainer_question_create", katalog_id=katalog.pk)
            return redirect("trainer_catalog_edit", pk=katalog.pk)
        else:
            messages.error(request, "Frage konnte nicht erstellt werden.")
            return render(request, "exams/trainer/question_create.html", self.get_context(katalog, form))


class TrainerAntwortCreateView(RollenMixin, View):
    rolle = Rolle.EXAM_OPERATOR

    def post(self, request, frage_id):
        frage = get_object_or_404(Frage, id=frage_id, fragenkatalog__in=trainer_catalog_queryset(request.user))
        form_class = ZuordnungsPaarForm if frage.typ == Frage.Typ.ZUORDNUNG else AntwortForm
        form = form_class(request.POST)
        if form.is_valid():
            objekt = form.save(commit=False)
            objekt.frage = frage
            objekt.save()
            messages.success(request, "Eintrag wurde erstellt.")
        else:
            messages.error(request, "Eintrag konnte nicht erstellt werden.")
        return redirect("trainer_catalog_edit", pk=frage.fragenkatalog_id)


class TrainerCSVImportView(RollenMixin, View):
    rolle = Rolle.EXAM_OPERATOR

    def post(self, request, katalog_id):
        katalog = get_object_or_404(trainer_catalog_queryset(request.user), id=katalog_id)
        form = CSVImportForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                with transaction.atomic():
                    erstellt = form.importiere(katalog)
            except (ValidationError, ValueError) as exc:
                messages.error(request, f"CSV-Datei konnte nicht importiert werden: {exc}")
            else:
                messages.success(request, f"{erstellt} Fragen mit Antworten wurden importiert.")
        else:
            messages.error(request, "CSV-Datei konnte nicht importiert werden.")
        return redirect("trainer_catalog_edit", pk=katalog.pk)


class TrainerPruefungListView(TrainerOderOperatorMixin, ListView):
    template_name = "exams/trainer/exam_list.html"
    context_object_name = "pruefungen"

    def get_queryset(self):
        return trainer_exam_queryset(self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["ist_exam_operator"] = self.request.user.is_superuser or self.request.user.profile.filter(rolle=Rolle.EXAM_OPERATOR, aktiv=True).exists()
        return context


class TrainerPruefungsFreigabeView(TrainerOderOperatorMixin, View):
    template_name = "exams/trainer/exam_approvals.html"

    def get_pruefung(self):
        return get_object_or_404(trainer_exam_queryset(self.request.user), pk=self.kwargs["pk"])

    def get(self, request, pk):
        pruefung = self.get_pruefung()
        return render(request, self.template_name, {
            "pruefung": pruefung,
            "form": PruefungsFreigabeForm(pruefung=pruefung),
            "freigaben": pruefung.freigaben.select_related("nutzer", "freigegeben_von"),
        })

    def post(self, request, pk):
        pruefung = self.get_pruefung()
        if request.POST.get("aktion") == "widerrufen":
            freigabe = get_object_or_404(PruefungsFreigabe, pk=request.POST.get("freigabe_id"), pruefung=pruefung)
            freigabe.widerrufen_am = timezone.now()
            freigabe.save(update_fields=["widerrufen_am"])
            messages.success(request, "Pruefungsfreigabe wurde widerrufen.")
            return redirect("trainer_exam_approvals", pk=pruefung.pk)
        form = PruefungsFreigabeForm(request.POST, pruefung=pruefung)
        if form.is_valid():
            _, erstellt = PruefungsFreigabe.objects.update_or_create(
                pruefung=pruefung,
                nutzer=form.cleaned_data["nutzer"],
                defaults={"freigegeben_von": request.user, "widerrufen_am": None},
            )
            messages.success(request, "Pruefung wurde fuer den Teilnehmer freigegeben." if erstellt else "Pruefungsfreigabe wurde erneut aktiviert.")
            return redirect("trainer_exam_approvals", pk=pruefung.pk)
        return render(request, self.template_name, {
            "pruefung": pruefung,
            "form": form,
            "freigaben": pruefung.freigaben.select_related("nutzer", "freigegeben_von"),
        })


class TrainerKatalogThemenView(RollenMixin, View):
    rolle = Rolle.EXAM_OPERATOR

    def get(self, request, pk):
        katalog = get_object_or_404(trainer_catalog_queryset(request.user), pk=pk)
        themen = FragenTag.objects.filter(
            organisation=katalog.organisation,
            frage__fragenkatalog=katalog,
        ).distinct().order_by("name")
        return JsonResponse({"themen": [{"id": thema.pk, "name": thema.name} for thema in themen]})


class TrainerPruefungFormMixin:
    themen_formset_class = PruefungsThemenquoteFormSet

    def get_themen_formset(self, data=None):
        return self.themen_formset_class(
            data=data,
            instance=self.object or Pruefung(),
            form_kwargs={"pruefung": self.object},
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["themen_formset"] = kwargs.get("themen_formset") or self.get_themen_formset()
        if self.object and self.object.pk:
            context["offline_boegen"] = self.object.offline_boegen.all()[:12]
        return context

    def form_valid(self, form):
        self.object = form.save(commit=False)
        themen_formset = self.get_themen_formset(data=self.request.POST)
        if not themen_formset.is_valid():
            return self.render_to_response(self.get_context_data(form=form, themen_formset=themen_formset))
        with transaction.atomic():
            self.object.save()
            form.save_m2m()
            themen_formset.instance = self.object
            themen_formset.save()
        return redirect(self.get_success_url())

    def form_invalid(self, form):
        return self.render_to_response(
            self.get_context_data(form=form, themen_formset=self.get_themen_formset(data=self.request.POST))
        )


class TrainerPruefungCreateView(TrainerPruefungFormMixin, RollenMixin, CreateView):
    rolle = Rolle.EXAM_OPERATOR
    form_class = PruefungForm
    template_name = "exams/trainer/exam_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        organisation = form.cleaned_data.get("organisation")
        if organisation and organisation.ist_demo_organisation:
            from apps.courses.models import Kurs
            if Pruefung.objects.filter(organisation=organisation).count() + Kurs.objects.filter(organisation=organisation).count() >= organisation.demo_inhalte_startbestand + 3:
                form.add_error(None, "In der Demo-Organisation koennen zusaetzlich hoechstens drei Kurse oder Zertifikatspruefungen angelegt werden.")
                return self.form_invalid(form)
        return super().form_valid(form)

    def get_success_url(self):
        messages.success(self.request, "Pruefung wurde gespeichert.")
        return reverse("trainer_exam_edit", kwargs={"pk": self.object.pk})


class TrainerPruefungUpdateView(TrainerPruefungFormMixin, RollenMixin, UpdateView):
    rolle = Rolle.EXAM_OPERATOR
    form_class = PruefungForm
    template_name = "exams/trainer/exam_form.html"

    def get_queryset(self):
        return trainer_exam_queryset(self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_success_url(self):
        messages.success(self.request, "Pruefung wurde gespeichert.")
        return reverse("trainer_exam_list")


class TrainerPruefungsbogenPDFView(TrainerOderOperatorMixin, View):

    def get(self, request, pk, variante):
        pruefung = get_object_or_404(trainer_exam_queryset(request.user), pk=pk)
        try:
            fragen = waehle_pruefungsfragen(pruefung)
        except NichtGenugFragenInThema as exc:
            messages.error(request, f"Prüfungsbogen konnte nicht erzeugt werden: {exc}")
            return redirect("trainer_exam_edit", pk=pruefung.pk)
        mit_loesungen = variante == "trainer"
        pdf_bytes = generiere_pruefungsbogen_pdf(pruefung, fragen, mit_loesungen=mit_loesungen)
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        name = "trainer-loesungen" if mit_loesungen else "teilnehmer"
        response["Content-Disposition"] = f'attachment; filename="pruefungsbogen-{pruefung.pk}-{name}.pdf"'
        return response


class TrainerOfflinePruefungsbogenCreateView(TrainerOderOperatorMixin, View):

    def post(self, request, pk):
        pruefung = get_object_or_404(trainer_exam_queryset(request.user), pk=pk)
        try:
            fragen = waehle_pruefungsfragen(pruefung)
        except NichtGenugFragenInThema as exc:
            messages.error(request, f"Offline-Pruefungsbogen konnte nicht erzeugt werden: {exc}")
            return redirect("trainer_exam_edit", pk=pruefung.pk)
        if not pruefung.zufaellige_fragenreihenfolge:
            fragen.sort(key=lambda frage: frage.id)
        archiv = PruefungsbogenArchiv.objects.create(
            pruefung=pruefung,
            erstellt_von=request.user,
            fragen_reihenfolge=[frage.pk for frage in fragen],
        )
        stamp = timezone.localtime(archiv.erstellt_am).strftime("%Y%m%d-%H%M%S")
        archiv.teilnehmer_pdf.save(
            f"pruefungsbogen-{pruefung.pk}-{stamp}-teilnehmer.pdf",
            ContentFile(generiere_pruefungsbogen_pdf(pruefung, fragen, mit_loesungen=False)),
            save=False,
        )
        archiv.loesung_pdf.save(
            f"pruefungsbogen-{pruefung.pk}-{stamp}-loesungen.pdf",
            ContentFile(generiere_pruefungsbogen_pdf(pruefung, fragen, mit_loesungen=True)),
            save=False,
        )
        archiv.save()
        messages.success(request, "Offline-Pruefungsbogen und Trainer-Lösung wurden im Archiv gespeichert.")
        return redirect("trainer_exam_edit", pk=pruefung.pk)


class TrainerOfflinePruefungsbogenDownloadView(TrainerOderOperatorMixin, View):

    def get(self, request, pk, archiv_id, variante):
        pruefung = get_object_or_404(trainer_exam_queryset(request.user), pk=pk)
        archiv = get_object_or_404(PruefungsbogenArchiv, pk=archiv_id, pruefung=pruefung)
        datei = archiv.loesung_pdf if variante == "loesung" else archiv.teilnehmer_pdf
        return FileResponse(datei.open("rb"), as_attachment=True, filename=datei.name.rsplit("/", 1)[-1])


class PruefungDetailView(LoginRequiredMixin, DetailView):
    model = Pruefung
    template_name = "exams/detail.html"
    context_object_name = "pruefung"

    def get_queryset(self):
        queryset = Pruefung.objects.filter(ist_aktiv=True, organisation__aktiv=True)
        if getattr(self.request, "tenant_org", None) and not self.request.user.is_superuser:
            queryset = queryset.filter(organisation=self.request.tenant_org)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["angemeldet"] = PruefungsAnmeldung.objects.filter(nutzer=self.request.user, pruefung=self.object).exists()
        return context


class PruefungEinschreibenView(LoginRequiredMixin, View):
    def post(self, request, pk):
        queryset = Pruefung.objects.filter(pk=pk, ist_aktiv=True, organisation__aktiv=True)
        if getattr(request, "tenant_org", None) and not request.user.is_superuser:
            queryset = queryset.filter(organisation=request.tenant_org)
        pruefung = get_object_or_404(queryset)
        PruefungsAnmeldung.objects.get_or_create(nutzer=request.user, pruefung=pruefung)
        messages.success(request, "Sie sind zur Prüfung angemeldet.")
        return redirect("exam_detail", pk=pruefung.pk)


class PruefungStartView(LoginRequiredMixin, View):
    def post(self, request, pk):
        queryset = Pruefung.objects.filter(pk=pk, ist_aktiv=True, organisation__aktiv=True)
        if getattr(request, "tenant_org", None) and not request.user.is_superuser:
            queryset = queryset.filter(organisation=request.tenant_org)
        pruefung = get_object_or_404(queryset)
        if not all([request.user.first_name, request.user.last_name, request.user.geburtsdatum, request.user.geburtsort]):
            messages.error(request, "Bitte vervollständigen Sie zuerst Vorname, Nachname, Geburtsdatum und Geburtsort im Profil.")
            return redirect("profile")
        if not PruefungsAnmeldung.objects.filter(nutzer=request.user, pruefung=pruefung).exists():
            messages.error(request, "Bitte melden Sie sich zuerst zur Prüfung an.")
            return redirect("exam_detail", pk=pruefung.pk)
        laufender_versuch = PruefungsVersuch.objects.filter(
            nutzer=request.user, pruefung=pruefung, status=PruefungsVersuch.Status.LAUFEND
        ).first()
        if laufender_versuch:
            return redirect("exam_take", pk=pruefung.pk, versuch_id=laufender_versuch.pk)
        if not PruefungsFreigabe.objects.filter(
            nutzer=request.user, pruefung=pruefung, widerrufen_am__isnull=True
        ).exists():
            messages.error(request, "Diese Zertifikatspruefung wurde noch nicht durch einen Trainer freigegeben.")
            return redirect("exam_detail", pk=pruefung.pk)
        try:
            versuch = starte_pruefung(pruefung, request.user)
        except MaxVersucheErreicht:
            messages.error(request, "Maximale Anzahl an Versuchen erreicht.")
            return redirect("exam_detail", pk=pruefung.pk)
        except NichtGenugFragenInThema as exc:
            messages.error(request, f"Prüfung kann nicht gestartet werden: {exc}")
            return redirect("exam_detail", pk=pruefung.pk)
        messages.success(request, "Pruefung wurde gestartet.")
        return redirect("exam_take", pk=pruefung.pk, versuch_id=versuch.pk)


class PruefungAblegenView(LoginRequiredMixin, TemplateView):
    template_name = "exams/take.html"

    def dispatch(self, request, *args, **kwargs):
        queryset = Pruefung.objects.filter(pk=kwargs["pk"], ist_aktiv=True)
        if getattr(request, "tenant_org", None) and not request.user.is_superuser:
            queryset = queryset.filter(organisation=request.tenant_org)
        self.pruefung = get_object_or_404(queryset)
        self.versuch = get_object_or_404(PruefungsVersuch, pk=kwargs["versuch_id"], pruefung=self.pruefung, nutzer=request.user)
        if self.versuch.aktive_phase_begonnen_am and self.versuch.letzte_aktivitaet_am and (timezone.now() - self.versuch.letzte_aktivitaet_am).total_seconds() > 15:
            pausiere_pruefung(self.versuch)
            self.versuch.refresh_from_db()
        if pruefe_zeitlimit(self.versuch):
            messages.error(request, "Das Zeitlimit wurde ueberschritten.")
            return redirect("exam_result", pk=self.pruefung.pk, versuch_id=self.versuch.pk)
        if self.versuch.status != PruefungsVersuch.Status.LAUFEND:
            return redirect("exam_result", pk=self.pruefung.pk, versuch_id=self.versuch.pk)
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        index = self.get_index(request.POST)
        frage = self.get_frage(index)
        if not frage:
            return redirect("exam_result", pk=self.pruefung.pk, versuch_id=self.versuch.pk)
        try:
            speichere_antwort(self.versuch, frage, request.POST)
        except ValidationError:
            return HttpResponseBadRequest("Die Antwort konnte nicht gespeichert werden. Bitte prüfen Sie Ihre Eingabe.")
        if "finish" in request.POST:
            werte_versuch_aus(self.versuch)
            messages.success(request, "Pruefung wurde abgegeben.")
            return redirect("exam_result", pk=self.pruefung.pk, versuch_id=self.versuch.pk)
        if request.POST.get("direction") == "previous":
            if index == 0:
                return redirect(f"{request.path}?uebersicht=1")
            return redirect(f"{request.path}?index={index - 1}")
        naechster_index = min(index + 1, len(self.versuch.fragen_reihenfolge) - 1)
        return redirect(f"{request.path}?index={naechster_index}")

    def get_index(self, data):
        try:
            index = int(data.get("index", 0))
        except (TypeError, ValueError):
            raise Http404("Ungültige Fragenposition.")
        if not 0 <= index < len(self.versuch.fragen_reihenfolge):
            raise Http404("Ungültige Fragenposition.")
        return index

    def get_frage(self, index):
        if index < 0 or index >= len(self.versuch.fragen_reihenfolge):
            return None
        return get_object_or_404(Frage.objects.prefetch_related("antworten", "zuordnungen", "teilfragen"), id=self.versuch.fragen_reihenfolge[index])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.GET.get("uebersicht") == "1":
            context.update({
                "pruefung": self.pruefung,
                "versuch": self.versuch,
                "uebersicht": True,
                "fragenpositionen": range(len(self.versuch.fragen_reihenfolge)),
            })
            return context
        index = self.get_index(self.request.GET)
        frage = self.get_frage(index)
        bestehende_antwort = TeilnehmerAntwort.objects.filter(versuch=self.versuch, frage=frage).first() if frage else None
        antworten = list(frage.antworten.all()) if frage else []
        if self.pruefung.zufaellige_antwortfolge:
            import random

            # Reproducible per attempt/question, including after a browser restart.
            seed = salted_hmac("exam-answer-order", f"{self.versuch.pk}:{frage.pk}").hexdigest()
            random.Random(seed).shuffle(antworten)
        context.update(
            {
                "pruefung": self.pruefung,
                "versuch": self.versuch,
                "frage": frage,
                "antworten": antworten,
                "bestehende_antwort": bestehende_antwort,
                "ausgewaehlte_antwort_ids": set(bestehende_antwort.ausgewaehlte_antworten.values_list("pk", flat=True)) if bestehende_antwort else set(),
                "index": index,
                "gesamt": len(self.versuch.fragen_reihenfolge),
                "is_last": index + 1 >= len(self.versuch.fragen_reihenfolge),
                "zuordnung_json": json.dumps(bestehende_antwort.zuordnung_json if bestehende_antwort else {}),
                "zeitlimit_sekunden": self.pruefung.zeitlimit_minuten * 60 if self.pruefung.zeitlimit_minuten else 0,
                "aktive_sekunden": min(aktive_sekunden(self.versuch), self.pruefung.zeitlimit_minuten * 60) if self.pruefung.zeitlimit_minuten else 0,
                "restliche_sekunden": restliche_sekunden(self.versuch) or 0,
                "ist_pausiert": not self.versuch.aktive_phase_begonnen_am,
            }
        )
        return context


class PruefungFortsetzenView(LoginRequiredMixin, View):
    def post(self, request, pk, versuch_id):
        versuch = get_object_or_404(PruefungsVersuch.objects.select_related("pruefung"), pk=versuch_id, pruefung_id=pk, nutzer=request.user)
        if pruefe_zeitlimit(versuch) or versuch.status != PruefungsVersuch.Status.LAUFEND:
            return JsonResponse({"ok": False, "error": "Prüfung nicht fortsetzbar."}, status=409)
        setze_pruefung_fort(versuch)
        return JsonResponse({"ok": True})


class PruefungPausierenView(LoginRequiredMixin, View):
    def post(self, request, pk, versuch_id):
        versuch = get_object_or_404(PruefungsVersuch.objects.select_related("pruefung"), pk=versuch_id, pruefung_id=pk, nutzer=request.user)
        pausiere_pruefung(versuch)
        return JsonResponse({"ok": True})


class PruefungAutosaveView(LoginRequiredMixin, View):
    def post(self, request, pk, versuch_id):
        versuch = get_object_or_404(PruefungsVersuch, pk=versuch_id, pruefung_id=pk, nutzer=request.user)
        try:
            payload = json.loads(request.body.decode("utf-8") or "{}")
            if payload.get("heartbeat"):
                bestaetige_aktivitaet(versuch)
                return JsonResponse({"ok": True, "restliche_sekunden": restliche_sekunden(versuch)})
            frage = self._frage(versuch, int(payload["frage_id"]))
            from django.http import QueryDict
            daten = QueryDict(mutable=True)
            for key, value in payload.items():
                if key == "antworten":
                    daten.setlist(key, [str(v) for v in value])
                elif key != "frage_id":
                    daten[key] = value
            speichere_antwort(versuch, frage, daten)
            bestaetige_aktivitaet(versuch)
        except (KeyError, TypeError, ValueError, ValidationError):
            return JsonResponse({"ok": False, "error": "Ungültige Antwort."}, status=400)
        return JsonResponse({"ok": True})

    @staticmethod
    def _frage(versuch, frage_id):
        if frage_id not in versuch.fragen_reihenfolge:
            raise ValidationError("Frage gehört nicht zu diesem Versuch.")
        return get_object_or_404(Frage, pk=frage_id)


class PruefungErgebnisView(LoginRequiredMixin, DetailView):
    model = PruefungsVersuch
    template_name = "exams/result.html"
    context_object_name = "versuch"
    pk_url_kwarg = "versuch_id"

    def get_queryset(self):
        queryset = PruefungsVersuch.objects.filter(nutzer=self.request.user, einsehbar_bis__gte=timezone.now()).select_related("pruefung")
        if getattr(self.request, "tenant_org", None) and not self.request.user.is_superuser:
            queryset = queryset.filter(pruefung__organisation=self.request.tenant_org)
        return queryset


class PruefungErgebnisListeView(LoginRequiredMixin, ListView):
    template_name = "exams/result_list.html"
    context_object_name = "versuche"

    def get_queryset(self):
        queryset = PruefungsVersuch.objects.filter(
            nutzer=self.request.user,
            status__in=[PruefungsVersuch.Status.ABGESCHLOSSEN, PruefungsVersuch.Status.AUSSTEHEND, PruefungsVersuch.Status.ABGELAUFEN],
        ).filter(einsehbar_bis__gte=timezone.now()).select_related("pruefung")
        if getattr(self.request, "tenant_org", None) and not self.request.user.is_superuser:
            queryset = queryset.filter(pruefung__organisation=self.request.tenant_org)
        return queryset


class ExaminerQueueView(RollenMixin, ListView):
    rolle = Rolle.EXAMINER
    template_name = "exams/examiner/queue.html"
    context_object_name = "antworten"

    def get_queryset(self):
        queryset = TeilnehmerAntwort.objects.filter(
            frage__typ__in=[Frage.Typ.FREITEXT, Frage.Typ.SZENARIO],
            freitext_punkte__isnull=True,
            versuch__status=PruefungsVersuch.Status.AUSSTEHEND,
        ).select_related("versuch", "versuch__pruefung", "frage", "versuch__nutzer")
        if self.request.user.is_superuser:
            return queryset
        organisation_ids = self.request.user.profile.filter(aktiv=True).values_list("organisation_id", flat=True)
        return queryset.filter(versuch__pruefung__organisation_id__in=organisation_ids)


class ExaminerBewertungView(RollenMixin, UpdateView):
    rolle = Rolle.EXAMINER
    form_class = FreitextBewertungForm
    template_name = "exams/examiner/review.html"
    context_object_name = "antwort"

    def get_queryset(self):
        return ExaminerQueueView().get_queryset()

    def get_object(self, queryset=None):
        queryset = TeilnehmerAntwort.objects.filter(frage__typ__in=[Frage.Typ.FREITEXT, Frage.Typ.SZENARIO]).select_related("versuch", "frage", "versuch__nutzer")
        if not self.request.user.is_superuser:
            organisation_ids = self.request.user.profile.filter(aktiv=True).values_list("organisation_id", flat=True)
            queryset = queryset.filter(versuch__pruefung__organisation_id__in=organisation_ids)
        return get_object_or_404(queryset, pk=self.kwargs["pk"])

    def form_valid(self, form):
        form.instance.freitext_bewertet_von = self.request.user
        form.instance.freitext_bewertet_am = timezone.now()
        response = super().form_valid(form)
        werte_versuch_aus(self.object.versuch)
        messages.success(self.request, "Freitext wurde bewertet.")
        return response

    def get_success_url(self):
        return reverse("examiner_queue")


class TrainerPruefungStatistikView(TrainerOderOperatorMixin, TemplateView):
    template_name = "exams/trainer/exam_stats.html"

    def dispatch(self, request, *args, **kwargs):
        self.pruefung = get_object_or_404(trainer_exam_queryset(request.user), pk=kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        versuche = PruefungsVersuch.objects.filter(pruefung=self.pruefung)
        abgeschlossen = versuche.filter(status=PruefungsVersuch.Status.ABGESCHLOSSEN)
        total = versuche.count()
        bestanden = versuche.filter(bestanden=True).count()
        frage_stats = (
            TeilnehmerAntwort.objects.filter(versuch__pruefung=self.pruefung)
            .values("frage_id", "frage__typ")
            .annotate(antworten=Count("id"), punkte_avg=Avg("punkte_vergeben"))
            .order_by("frage_id")
        )
        context.update({
            "pruefung": self.pruefung,
            "versuche_count": total,
            "abgeschlossen_count": abgeschlossen.count(),
            "bestanden_count": bestanden,
            "bestehensquote": round((bestanden / total) * 100) if total else 0,
            "durchschnitt": versuche.aggregate(avg=Avg("prozent_erreicht"))["avg"] or 0,
            "frage_stats": frage_stats,
        })
        return context


class TrainerPruefungErgebnisListeView(TrainerOderOperatorMixin, ListView):
    template_name = "exams/trainer/exam_results.html"
    context_object_name = "versuche"

    def dispatch(self, request, *args, **kwargs):
        self.pruefung = get_object_or_404(trainer_exam_queryset(request.user), pk=kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return PruefungsVersuch.objects.filter(pruefung=self.pruefung).select_related("nutzer").order_by("-gestartet_am")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["pruefung"] = self.pruefung
        return context
