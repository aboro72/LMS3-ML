from django.conf import settings
from functools import wraps

from .models import Organisation


def system_organisation():
    """Return the configured organisation used by single-system mode."""
    slug = getattr(settings, "SINGLE_SYSTEM_ORGANISATION_SLUG", "ml-gruppe")
    organisation, _ = Organisation.objects.get_or_create(
        slug=slug,
        defaults={
            "name": getattr(settings, "SINGLE_SYSTEM_BRAND_NAME", "ML Gruppe"),
            "kontakt_email": getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@example.com"),
        },
    )
    return organisation


def bind_system_form(form):
    """Bind organisation fields to the configured organisation in single-system mode."""
    if not getattr(settings, "SINGLE_SYSTEM_MODE", False):
        return form
    field = form.fields.get("organisation")
    if field is None:
        return form
    organisation = system_organisation()
    field.queryset = Organisation.objects.filter(pk=organisation.pk)
    field.initial = organisation.pk
    field.disabled = True
    return form


def system_view(view):
    """Expose organisation-scoped views through the central single-system URLs."""
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        kwargs.setdefault("slug", system_organisation().slug)
        return view(request, *args, **kwargs)

    return wrapped
