from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from apps.accounts.views import DashboardView, HomeView


urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    path("admin/", admin.site.urls),
    path("accounts/", include("allauth.urls")),
    path("accounts/", include("apps.accounts.urls")),
    path("install/<str:token>/", include("apps.installer.urls")),
    path("", include("apps.courses.urls")),
    path("", include("apps.exams.urls")),
    path("", include("apps.payments.urls")),
    path("", include("apps.certificates.urls")),
    path("", include("apps.organisations.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
