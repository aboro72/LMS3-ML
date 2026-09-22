from django.urls import path

from .views import ZertifikatDesignView, ZertifikatDownloadView, ZertifikatListeView, ZertifikatVerifyView

urlpatterns = [
    path("zertifikate/", ZertifikatListeView.as_view(), name="cert_list"),
    path("zertifikate/verify/<uuid:code>/", ZertifikatVerifyView.as_view(), name="cert_verify"),
    path("zertifikate/<uuid:code>/pdf/", ZertifikatDownloadView.as_view(), name="cert_download"),
    path("organisationen/<slug:slug>/zertifikat-design/", ZertifikatDesignView.as_view(), name="org_cert_design"),
]
