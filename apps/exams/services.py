import random
import json
from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import Antwort, Frage, Pruefung, Pruefungsversion, PruefungsVersuch, TeilnehmerAntwort


class MaxVersucheErreicht(Exception):
    pass


class NichtGenugFragenInThema(Exception):
    pass


def aktive_sekunden(versuch, jetzt=None):
    jetzt = jetzt or timezone.now()
    sekunden = versuch.aktive_sekunden
    if versuch.aktive_phase_begonnen_am:
        sekunden += max(0, int((jetzt - versuch.aktive_phase_begonnen_am).total_seconds()))
    return sekunden


def restliche_sekunden(versuch, jetzt=None):
    if not versuch.pruefung.zeitlimit_minuten:
        return None
    return max(0, versuch.pruefung.zeitlimit_minuten * 60 - aktive_sekunden(versuch, jetzt))


@transaction.atomic
def setze_pruefung_fort(versuch):
    if versuch.status != PruefungsVersuch.Status.LAUFEND:
        return False
    jetzt = timezone.now()
    versuch.aktive_phase_begonnen_am = jetzt
    versuch.letzte_aktivitaet_am = jetzt
    versuch.pausiert_am = None
    versuch.save(update_fields=["aktive_phase_begonnen_am", "letzte_aktivitaet_am", "pausiert_am"])
    return True


@transaction.atomic
def pausiere_pruefung(versuch, jetzt=None):
    if versuch.status != PruefungsVersuch.Status.LAUFEND or not versuch.aktive_phase_begonnen_am:
        return False
    jetzt = jetzt or timezone.now()
    versuch.aktive_sekunden = aktive_sekunden(versuch, jetzt)
    versuch.aktive_phase_begonnen_am = None
    versuch.letzte_aktivitaet_am = jetzt
    versuch.pausiert_am = jetzt
    versuch.save(update_fields=["aktive_sekunden", "aktive_phase_begonnen_am", "letzte_aktivitaet_am", "pausiert_am"])
    return True


@transaction.atomic
def bestaetige_aktivitaet(versuch, jetzt=None):
    if versuch.status != PruefungsVersuch.Status.LAUFEND:
        return False
    jetzt = jetzt or timezone.now()
    versuch.letzte_aktivitaet_am = jetzt
    versuch.save(update_fields=["letzte_aktivitaet_am"])
    return True


def waehle_pruefungsfragen(pruefung):
    fragen_queryset = Frage.objects.filter(fragenkatalog=pruefung.fragenkatalog, eltern_szenario__isnull=True, aktiv=True).prefetch_related("antworten", "zuordnungen")
    themenquoten = list(pruefung.themenquoten.select_related("thema"))
    if not themenquoten:
        fragen = list(fragen_queryset)
        random.shuffle(fragen)
        return fragen[:pruefung.anzahl_fragen]
    fragen, bereits_gewaehlt = [], set()
    for quote in themenquoten:
        kandidaten = list(fragen_queryset.filter(tags=quote.thema).exclude(id__in=bereits_gewaehlt).distinct())
        random.shuffle(kandidaten)
        if len(kandidaten) < quote.anzahl_fragen:
            raise NichtGenugFragenInThema(f"Für das Thema „{quote.thema}“ stehen nur {len(kandidaten)} passende Fragen zur Verfügung.")
        auswahl = kandidaten[:quote.anzahl_fragen]
        fragen.extend(auswahl)
        bereits_gewaehlt.update(frage.id for frage in auswahl)
    rest_anzahl = pruefung.anzahl_fragen - len(fragen)
    if rest_anzahl < 0:
        raise NichtGenugFragenInThema("Die Summe der Themenquoten ist größer als die Gesamtzahl der Prüfung.")
    weitere_kandidaten = list(fragen_queryset.exclude(id__in=bereits_gewaehlt))
    if len(weitere_kandidaten) < rest_anzahl:
        raise NichtGenugFragenInThema(
            f"Für die Gesamtzahl von {pruefung.anzahl_fragen} Fragen stehen nur {len(fragen) + len(weitere_kandidaten)} Fragen zur Verfügung."
        )
    fragen.extend(random.sample(weitere_kandidaten, rest_anzahl))
    random.shuffle(fragen)
    return fragen


