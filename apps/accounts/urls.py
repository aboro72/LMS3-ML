from django.urls import path

from .views import DashboardView, ProfilView, RegisterView, RoleHelpView


urlpatterns = [
    path("hilfe/", RoleHelpView.as_view(), name="role_help"),
    path("hilfe/<str:role>/", RoleHelpView.as_view(), name="role_help_detail"),
    path("register/", RegisterView.as_view(), name="register"),
    path("profil/", ProfilView.as_view(), name="profile"),
]
