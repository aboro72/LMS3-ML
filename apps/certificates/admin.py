from apps.organisations.single_system_admin import SingleSystemAdminMixin
from django.contrib import admin

from .models import Zertifikat, ZertifikatDesign


@admin.register(Zertifikat)
class ZertifikatAdmin(SingleSystemAdminMixin, admin.ModelAdmin):
    list_display = ("code", "nutzer", "get_titel", "ausgestellt_am", "ist_widerrufen")
    list_filter = ("ist_widerrufen",)
    search_fields = ("nutzer__username", "nutzer__email")
    readonly_fields = ("code", "ausgestellt_am")
    actions = ["widerrufen"]

    @admin.action(description="Zertifikate widerrufen")
    def widerrufen(self, request, queryset):
        queryset.update(ist_widerrufen=True)


@admin.register(ZertifikatDesign)
class ZertifikatDesignAdmin(SingleSystemAdminMixin, admin.ModelAdmin):
    list_display = ("organisation", "primary_color", "secondary_color")
    search_fields = ("organisation__name",)
