from django.conf import settings

from .single_system import system_organisation


class SingleSystemAdminMixin:
    """Apply the configured organisation boundary to Django admin models."""

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if not getattr(settings, "SINGLE_SYSTEM_MODE", False):
            return queryset
        model = queryset.model
        field = getattr(model, "_meta", None) and model._meta.get_field("organisation") if hasattr(model, "_meta") else None
        if field is not None:
            return queryset.filter(organisation=system_organisation())
        return queryset

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if (
            getattr(settings, "SINGLE_SYSTEM_MODE", False)
            and db_field.name == "organisation"
        ):
            kwargs["queryset"] = db_field.remote_field.model.objects.filter(pk=system_organisation().pk)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        if getattr(settings, "SINGLE_SYSTEM_MODE", False) and hasattr(obj, "organisation_id"):
            obj.organisation = system_organisation()
        super().save_model(request, obj, form, change)
