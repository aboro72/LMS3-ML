import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.security.fields import EncryptedCharField, EncryptedTextField


class Zahlungsart(models.TextChoices):
    STRIPE = "stripe", "Stripe"
    GOOGLE_PAY = "google_pay", "Google Pay"
    BANK_TRANSFER = "bank_transfer", "Ueberweisung"
    PAYPAL = "paypal", "PayPal"


class Zahlungsstatus(models.TextChoices):
    OFFEN = "offen", "Offen"
    BEZAHLT = "bezahlt", "Bezahlt"
    FEHLGESCHLAGEN = "fehlgeschlagen", "Fehlgeschlagen"
    STORNIERT = "storniert", "Storniert"


class Auszahlungsstatus(models.TextChoices):
    OFFEN = "offen", "Offen"
    GEMELDET = "gemeldet", "Betreiber informiert"
    AUSGEZAHLT = "ausgezahlt", "Ausgezahlt"


class Zahlungseinstellungen(models.Model):
    payment_aktiv = models.BooleanField("Zahlungen aktivieren", default=False)
    stripe_aktiv = models.BooleanField(default=False)
    stripe_public_key = models.CharField(max_length=255, blank=True)
    stripe_secret_key = EncryptedCharField(blank=True)
    google_pay_aktiv = models.BooleanField(default=False)
    paypal_aktiv = models.BooleanField(default=False)
    paypal_client_id = models.CharField(max_length=255, blank=True)
    paypal_secret = EncryptedCharField(blank=True)
    ueberweisung_aktiv = models.BooleanField(default=True)
    kontoinhaber = EncryptedCharField(blank=True)
    iban = EncryptedCharField(blank=True)
    bic = EncryptedCharField(blank=True)
    bankname = EncryptedCharField(blank=True)
    demo_autoconfirm = models.BooleanField(default=False)
    aktualisiert_am = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Zahlungseinstellungen"
        verbose_name_plural = "Zahlungseinstellungen"

    def __str__(self):
        return "Zahlungseinstellungen"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def aktive_zahlungsarten(self):
        choices = []
        if not self.payment_aktiv:
            return choices
        # Online-Anbieter sind bis zur echten Integration nur lokal im Demo-Modus verfuegbar.
        demo = settings.DEBUG and self.demo_autoconfirm
        if demo and self.stripe_aktiv:
            choices.append((Zahlungsart.STRIPE, Zahlungsart.STRIPE.label))
            choices.append((Zahlungsart.GOOGLE_PAY, Zahlungsart.GOOGLE_PAY.label))
        elif demo and self.google_pay_aktiv:
            choices.append((Zahlungsart.GOOGLE_PAY, Zahlungsart.GOOGLE_PAY.label))
        if demo and self.paypal_aktiv:
            choices.append((Zahlungsart.PAYPAL, Zahlungsart.PAYPAL.label))
        if self.ueberweisung_aktiv:
            choices.append((Zahlungsart.BANK_TRANSFER, Zahlungsart.BANK_TRANSFER.label))
        return choices


class OrganisationZahlungseinstellungen(models.Model):
    """Abgeschottete Anbieter- und Bankdaten einer einzelnen Organisation."""
    organisation = models.OneToOneField("organisations.Organisation", on_delete=models.CASCADE, related_name="zahlungseinstellungen")
    payment_aktiv = models.BooleanField("Bezahlte Angebote aktivieren", default=False)
    stripe_aktiv = models.BooleanField("Stripe anbieten", default=False)
    stripe_public_key = models.CharField(max_length=255, blank=True)
    stripe_secret_key = EncryptedCharField(blank=True)
    paypal_aktiv = models.BooleanField("PayPal anbieten", default=False)
    paypal_client_id = models.CharField(max_length=255, blank=True)
    paypal_secret = EncryptedCharField(blank=True)
    ueberweisung_aktiv = models.BooleanField("Bankueberweisung anbieten", default=False)
    kontoinhaber = EncryptedCharField(blank=True)
    iban = EncryptedCharField(blank=True)
    bic = EncryptedCharField(blank=True)
    bankname = EncryptedCharField(blank=True)
    aktualisiert_am = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Organisations-Zahlungseinstellungen"
        verbose_name_plural = "Organisations-Zahlungseinstellungen"

    def __str__(self):
        return f"Zahlungseinstellungen – {self.organisation}"

    def aktive_zahlungsarten(self):
        if not self.payment_aktiv:
            return []
        choices = []
        if self.stripe_aktiv and self.stripe_public_key and self.stripe_secret_key:
            choices.append((Zahlungsart.STRIPE, Zahlungsart.STRIPE.label))
        if self.paypal_aktiv and self.paypal_client_id and self.paypal_secret:
            choices.append((Zahlungsart.PAYPAL, Zahlungsart.PAYPAL.label))
        if self.ueberweisung_aktiv and self.iban:
            choices.append((Zahlungsart.BANK_TRANSFER, Zahlungsart.BANK_TRANSFER.label))
        return choices


