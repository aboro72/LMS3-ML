from django.urls import path

from .views import InstallerView


urlpatterns = [
    path("", InstallerView.as_view(), name="installer"),
]

