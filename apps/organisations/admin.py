from apps.organisations.single_system_admin import SingleSystemAdminMixin
from django.contrib import admin

from .models import (
    Einladung,
    Organisation,
    OrganisationDesign,
    OrganisationEmailKonfiguration,
    OrganisationStartseite,
)


@admin.register(Organisation)
class OrganisationAdmin(SingleSystemAdminMixin, admin.ModelAdmin):
    def has_add_permission(self, request):
        from django.conf import settings
        return not settings.SINGLE_SYSTEM_MODE and super().has_add_permission(request)

    def has_delete_permission(self, request, obj=None):
        from django.conf import settings
        return not settings.SINGLE_SYSTEM_MODE and super().has_delete_permission(request, obj)

    def has_module_permission(self, request):
        from django.conf import settings
        return not settings.SINGLE_SYSTEM_MODE and super().has_module_permission(request)
    list_display = ("name", "slug", "ist_demo_organisation", "lizenz_typ", "max_nutzer", "max_kurse", "aktiv", "erstellt_am")
    fields = ("name", "slug", "kontakt_email", "website", "weiterleitungs_url", "ist_demo_organisation", "lizenz_typ", "max_nutzer", "max_kurse", "aktiv")
    list_filter = ("lizenz_typ", "aktiv")
    search_fields = ("name", "slug", "kontakt_email", "weiterleitungs_url")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Einladung)
class EinladungAdmin(SingleSystemAdminMixin, admin.ModelAdmin):
    list_display = ("email", "organisation", "rolle", "erstellt_am", "akzeptiert_am", "abgelaufen_am")
    list_filter = ("rolle", "organisation", "akzeptiert_am")
    search_fields = ("email", "organisation__name")
    readonly_fields = ("token", "erstellt_am")


@admin.register(OrganisationEmailKonfiguration)
class OrganisationEmailKonfigAdmin(SingleSystemAdminMixin, admin.ModelAdmin):
    list_display = ("organisation", "absender_email", "smtp_host", "smtp_port", "aktiv")
    list_filter = ("aktiv", "smtp_use_tls", "smtp_use_ssl")
    search_fields = ("organisation__name", "absender_email", "smtp_host")


@admin.register(OrganisationDesign)
class OrganisationDesignAdmin(SingleSystemAdminMixin, admin.ModelAdmin):
    list_display = ("organisation", "primary_color", "secondary_color", "navbar_farbe")
    search_fields = ("organisation__name",)


@admin.register(OrganisationStartseite)
class OrganisationStartseiteAdmin(SingleSystemAdminMixin, admin.ModelAdmin):
    list_display = ("organisation", "hero_titel", "aktiv")
    list_filter = ("aktiv",)
    search_fields = ("organisation__name", "hero_titel")