class Zahlung(models.Model):
    zahlung_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    nutzer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="zahlungen")
    kurs = models.ForeignKey("courses.Kurs", on_delete=models.CASCADE, related_name="zahlungen")
    trainer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="trainer_zahlungen")
    zahlungsart = models.CharField(max_length=30, choices=Zahlungsart.choices)
    status = models.CharField(max_length=30, choices=Zahlungsstatus.choices, default=Zahlungsstatus.OFFEN)
    auszahlungsstatus = models.CharField(max_length=30, choices=Auszahlungsstatus.choices, default=Auszahlungsstatus.OFFEN)
    betrag_brutto = models.DecimalField(max_digits=10, decimal_places=2)
    plattform_gebuehr = models.DecimalField(max_digits=10, decimal_places=2)
    trainer_anteil = models.DecimalField(max_digits=10, decimal_places=2)
    waehrung = models.CharField(max_length=3, default="EUR")
    provider_referenz = EncryptedCharField(blank=True)
    betreiber_notiz = EncryptedTextField(blank=True)
    erstellt_am = models.DateTimeField(auto_now_add=True)
    bezahlt_am = models.DateTimeField(null=True, blank=True)
    ausgezahlt_am = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-erstellt_am"]
        verbose_name = "Zahlung"
        verbose_name_plural = "Zahlungen"

    def __str__(self):
        return f"{self.kurs} - {self.nutzer} - {self.betrag_brutto} {self.waehrung}"

    @classmethod
    def berechne_aufteilung(cls, betrag):
        brutto = Decimal(betrag)
        gebuehr = (brutto * Decimal(settings.PLATFORM_COMMISSION_PERCENT) / Decimal("100")).quantize(Decimal("0.01"))
        trainer_anteil = brutto - gebuehr
        return gebuehr, trainer_anteil

class Rechnung(models.Model):
    zahlung = models.OneToOneField(Zahlung, on_delete=models.CASCADE, related_name="rechnung")
    rechnungsnummer = models.CharField(max_length=40, unique=True)
    rechnungsdatum = models.DateTimeField(auto_now_add=True)
    empfaenger_name = models.CharField(max_length=255)
    empfaenger_email = models.EmailField()
    betrag_netto = models.DecimalField(max_digits=10, decimal_places=2)
    steuerbetrag = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    betrag_brutto = models.DecimalField(max_digits=10, decimal_places=2)
    waehrung = models.CharField(max_length=3, default="EUR")

    class Meta:
        ordering = ["-rechnungsdatum"]
        verbose_name = "Rechnung/Beleg"
        verbose_name_plural = "Rechnungen/Belege"

    def __str__(self):
        return self.rechnungsnummer

    @classmethod
    def naechste_nummer(cls):
        jahr = timezone.now().year
        prefix = f"RE-{jahr}-"
        letzte = cls.objects.filter(rechnungsnummer__startswith=prefix).order_by("-rechnungsnummer").first()
        if not letzte:
            return f"{prefix}0001"
        nummer = int(letzte.rechnungsnummer.rsplit("-", 1)[-1]) + 1
        return f"{prefix}{nummer:04d}"


class AuditLog(models.Model):
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    organisation = models.ForeignKey("organisations.Organisation", on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=100)
    object_type = models.CharField(max_length=100, blank=True)
    object_id = models.CharField(max_length=100, blank=True)
    message = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    erstellt_am = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-erstellt_am"]
        verbose_name = "Audit-Log"
        verbose_name_plural = "Audit-Logs"

    def __str__(self):
        return f"{self.erstellt_am:%Y-%m-%d %H:%M} - {self.action}"