@transaction.atomic
def starte_pruefung(pruefung, nutzer):
    bisherige_versuche = PruefungsVersuch.objects.filter(pruefung=pruefung, nutzer=nutzer).count()
    if pruefung.max_versuche is not None and bisherige_versuche >= pruefung.max_versuche:
        raise MaxVersucheErreicht("Maximale Anzahl an Versuchen erreicht.")

    fragen = waehle_pruefungsfragen(pruefung)
    if not pruefung.zufaellige_fragenreihenfolge:
        fragen.sort(key=lambda frage: frage.id)

    version = Pruefungsversion.objects.create(
        pruefung=pruefung,
        versionsnummer=(Pruefungsversion.objects.filter(pruefung=pruefung).count() + 1),
        erstellt_von=nutzer,
        snapshot={
            "parameter": {
                "anzahl_fragen": pruefung.anzahl_fragen,
                "zeitlimit_minuten": pruefung.zeitlimit_minuten,
                "bestehensgrenze_prozent": pruefung.bestehensgrenze_prozent,
                "pdf_antwortzeilen": pruefung.pdf_antwortzeilen,
                "pdf_fusszeile": pruefung.pdf_fusszeile,
            },
            "fragen": [
                {
                    "id": frage.pk,
                    "typ": frage.typ,
                    "text": frage.fragetext.html,
                    "erklaerung": frage.erklaerung.html,
                    "bewertungshinweis": frage.bewertungshinweis.html,
                    "punkte": frage.punkte,
                    "antworten": list(frage.antworten.values("id", "antworttext", "ist_korrekt", "reihenfolge")),
                    "zuordnungen": list(frage.zuordnungen.values("id", "linkes_element", "rechtes_element", "reihenfolge")),
                }
                for frage in fragen
            ],
        },
    )

    jetzt = timezone.now()
    return PruefungsVersuch.objects.create(
        nutzer=nutzer,
        pruefung=pruefung,
        versuch_nummer=bisherige_versuche + 1,
        pruefungsversion=version,
        fragen_reihenfolge=[frage.id for frage in fragen],
        aktive_phase_begonnen_am=jetzt,
        letzte_aktivitaet_am=jetzt,
    )


def speichere_antwort(versuch, frage, daten):
    if frage.typ == Frage.Typ.ZUORDNUNG:
        mapping = daten.get("zuordnung_json", {})
        if isinstance(mapping, str):
            try:
                mapping = json.loads(mapping)
            except (TypeError, ValueError):
                raise ValidationError("Ungültige Zuordnungen.")
        if not isinstance(mapping, dict):
            raise ValidationError("Ungültige Zuordnungen.")
        paare = list(frage.zuordnungen.all())
        erlaubte_ids = {str(paar.pk) for paar in paare}
        if any(key not in erlaubte_ids or not isinstance(value, str) for key, value in mapping.items()):
            raise ValidationError("Ungültige Zuordnungen.")
    teilnehmer_antwort, _ = TeilnehmerAntwort.objects.get_or_create(versuch=versuch, frage=frage)
    if frage.typ in [Frage.Typ.SINGLE_CHOICE, Frage.Typ.MULTIPLE_CHOICE, Frage.Typ.WAHR_FALSCH]:
        antwort_ids = daten.getlist("antworten") if hasattr(daten, "getlist") else daten.get("antworten", [])
        erlaubte_ids = list(frage.antworten.values_list("id", flat=True))
        antworten = Antwort.objects.filter(id__in=antwort_ids).filter(id__in=erlaubte_ids)
        teilnehmer_antwort.ausgewaehlte_antworten.set(antworten)
    elif frage.typ in [Frage.Typ.FREITEXT, Frage.Typ.SZENARIO]:
        teilnehmer_antwort.freitext_antwort = daten.get("freitext_antwort", "")
    elif frage.typ == Frage.Typ.ZUORDNUNG:
        teilnehmer_antwort.zuordnung_json = mapping
    teilnehmer_antwort.save()
    return teilnehmer_antwort


