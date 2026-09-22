from apps.organisations.single_system_admin import SingleSystemAdminMixin
from django.contrib import admin

from .models import Antwort, Frage, Fragenkatalog, FragenTag, Pruefung, PruefungsThemenquote, PruefungsVersuch, PruefungsbogenArchiv, TeilnehmerAntwort, ZuordnungsPaar


class AntwortInline(admin.TabularInline):
    model = Antwort
    extra = 2


class ZuordnungsPaarInline(admin.TabularInline):
    model = ZuordnungsPaar
    extra = 2


class PruefungsThemenquoteInline(admin.TabularInline):
    model = PruefungsThemenquote
    extra = 1


@admin.register(Fragenkatalog)
class FragenkatalogAdmin(SingleSystemAdminMixin, admin.ModelAdmin):
    list_display = ("titel", "organisation", "erstellt_von", "erstellt_am")
    list_filter = ("organisation",)
    search_fields = ("titel", "beschreibung", "organisation__name")
    autocomplete_fields = ("organisation", "erstellt_von")


@admin.register(FragenTag)
class FragenTagAdmin(SingleSystemAdminMixin, admin.ModelAdmin):
    list_display = ("name", "organisation")
    list_filter = ("organisation",)
    search_fields = ("name",)


@admin.register(Frage)
class FrageAdmin(SingleSystemAdminMixin, admin.ModelAdmin):
    list_display = ("id", "fragenkatalog", "typ", "schwierigkeit", "punkte")
    list_filter = ("typ", "schwierigkeit", "fragenkatalog__organisation")
    search_fields = ("fragetext", "fragenkatalog__titel")
    inlines = (AntwortInline, ZuordnungsPaarInline)


@admin.register(Antwort)
class AntwortAdmin(SingleSystemAdminMixin, admin.ModelAdmin):
    list_display = ("frage", "antworttext", "ist_korrekt", "reihenfolge")
    list_filter = ("ist_korrekt", "frage__typ")
    search_fields = ("antworttext",)


@admin.register(ZuordnungsPaar)
class ZuordnungsPaarAdmin(SingleSystemAdminMixin, admin.ModelAdmin):
    list_display = ("frage", "linkes_element", "rechtes_element", "reihenfolge")
    search_fields = ("linkes_element", "rechtes_element")


@admin.register(Pruefung)
class PruefungAdmin(SingleSystemAdminMixin, admin.ModelAdmin):
    list_display = ("titel", "organisation", "fragenkatalog", "anzahl_fragen", "ist_aktiv")
    list_filter = ("ist_aktiv", "organisation")
    search_fields = ("titel", "beschreibung", "fragenkatalog__titel")
    inlines = (PruefungsThemenquoteInline,)


@admin.register(PruefungsVersuch)
class PruefungsVersuchAdmin(SingleSystemAdminMixin, admin.ModelAdmin):
    list_display = ("nutzer", "pruefung", "versuch_nummer", "status", "prozent_erreicht", "bestanden")
    list_filter = ("status", "bestanden", "pruefung__organisation")
    search_fields = ("nutzer__username", "pruefung__titel")


@admin.register(PruefungsbogenArchiv)
class PruefungsbogenArchivAdmin(SingleSystemAdminMixin, admin.ModelAdmin):
    list_display = ("pruefung", "erstellt_von", "erstellt_am")
    list_filter = ("pruefung__organisation",)


@admin.register(TeilnehmerAntwort)
class TeilnehmerAntwortAdmin(SingleSystemAdminMixin, admin.ModelAdmin):
    list_display = ("versuch", "frage", "ist_korrekt", "punkte_vergeben")
    list_filter = ("ist_korrekt", "frage__typ")
    search_fields = ("versuch__nutzer__username",)
