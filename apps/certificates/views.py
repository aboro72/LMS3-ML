from django.conf import settings
from django.contrib import messages
from django.http import Http404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import DetailView, ListView

from apps.accounts.mixins import RollenMixin
from apps.accounts.models import Rolle
from apps.organisations.models import Organisation

from .forms import ZertifikatDesignForm
from .models import Zertifikat, ZertifikatDesign
from .services import generiere_zertifikat_pdf


class ZertifikatListeView(LoginRequiredMixin, ListView):
    template_name = "certificates/list.html"
    context_object_name = "zertifikate"

    def get_queryset(self):
        return Zertifikat.objects.filter(
            nutzer=self.request.user,
            ist_widerrufen=False,
        ).select_related(
            "pruefungsversuch__pruefung__organisation",
            "einschreibung__kurs",
        )


class ZertifikatVerifyView(DetailView):
    model = Zertifikat
    template_name = "certificates/verify.html"
    context_object_name = "zertifikat"
    slug_field = "code"
    slug_url_kwarg = "code"


class ZertifikatDownloadView(LoginRequiredMixin, View):
    def get(self, request, code):
        zert = get_object_or_404(
            Zertifikat,
            code=code,
            nutzer=request.user,
            ist_widerrufen=False,
        )
        base_url = request.build_absolute_uri("/")
        if not zert.pdf_datei:
            pdf_bytes = generiere_zertifikat_pdf(zert, base_url)
            from django.core.files.base import ContentFile
            zert.pdf_datei.save(f"zertifikat-{zert.zertifikatsnummer or zert.code}.pdf", ContentFile(pdf_bytes), save=True)
        response = HttpResponse(zert.pdf_datei.open("rb"), content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="zertifikat-{zert.zertifikatsnummer or zert.code}.pdf"'
        return response


class ZertifikatDesignView(RollenMixin, View):
    rolle = Rolle.ORG_ADMIN

    def _get_org(self, slug):
        if settings.SINGLE_SYSTEM_MODE and self.request.path.startswith("/organisationen/"):
            raise Http404("Organisationsbezogenes Zertifikat-Design ist im Einzelsystem deaktiviert.")
        if self.request.user.is_superuser:
            return get_object_or_404(Organisation, slug=slug)
        org_ids = self.request.user.profile.filter(
            rolle=Rolle.ORG_ADMIN, aktiv=True
        ).values_list("organisation_id", flat=True)
        return get_object_or_404(Organisation, slug=slug, id__in=org_ids)

    def get(self, request, slug):
        org = self._get_org(slug)
        design, _ = ZertifikatDesign.objects.get_or_create(organisation=org)
        form = ZertifikatDesignForm(instance=design)
        return render(request, "certificates/design_form.html", {"form": form, "org": org, "design": design})

    def post(self, request, slug):
        org = self._get_org(slug)
        design, _ = ZertifikatDesign.objects.get_or_create(organisation=org)
        form = ZertifikatDesignForm(request.POST, request.FILES, instance=design)
        if form.is_valid():
            form.save()
            messages.success(request, "Zertifikat-Design wurde gespeichert.")
            return redirect("org_cert_design", slug=slug)
        return render(request, "certificates/design_form.html", {"form": form, "org": org, "design": design})
