from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.utils import timezone

from apps.courses.models import Einschreibung

from .models import AuditLog, OrganisationZahlungseinstellungen, Rechnung, Zahlung, Zahlungsart, Zahlungseinstellungen, Zahlungsstatus


@transaction.atomic
def erstelle_zahlung(kurs, nutzer, zahlungsart):
    if zahlungsart not in dict(lade_zahlungseinstellungen(kurs.organisation).aktive_zahlungsarten()):
        raise PermissionDenied("Zahlungen oder diese Zahlungsart sind außerhalb der Entwicklungsumgebung derzeit deaktiviert.")
    gebuehr, trainer_anteil = Zahlung.berechne_aufteilung(kurs.preis)
    zahlung = Zahlung.objects.create(
        nutzer=nutzer,
        kurs=kurs,
        trainer=kurs.erstellt_von,
        zahlungsart=zahlungsart,
        betrag_brutto=kurs.preis,
        plattform_gebuehr=gebuehr,
        trainer_anteil=trainer_anteil,
    )
    log_audit(
        actor=nutzer,
        organisation=kurs.organisation,
        action="zahlung_erstellt",
        obj=zahlung,
        message=f"Zahlung fuer Kurs '{kurs.titel}' erstellt.",
        metadata={"zahlungsart": zahlungsart, "betrag": str(kurs.preis)},
    )
    return zahlung


@transaction.atomic
def bestaetige_zahlung(zahlung, provider_referenz="", actor=None):
    if zahlung.status == Zahlungsstatus.BEZAHLT:
        return zahlung
    zahlung.status = Zahlungsstatus.BEZAHLT
    zahlung.provider_referenz = provider_referenz or zahlung.provider_referenz
    zahlung.bezahlt_am = timezone.now()
    zahlung.save(update_fields=["status", "provider_referenz", "bezahlt_am"])
    Einschreibung.objects.update_or_create(
        nutzer=zahlung.nutzer,
        kurs=zahlung.kurs,
        defaults={"bezahlt": True},
    )
    erstelle_rechnung(zahlung)
    log_audit(
        actor=actor or zahlung.nutzer,
        organisation=zahlung.kurs.organisation,
        action="zahlung_bestaetigt",
        obj=zahlung,
        message=f"Zahlung {zahlung.zahlung_id} wurde bestaetigt.",
        metadata={"provider_referenz": zahlung.provider_referenz},
    )
    return zahlung


@transaction.atomic
def erstelle_rechnung(zahlung):
    rechnung, _ = Rechnung.objects.get_or_create(
        zahlung=zahlung,
        defaults={
            "rechnungsnummer": Rechnung.naechste_nummer(),
            "empfaenger_name": zahlung.nutzer.get_full_name() or zahlung.nutzer.username,
            "empfaenger_email": zahlung.nutzer.email or "noreply@aborosoft.de",
            "betrag_netto": zahlung.betrag_brutto,
            "steuerbetrag": 0,
            "betrag_brutto": zahlung.betrag_brutto,
            "waehrung": zahlung.waehrung,
        },
    )
    return rechnung


def log_audit(actor=None, organisation=None, action="", obj=None, message="", metadata=None):
    return AuditLog.objects.create(
        actor=actor if getattr(actor, "is_authenticated", True) else None,
        organisation=organisation,
        action=action,
        object_type=obj.__class__.__name__ if obj is not None else "",
        object_id=str(getattr(obj, "pk", "")) if obj is not None else "",
        message=message,
        metadata=metadata or {},
    )


def zahlungsart_ist_automatisch(zahlungsart):
    return zahlungsart in [Zahlungsart.STRIPE, Zahlungsart.GOOGLE_PAY, Zahlungsart.PAYPAL]


def lade_zahlungseinstellungen(organisation=None):
    if organisation is None:
        return Zahlungseinstellungen.load()
    obj, _ = OrganisationZahlungseinstellungen.objects.get_or_create(organisation=organisation)
    return obj
