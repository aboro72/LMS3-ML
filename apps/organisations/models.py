import uuid
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone
from django_quill.fields import QuillField

from apps.accounts.models import Rolle
from apps.security.fields import EncryptedCharField


class LizenzTyp(models.TextChoices):
    BASIC = "basic", "Basic"
    PRO = "pro", "Pro"
    ENTERPRISE = "enterprise", "Enterprise"


def default_invitation_expiry():
    return timezone.now() + timedelta(days=7)


class Organisation(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    logo = models.ImageField(upload_to="logos/", blank=True)
    kontakt_email = models.EmailField()
    website = models.URLField(blank=True)
    weiterleitungs_url = models.URLField(
        blank=True,
        verbose_name="Weiterleitungs-URL",
        help_text="Optionale externe oder alte URL, die auf die Mandanten-Startseite weiterleitet.",
    )
    lizenz_typ = models.CharField(max_length=20, choices=LizenzTyp.choices, default=LizenzTyp.BASIC)
    max_nutzer = models.PositiveIntegerField(default=50)
    max_kurse = models.PositiveIntegerField(default=10)
    ist_demo_organisation = models.BooleanField(default=False, verbose_name="Demo-Organisation")
    demo_inhalte_startbestand = models.PositiveIntegerField(default=0, editable=False)
    aktiv = models.BooleanField(default=True)
    erstellt_am = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Organisation"
        verbose_name_plural = "Organisationen"

    def __str__(self):
        return self.name


class Einladung(models.Model):
    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE)
    email = models.EmailField()
    rolle = models.CharField(max_length=20, choices=Rolle.choices)
    token = models.UUIDField(default=uuid.uuid4, unique=True)
    eingeladen_von = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    pruefung = models.ForeignKey(
        "exams.Pruefung", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="einladungen", verbose_name="Zertifikatspruefung",
    )
    erstellt_am = models.DateTimeField(auto_now_add=True)
    akzeptiert_am = models.DateTimeField(null=True, blank=True)
    abgelaufen_am = models.DateTimeField(default=default_invitation_expiry)

    class Meta:
        ordering = ["-erstellt_am"]
        verbose_name = "Einladung"
        verbose_name_plural = "Einladungen"

    def __str__(self):
        return f"{self.email} - {self.organisation} ({self.get_rolle_display()})"

    @property
    def ist_abgelaufen(self):
        return timezone.now() >= self.abgelaufen_am


# --------------------------------------------------------------------------- #
# Organisations-E-Mail-Konfiguration
# --------------------------------------------------------------------------- #
class OrganisationEmailKonfiguration(models.Model):
    organisation = models.OneToOneField(
        Organisation, on_delete=models.CASCADE, related_name="email_konfiguration"
    )
    aktiv = models.BooleanField(
        default=False,
        verbose_name="Eigenen E-Mail-Server verwenden",
        help_text="Wenn deaktiviert, wird der Plattform-Standard-SMTP genutzt.",
    )
    absender_name = models.CharField(max_length=200, blank=True, verbose_name="Absendername")
    absender_email = models.EmailField(blank=True, verbose_name="Absender-E-Mail")
    antwort_email = models.EmailField(
        blank=True,
        verbose_name="Antwort-E-Mail (Reply-To)",
        help_text="Zweite Adresse – z.B. support@meinefirma.de",
    )
    smtp_host = models.CharField(max_length=200, blank=True, verbose_name="SMTP-Host")
    smtp_port = models.PositiveIntegerField(default=587, verbose_name="SMTP-Port")
    smtp_user = models.CharField(max_length=200, blank=True, verbose_name="SMTP-Benutzername")
    smtp_password = EncryptedCharField(blank=True, verbose_name="SMTP-Passwort")
    smtp_use_tls = models.BooleanField(default=True, verbose_name="STARTTLS verwenden (Port 587)")
    smtp_use_ssl = models.BooleanField(default=False, verbose_name="SSL verwenden (Port 465)")
    einladung_betreff = models.CharField(max_length=200, default="Einladung zu {{ organisation }}")
    einladung_text = models.TextField(
        default="Hallo,\n\nSie wurden zu {{ organisation }} eingeladen. Bitte nehmen Sie die Einladung innerhalb von 7 Tagen an:\n{{ einladungslink }}\n\nFreundliche Gruesse\n{{ organisation }}"
    )
    passwort_reset_betreff = models.CharField(max_length=200, default="Passwort zuruecksetzen bei {{ organisation }}")
    passwort_reset_text = models.TextField(
        default="Hallo,\n\nSie haben angefordert, Ihr Passwort fuer {{ organisation }} zurueckzusetzen. Nutzen Sie dazu diesen Link:\n{{ passwort_reset_link }}\n\nWenn Sie dies nicht angefordert haben, koennen Sie diese E-Mail ignorieren."
    )

    class Meta:
        verbose_name = "E-Mail-Konfiguration"
        verbose_name_plural = "E-Mail-Konfigurationen"

    def __str__(self):
        return f"E-Mail-Konfiguration für {self.organisation}"

    def get_from_email(self):
        if self.absender_name and self.absender_email:
            return f"{self.absender_name} <{self.absender_email}>"
        return self.absender_email or None

    def get_connection(self):
        if not self.aktiv or not self.smtp_host:
            return None
        from django.core.mail import get_connection
        return get_connection(
            backend="django.core.mail.backends.smtp.EmailBackend",
            host=self.smtp_host,
            port=self.smtp_port,
            username=self.smtp_user,
            password=self.smtp_password,
            use_tls=self.smtp_use_tls,
            use_ssl=self.smtp_use_ssl,
            fail_silently=False,
        )