@transaction.atomic
def werte_versuch_aus(versuch):
    punkte_erreicht = Decimal("0")
    punkte_gesamt = Decimal("0")
    freitext_offen = False

    fragen = Frage.objects.filter(id__in=versuch.fragen_reihenfolge).prefetch_related("antworten", "zuordnungen")
    fragen_map = {frage.id: frage for frage in fragen}
    for frage_id in versuch.fragen_reihenfolge:
        frage = fragen_map.get(frage_id)
        if not frage:
            continue
        antwort, _ = TeilnehmerAntwort.objects.get_or_create(versuch=versuch, frage=frage)
        punkte_gesamt += Decimal(frage.punkte)
        punkte = Decimal("0")
        ist_korrekt = False

        if frage.typ in [Frage.Typ.SINGLE_CHOICE, Frage.Typ.WAHR_FALSCH]:
            richtige_ids = set(frage.antworten.filter(ist_korrekt=True).values_list("id", flat=True))
            gewaehlt_ids = set(antwort.ausgewaehlte_antworten.values_list("id", flat=True))
            ist_korrekt = len(gewaehlt_ids) == 1 and gewaehlt_ids == richtige_ids
            punkte = Decimal(frage.punkte) if ist_korrekt else Decimal("0")
        elif frage.typ == Frage.Typ.MULTIPLE_CHOICE:
            richtige_ids = set(frage.antworten.filter(ist_korrekt=True).values_list("id", flat=True))
            gewaehlt_ids = set(antwort.ausgewaehlte_antworten.values_list("id", flat=True))
            ist_korrekt = gewaehlt_ids == richtige_ids
            punkte = Decimal(frage.punkte) if ist_korrekt else Decimal("0")
        elif frage.typ == Frage.Typ.ZUORDNUNG:
            paare = list(frage.zuordnungen.all())
            mapping = antwort.zuordnung_json or {}
            korrekt = sum(1 for paar in paare if mapping.get(str(paar.id)) == paar.rechtes_element)
            punkte = Decimal(frage.punkte) * Decimal(korrekt) / Decimal(len(paare) or 1)
            ist_korrekt = korrekt == len(paare)
        elif frage.typ in [Frage.Typ.FREITEXT, Frage.Typ.SZENARIO]:
            if antwort.freitext_punkte is None:
                freitext_offen = True
                ist_korrekt = None
                punkte = Decimal("0")
            else:
                punkte = min(Decimal(antwort.freitext_punkte), Decimal(frage.punkte))
                ist_korrekt = punkte > Decimal("0")

        antwort.ist_korrekt = ist_korrekt
        antwort.punkte_vergeben = punkte
        antwort.save(update_fields=["ist_korrekt", "punkte_vergeben"])
        punkte_erreicht += punkte

    prozent = Decimal("0") if punkte_gesamt == 0 else (punkte_erreicht / punkte_gesamt) * Decimal("100")
    versuch.punkte_erreicht = punkte_erreicht
    versuch.punkte_gesamt = punkte_gesamt
    versuch.prozent_erreicht = prozent.quantize(Decimal("0.01"))
    versuch.bestanden = versuch.prozent_erreicht >= Decimal(versuch.pruefung.bestehensgrenze_prozent)
    versuch.status = PruefungsVersuch.Status.AUSSTEHEND if freitext_offen else PruefungsVersuch.Status.ABGESCHLOSSEN
    versuch.abgeschlossen_am = timezone.now()
    versuch.einsehbar_bis = versuch.abgeschlossen_am + timedelta(days=365)
    versuch.ergebnis_verschluesselt = json.dumps({
        "status": versuch.status,
        "bestanden": versuch.bestanden,
        "punkte_erreicht": str(versuch.punkte_erreicht),
        "punkte_gesamt": str(versuch.punkte_gesamt),
        "prozent_erreicht": str(versuch.prozent_erreicht),
        "abgeschlossen_am": versuch.abgeschlossen_am.isoformat(),
    })
    versuch.save()

    if versuch.bestanden and versuch.status == PruefungsVersuch.Status.ABGESCHLOSSEN:
        try:
            from apps.certificates.services import stelle_zertifikat_aus
            stelle_zertifikat_aus(versuch)
        except Exception:
            pass

    return versuch


def pruefe_zeitlimit(versuch):
    if not versuch.pruefung.zeitlimit_minuten:
        return False
    if not versuch.aktive_phase_begonnen_am:
        return False
    if aktive_sekunden(versuch) <= versuch.pruefung.zeitlimit_minuten * 60:
        return False
    pausiere_pruefung(versuch)
    versuch.status = PruefungsVersuch.Status.ABGELAUFEN
    versuch.abgeschlossen_am = timezone.now()
    versuch.einsehbar_bis = versuch.abgeschlossen_am + timedelta(days=365)
    versuch.save(update_fields=["status", "abgeschlossen_am", "einsehbar_bis"])
    return True
