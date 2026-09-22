from django.urls import path
from .single_system import system_view
from apps.certificates.views import ZertifikatDesignView

from .views import (
    OffentlicheStartseiteRedirectView,
    OffentlicheStartseiteView,
    OrgAdminDashboardView,
    OrgDesignView,
    EinladungAnnehmenView,
    OrgEinladungCreateView,
    OrgEmailKonfigView,
    OrgMemberListView,
    OrgStartseitePageBuilderView,
    OrgStartseiteView,
    SingleSystemStartseiteView,
    SingleSystemStartseiteEditorView,
    SingleSystemPageBuilderView,
    SuperadminOrganisationenView,
)
from apps.accounts.views import OrganisationLoginView, OrganisationRegisterView

urlpatterns = [
    path("verwaltung/benutzer/", system_view(OrgMemberListView.as_view()), name="system_members"),
    path("verwaltung/einladen/", system_view(OrgEinladungCreateView.as_view()), name="system_invite"),
    path("verwaltung/design/", system_view(OrgDesignView.as_view()), name="system_design"),
    path("verwaltung/email/", system_view(OrgEmailKonfigView.as_view()), name="system_email"),
    path("verwaltung/zertifikat-design/", system_view(ZertifikatDesignView.as_view()), name="system_cert_design"),
    path("startseite/", SingleSystemStartseiteView.as_view(), name="single_system_startseite"),
    path("startseite/editor/", SingleSystemStartseiteEditorView.as_view(), name="single_system_startseite_editor"),
    path("startseite/pagebuilder/", SingleSystemPageBuilderView.as_view(), name="single_system_pagebuilder"),
    # Öffentliche Organisations-Startseite
    path("o/<slug:slug>/", OffentlicheStartseiteRedirectView.as_view(), name="org_public_home_legacy"),

    # Org-Selbstregistrierung
    path("<slug:org_slug>/login/", OrganisationLoginView.as_view(), name="tenant_login"),
    path("<slug:org_slug>/register/", OrganisationRegisterView.as_view(), name="tenant_register"),

    # Org-Admin-Bereich
    path("organisationen/<slug:slug>/", OrgAdminDashboardView.as_view(), name="org_admin_dashboard"),
    path("organisationen/<slug:slug>/mitglieder/", OrgMemberListView.as_view(), name="org_members"),
    path("organisationen/einladung/<uuid:token>/", EinladungAnnehmenView.as_view(), name="org_invitation_accept"),
    path("organisationen/<slug:slug>/einladen/", OrgEinladungCreateView.as_view(), name="org_invite"),
    path("organisationen/<slug:slug>/email-konfiguration/", OrgEmailKonfigView.as_view(), name="org_email_config"),
    path("organisationen/<slug:slug>/design/", OrgDesignView.as_view(), name="org_design"),
    path("organisationen/<slug:slug>/startseite/", OrgStartseiteView.as_view(), name="org_startseite"),
    path("organisationen/<slug:slug>/startseite/pagebuilder/", OrgStartseitePageBuilderView.as_view(), name="org_startseite_pagebuilder"),

    # Superadmin
    path("superadmin/organisationen/", SuperadminOrganisationenView.as_view(), name="superadmin_orgs"),

    # Kanonische Mandanten-Startseite
    path("<slug:slug>/", OffentlicheStartseiteView.as_view(), name="org_public_home"),
]