# --------------------------------------------------------------------------- #
# Organisations-Design (Kurs-Katalog, Kurs-Seiten, Navbar)
# --------------------------------------------------------------------------- #
class OrganisationDesign(models.Model):
    organisation = models.OneToOneField(
        Organisation, on_delete=models.CASCADE, related_name="design"
    )
    primary_color = models.CharField(
        max_length=20, default="#12315f",
        verbose_name="Primärfarbe",
        help_text="Navigationselemente, Überschriften, Rahmen",
    )
    secondary_color = models.CharField(
        max_length=20, default="#f28c28",
        verbose_name="Akzentfarbe",
        help_text="Buttons, Highlights, Fortschrittsbalken",
    )
    navbar_farbe = models.CharField(
        max_length=20, default="#0c2448",
        verbose_name="Navigationsleisten-Farbe",
    )
    hintergrund_farbe = models.CharField(
        max_length=20, default="#f6f8fb",
        verbose_name="Seiten-Hintergrundfarbe",
    )
    logo = models.ImageField(
        upload_to="org_design/logos/", blank=True,
        verbose_name="Organisations-Logo",
        help_text="Wird in Navbar und Kurskatalog angezeigt (PNG/SVG empfohlen)",
    )
    favicon = models.ImageField(
        upload_to="org_design/favicons/", blank=True,
        verbose_name="Favicon (16×16 oder 32×32 px)",
    )
    custom_css = models.TextField(
        blank=True,
        verbose_name="Eigenes CSS",
        help_text="Erweiterte Anpassungen – nur für erfahrene Nutzer",
    )

    class Meta:
        verbose_name = "Organisations-Design"
        verbose_name_plural = "Organisations-Designs"

    def __str__(self):
        return f"Design für {self.organisation}"


# --------------------------------------------------------------------------- #
# Organisations-Startseite (WYSIWYG Landing Page)
# --------------------------------------------------------------------------- #
class OrganisationStartseite(models.Model):
    organisation = models.OneToOneField(
        Organisation, on_delete=models.CASCADE, related_name="startseite"
    )
    aktiv = models.BooleanField(
        default=False,
        verbose_name="Eigene Startseite aktivieren",
        help_text="Wenn deaktiviert, wird die Plattform-Standardseite angezeigt.",
    )
    hero_titel = models.CharField(max_length=200, blank=True, verbose_name="Haupt-Überschrift")
    hero_untertitel = models.CharField(max_length=500, blank=True, verbose_name="Unter-Überschrift")
    hero_bild = models.ImageField(
        upload_to="org_design/hero/", blank=True,
        verbose_name="Hero-Hintergrundbild",
    )
    hero_button_text = models.CharField(
        max_length=100, blank=True, default="Kurse entdecken",
        verbose_name="Schaltflächen-Text",
    )
    inhalt = QuillField(blank=True, verbose_name="Seiteninhalt (WYSIWYG)")

    class Meta:
        verbose_name = "Organisations-Startseite"
        verbose_name_plural = "Organisations-Startseiten"

    def __str__(self):
        return f"Startseite für {self.organisation}"
