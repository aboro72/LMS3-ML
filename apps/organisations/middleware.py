from urllib.parse import urlparse

from django.shortcuts import redirect
from django.urls import reverse

from .models import Organisation


class TenantRedirectMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.tenant_org = self._active_organisation(request)
        response = self._redirect_from_configured_url(request)
        if response is not None:
            return response
        return self.get_response(request)

    def _active_organisation(self, request):
        organisation_id = request.session.get("active_organisation_id")
        if organisation_id:
            org = Organisation.objects.filter(pk=organisation_id, aktiv=True).first()
            if org:
                return org
        first_segment = request.path.strip("/").split("/", 1)[0]
        reserved = {"accounts", "kurse", "pruefungen", "lernpfade", "dashboard", "organisationen", "trainer", "examiner", "admin"}
        if first_segment in reserved:
            return None
        return Organisation.objects.filter(slug=first_segment, aktiv=True).first()

    def _redirect_from_configured_url(self, request):
        host = request.get_host().split(":", 1)[0].lower()
        path = request.path.rstrip("/") or "/"
        for org in Organisation.objects.filter(aktiv=True).exclude(weiterleitungs_url=""):
            parsed = urlparse(org.weiterleitungs_url)
            configured_host = (parsed.netloc or parsed.path).split("/", 1)[0].split(":", 1)[0].lower()
            configured_path = parsed.path.rstrip("/") or "/"
            if not configured_host or host != configured_host:
                continue
            if configured_path != "/" and path != configured_path:
                continue
            target = reverse("org_public_home", kwargs={"slug": org.slug})
            if path == target.rstrip("/"):
                return None
            if request.GET:
                target = f"{target}?{request.GET.urlencode()}"
            return redirect(target, permanent=False)
        return None
