from apps.organisations.single_system_admin import SingleSystemAdminMixin
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group

from .models import Rolle, User, UserProfile


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("ABoroLMS", {"fields": ("avatar", "bio", "bevorzugte_sprache")}),
    )
    list_display = ("username", "email", "first_name", "last_name", "is_staff", "erstellt_am")
    search_fields = ("username", "email", "first_name", "last_name")


@admin.register(UserProfile)
class UserProfileAdmin(SingleSystemAdminMixin, admin.ModelAdmin):
    list_display = ("nutzer", "organisation", "rolle", "aktiv", "eingeladen_am")
    list_filter = ("rolle", "aktiv", "organisation")
    search_fields = ("nutzer__username", "nutzer__email", "organisation__name")
    autocomplete_fields = ("nutzer", "organisation")


def ensure_default_groups():
    for role in Rolle:
        Group.objects.get_or_create(name=role.value)
