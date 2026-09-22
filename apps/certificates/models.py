import uuid

from django.conf import settings
from django.db import models


class ZertifikatDesign(models.Model):
    organisation = models.OneToOneField(
        "organisations.Organisation",
        on_delete=models.CASCADE,
        related_name="zertifikat_design",
    )
    primary_color = models.CharField(max_length=20, default="#12315f", verbose_name="Hauptfarbe")
    secondary_color = models.CharField(max_length=20, default="#f28c28", verbose_name="Akzentfarbe")
    org_display_name = models.CharField(
        max_length=200, blank=True, verbose_name="Anzeigename im Zertifikat",
        help_text="Leer lassen = Organisationsname wird verwendet",
    )
    footer_text = models.CharField(max_length=500, blank=True, verbose_name="Fußzeilentext")
    signature_line = models.CharField(max_length=200, blank=True, verbose_name="Unterschriftenzeile")
    unterschrift_1 = models.ImageField(upload_to="zertifikat_unterschriften/", blank=True, verbose_name="Unterschrift 1")
    unterschrift_2 = models.ImageField(upload_to="zertifikat_unterschriften/", blank=True, verbose_name="Unterschrift 2")
    logo = models.ImageField(upload_to="zertifikat_logos/", blank=True, verbose_name="Logo")

    class Meta:
        verbose_name = "Zertifikat-Design"
        verbose_name_plural = "Zertifikat-Designs"

    def __str__(self):
        return f"Design für {self.organisation}"

    def get_display_name(self, organisation):
        return self.org_display_name or organisation.name


class Zertifikat(models.Model):
    nutzer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="zertifikate",
    )
    pruefungsversuch = models.OneToOneField(
        "exams.PruefungsVersuch",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="zertifikat",
    )
    einschreibung = models.ForeignKey(
        "courses.Einschreibung",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="zertifikate",
    )
    code = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    zertifikatsnummer = models.CharField(max_length=80, unique=True, null=True, blank=True, editable=False)
    pdf_datei = models.FileField(upload_to="zertifikate/", blank=True)
    ausgestellt_am = models.DateTimeField(auto_now_add=True)
    ist_widerrufen = models.BooleanField(default=False)

    class Meta:
        ordering = ["-ausgestellt_am"]
        verbose_name = "Zertifikat"
        verbose_name_plural = "Zertifikate"

    def __str__(self):
        return f"Zertifikat {self.code} - {self.nutzer}"

    def get_titel(self):
        if self.pruefungsversuch:
            return self.pruefungsversuch.pruefung.titel
        if self.einschreibung:
            return self.einschreibung.kurs.titel
        return "Zertifikat"

    def get_organisation(self):
        if self.pruefungsversuch:
            return self.pruefungsversuch.pruefung.organisation
        if self.einschreibung:
            return self.einschreibung.kurs.organisation
        return None

    def get_inhaber_name(self):
        return self.nutzer.get_full_name() or self.nutzer.username


class InterneZertifikatsnummer(models.Model):
    naechste_nummer = models.PositiveIntegerField(default=5001)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1, defaults={"naechste_nummer": 5001})
        return obj
