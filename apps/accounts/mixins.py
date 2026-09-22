from django.contrib.auth.mixins import LoginRequiredMixin
from django.conf import settings
from django.core.exceptions import PermissionDenied

from .models import Rolle


class RollenMixin(LoginRequiredMixin):
    rolle = None

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if self.rolle is None:
            return super().dispatch(request, *args, **kwargs)
        if request.user.is_superuser or request.user.groups.filter(name=Rolle.SUPERADMIN).exists():
            return super().dispatch(request, *args, **kwargs)
        if getattr(settings, "SINGLE_SYSTEM_MODE", False) and self.rolle == Rolle.ORG_ADMIN:
            raise PermissionDenied
        if request.user.profile.filter(rolle=self.rolle, aktiv=True).exists():
            return super().dispatch(request, *args, **kwargs)
        raise PermissionDenied


class OperatorMixin(RollenMixin):
    """Access guard for configuration of formal certification exams."""

    rolle = Rolle.EXAM_OPERATOR


class OrganisationMixin(LoginRequiredMixin):
    organisation_field = "organisation"

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.is_superuser:
            return queryset
        organisation_ids = self.request.user.profile.filter(aktiv=True).values_list(
            "organisation_id",
            flat=True,
        )
        return queryset.filter(**{f"{self.organisation_field}_id__in": organisation_ids})

    def get_user_organisations(self):
        return self.request.user.profile.filter(aktiv=True).select_related("organisation")
