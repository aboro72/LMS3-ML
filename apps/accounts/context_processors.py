from .models import Rolle


def rollen_context(request):
    from django.conf import settings

    system_context = {
        "single_system_mode": getattr(settings, "SINGLE_SYSTEM_MODE", False),
        "system_brand_name": getattr(settings, "SINGLE_SYSTEM_BRAND_NAME", "ML Gruppe"),
        "system_domain": getattr(settings, "SINGLE_SYSTEM_DOMAIN", "ml-gruppe.de"),
        "system_org_slug": getattr(settings, "SINGLE_SYSTEM_ORGANISATION_SLUG", "ml-gruppe"),
        "system_primary_color": getattr(settings, "SINGLE_SYSTEM_PRIMARY_COLOR", "#0c437b"),
        "system_secondary_color": getattr(settings, "SINGLE_SYSTEM_SECONDARY_COLOR", "#2fb2bf"),
        "system_navbar_color": getattr(settings, "SINGLE_SYSTEM_NAVBAR_COLOR", "#2b2e34"),
        "system_background_color": getattr(settings, "SINGLE_SYSTEM_BACKGROUND_COLOR", "#f9f9fb"),
        "system_logo_static": "branding/ml-gruppe-logo-weiss.png",
    }
    if not request.user.is_authenticated:
        return system_context

    active_org = getattr(request, "tenant_org", None)
    profile_qs = request.user.profile.filter(aktiv=True)
    # In single-system mode the configured organisation is the system context,
    # not a tenant boundary.  Roles must therefore be resolved from all active
    # profiles so an operator remains visible even when the profile belongs to
    # an older/demo organisation slug.
    if active_org and not request.user.is_superuser and not system_context["single_system_mode"]:
        profile_qs = profile_qs.filter(organisation=active_org)
    rollen = set(profile_qs.values_list("rolle", flat=True))
    ist_superadmin = request.user.is_superuser or request.user.groups.filter(name=Rolle.SUPERADMIN).exists()
    meine_org = None
    org_design = None

    if active_org and (request.user.is_superuser or profile_qs.exists()):
        meine_org = active_org
    elif Rolle.ORG_ADMIN in rollen:
        profil = (
            request.user.profile
            .filter(rolle=Rolle.ORG_ADMIN, aktiv=True)
            .select_related("organisation")
            .first()
        )
        if profil:
            meine_org = profil.organisation
    elif rollen:
        # Kein Org-Admin – erste aktive Org für Design-Kontext laden
        profil = (
            request.user.profile
            .filter(aktiv=True)
            .select_related("organisation")
            .first()
        )
        if profil:
            meine_org = profil.organisation

    # Superadmins are system-wide and do not necessarily have a UserProfile.
    # Still provide the system organisation for the central administration menu.
    if ist_superadmin and meine_org is None:
        try:
            from apps.organisations.models import Organisation
            meine_org = Organisation.objects.filter(aktiv=True).order_by("pk").first()
        except Exception:
            meine_org = None

    if meine_org is not None:
        try:
            from apps.organisations.models import OrganisationDesign
            org_design = OrganisationDesign.objects.get(organisation=meine_org)
        except Exception:
            org_design = None

    return {
        **system_context,
        "ist_superadmin": ist_superadmin,
        "ist_trainer": Rolle.TRAINER in rollen,
        "ist_exam_operator": Rolle.EXAM_OPERATOR in rollen,
        "ist_examiner": Rolle.EXAMINER in rollen,
        "ist_org_admin": Rolle.ORG_ADMIN in rollen,
        "operator_arbeitsplatz": Rolle.EXAM_OPERATOR in rollen and not ist_superadmin and Rolle.TRAINER not in rollen and Rolle.LEARNER not in rollen,
        "meine_org": meine_org,
        "org_design": org_design,
    }
