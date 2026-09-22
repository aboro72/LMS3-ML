from pathlib import Path

from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.text import slugify

from apps.accounts.models import Rolle
from apps.organisations.models import Organisation
from apps.organisations.single_system import bind_system_form
from apps.exams.models import Pruefung

from .models import Abschnitt, Begleitmaterial, Kurs, KursBewertung, KursKategorie, Lektion, Lernpfad, LernpfadKurs, Uebungsantwort, Uebungsfrage


def _eindeutiger_slug(modell, titel, pk=None):
    basis = slugify(titel) or "eintrag"
    slug = basis
    nummer = 2
    queryset = modell.objects.exclude(pk=pk) if pk else modell.objects.all()
    while queryset.filter(slug=slug).exists():
        slug = f"{basis}-{nummer}"
        nummer += 1
    return slug


def _validate_upload(uploaded_file, allowed_extensions, max_mb, label):
    if not uploaded_file:
        return
    suffix = Path(uploaded_file.name).suffix.lower()
    allowed = tuple(ext.lower() for ext in allowed_extensions)
    if suffix not in allowed:
        raise ValidationError(f"{label} erlaubt nur folgende Dateitypen: {', '.join(allowed)}.")
    max_bytes = max_mb * 1024 * 1024
    if uploaded_file.size > max_bytes:
        raise ValidationError(f"{label} darf maximal {max_mb} MB gross sein.")


class KursForm(forms.ModelForm):
    class Meta:
        model = Kurs
        fields = (
            "titel",
            "beschreibung",
            "thumbnail",
            "organisation",
            "kategorie",
            "sprache",
            "niveau",
            "angebotstyp",
            "pruefung",
            "ist_veroeffentlicht",
            "ist_kostenlos",
            "preis",
        )
        help_texts = {
            "beschreibung": "Optional – kann später ergänzt werden.",
            "angebotstyp": "Wählen Sie „Reine Zertifikatsprüfung“, wenn Teilnehmende keine Lektionen bearbeiten sollen.",
            "pruefung": "Bei einer reinen Zertifikatsprüfung erforderlich.",
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user and not user.is_superuser:
            organisation_ids = user.profile.filter(rolle=Rolle.TRAINER, aktiv=True).values_list("organisation_id", flat=True)
            self.fields["organisation"].queryset = Organisation.objects.filter(id__in=organisation_ids)
            self.fields["pruefung"].queryset = Pruefung.objects.filter(organisation_id__in=organisation_ids)
            self.fields["kategorie"].queryset = KursKategorie.objects.filter(organisation_id__in=organisation_ids)
        bind_system_form(self)

    def clean(self):
        cleaned_data = super().clean()
        angebotstyp = cleaned_data.get("angebotstyp")
        pruefung = cleaned_data.get("pruefung")
        organisation = cleaned_data.get("organisation")
        if angebotstyp == Kurs.Angebotstyp.ZERTIFIKAT and not pruefung:
            self.add_error("pruefung", "Bitte wählen Sie die Zertifikatsprüfung aus.")
        if pruefung and organisation and pruefung.organisation_id != organisation.id:
            self.add_error("pruefung", "Die Prüfung muss zur gewählten Organisation gehören.")
        return cleaned_data

    def clean_thumbnail(self):
        thumbnail = self.cleaned_data.get("thumbnail")
        _validate_upload(
            thumbnail,
            settings.ALLOWED_IMAGE_EXTENSIONS,
            settings.MAX_IMAGE_UPLOAD_MB,
            "Thumbnail",
        )
        return thumbnail

    def save(self, commit=True):
        kurs = super().save(commit=False)
        if not kurs.slug:
            kurs.slug = _eindeutiger_slug(Kurs, kurs.titel, kurs.pk)
        if commit:
            kurs.save()
            self.save_m2m()
        return kurs


class KursKategorieForm(forms.ModelForm):
    class Meta:
        model = KursKategorie
        fields = ("organisation", "parent", "name")

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user and not user.is_superuser:
            org_ids = user.profile.filter(rolle=Rolle.TRAINER, aktiv=True).values_list("organisation_id", flat=True)
            self.fields["organisation"].queryset = Organisation.objects.filter(id__in=org_ids)
            self.fields["parent"].queryset = KursKategorie.objects.filter(organisation_id__in=org_ids)
        bind_system_form(self)


class AbschnittForm(forms.ModelForm):
    class Meta:
        model = Abschnitt
        fields = ("titel", "reihenfolge", "ist_veroeffentlicht")


class LektionForm(forms.ModelForm):
    class Meta:
        model = Lektion
        fields = (
            "titel",
            "typ",
            "reihenfolge",
            "inhalt",
            "video_url",
            "datei",
            "dauer_minuten",
            "ist_vorschau",
        )
        labels = {
            "typ": "Lektionstyp",
            "inhalt": "Begleittext",
            "video_url": "Video-URL",
            "datei": "Upload-Datei",
            "dauer_minuten": "Dauer in Minuten",
            "ist_vorschau": "Kostenlose Vorschau",
        }
        help_texts = {
            "video_url": "Optional fuer externe Videoquellen. Fuer Selfhosting bevorzugt: Video als Datei hochladen.",
            "datei": "Bei Video-Lektionen MP4, WebM, MOV oder M4V hochladen. Bei Dokumenten PDF oder andere Kursdateien.",
            "inhalt": "Optionaler Text unter dem Video oder Dokument.",
        }

    def clean(self):
        cleaned_data = super().clean()
        lesson_type = cleaned_data.get("typ")
        uploaded_file = cleaned_data.get("datei")
        video_url = cleaned_data.get("video_url")
        if lesson_type == Lektion.Typ.VIDEO and not uploaded_file and not video_url and not self.instance.datei:
            raise ValidationError("Video-Lektionen benoetigen eine Video-URL oder eine hochgeladene Videodatei.")
        if uploaded_file:
            if lesson_type == Lektion.Typ.VIDEO:
                _validate_upload(
                    uploaded_file,
                    settings.ALLOWED_VIDEO_EXTENSIONS,
                    settings.MAX_VIDEO_UPLOAD_MB,
                    "Video-Upload",
                )
            else:
                _validate_upload(
                    uploaded_file,
                    settings.ALLOWED_DOCUMENT_EXTENSIONS,
                    settings.MAX_DOCUMENT_UPLOAD_MB,
                    "Lektionsdatei",
                )
        return cleaned_data


class BegleitmaterialForm(forms.ModelForm):
    class Meta:
        model = Begleitmaterial
        fields = ("titel", "datei", "reihenfolge")

    def clean_datei(self):
        datei = self.cleaned_data.get("datei")
        _validate_upload(
            datei,
            settings.ALLOWED_DOCUMENT_EXTENSIONS,
            settings.MAX_DOCUMENT_UPLOAD_MB,
            "Begleitmaterial",
        )
        return datei


class LektionMedienForm(forms.ModelForm):
    class Meta:
        model = Lektion
        fields = ("typ", "video_url", "datei")
        labels = {
            "typ": "Lektionstyp",
            "video_url": "Video-URL",
            "datei": "Upload-Datei",
        }
        help_texts = {
            "datei": "Fuer Videos MP4, WebM, MOV oder M4V hochladen. Fuer Dokumente PDF oder andere Kursdateien.",
            "video_url": "Optional fuer externe Videoquellen.",
        }

    def clean(self):
        cleaned_data = super().clean()
        lesson_type = cleaned_data.get("typ")
        uploaded_file = cleaned_data.get("datei")
        video_url = cleaned_data.get("video_url")
        if lesson_type == Lektion.Typ.VIDEO and not uploaded_file and not video_url and not self.instance.datei:
            raise ValidationError("Video-Lektionen benoetigen eine Video-URL oder eine hochgeladene Videodatei.")
        if uploaded_file:
            if lesson_type == Lektion.Typ.VIDEO:
                _validate_upload(
                    uploaded_file,
                    settings.ALLOWED_VIDEO_EXTENSIONS,
                    settings.MAX_VIDEO_UPLOAD_MB,
                    "Video-Upload",
                )
            else:
                _validate_upload(
                    uploaded_file,
                    settings.ALLOWED_DOCUMENT_EXTENSIONS,
                    settings.MAX_DOCUMENT_UPLOAD_MB,
                    "Lektionsdatei",
                )
        return cleaned_data



class LernpfadForm(forms.ModelForm):
    class Meta:
        model = Lernpfad
        fields = ("titel", "beschreibung", "organisation", "ist_veroeffentlicht")
        labels = {
            "titel": "Titel",
            "beschreibung": "Beschreibung",
            "organisation": "Organisation",
            "ist_veroeffentlicht": "Veroeffentlicht",
        }
        widgets = {
            "beschreibung": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user and not user.is_superuser:
            organisation_ids = user.profile.filter(rolle=Rolle.TRAINER, aktiv=True).values_list("organisation_id", flat=True)
            self.fields["organisation"].queryset = Organisation.objects.filter(id__in=organisation_ids)
        bind_system_form(self)

    def save(self, commit=True):
        lernpfad = super().save(commit=False)
        if not lernpfad.slug:
            lernpfad.slug = _eindeutiger_slug(Lernpfad, lernpfad.titel, lernpfad.pk)
        if commit:
            lernpfad.save()
            self.save_m2m()
        return lernpfad


class LernpfadKursForm(forms.ModelForm):
    class Meta:
        model = LernpfadKurs
        fields = ("kurs", "reihenfolge", "pflichtkurs")
        labels = {
            "kurs": "Kurs",
            "reihenfolge": "Reihenfolge",
            "pflichtkurs": "Pflichtkurs",
        }

    def __init__(self, *args, lernpfad=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        queryset = Kurs.objects.none()
        if lernpfad is not None:
            queryset = Kurs.objects.filter(organisation=lernpfad.organisation).order_by("titel")
            existing_ids = lernpfad.pfad_kurse.values_list("kurs_id", flat=True)
            queryset = queryset.exclude(id__in=existing_ids)
        elif user and user.is_superuser:
            queryset = Kurs.objects.all().order_by("organisation__name", "titel")
        self.fields["kurs"].queryset = queryset
class UebungsfrageForm(forms.ModelForm):
    class Meta:
        model = Uebungsfrage
        fields = ("frage", "erklaerung", "reihenfolge", "aktiv")
        widgets = {
            "frage": forms.Textarea(attrs={"rows": 3}),
            "erklaerung": forms.Textarea(attrs={"rows": 3}),
        }


class UebungsantwortForm(forms.ModelForm):
    class Meta:
        model = Uebungsantwort
        fields = ("antwort", "ist_korrekt", "reihenfolge")

class KursBewertungForm(forms.ModelForm):
    class Meta:
        model = KursBewertung
        fields = ("sterne", "kommentar")
        widgets = {
            "sterne": forms.NumberInput(attrs={"class": "form-control", "min": 1, "max": 5}),
            "kommentar": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }
