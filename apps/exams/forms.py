import csv
import json
import re
from io import TextIOWrapper

from django import forms
from django.contrib.auth import get_user_model
from django.forms import BaseInlineFormSet, inlineformset_factory
from django_quill.quill import Quill

from apps.accounts.models import Rolle
from apps.organisations.models import Organisation
from apps.organisations.single_system import bind_system_form

from .models import Antwort, Frage, Fragenkatalog, FragenTag, Pruefung, PruefungsThemenquote, TeilnehmerAntwort, ZuordnungsPaar


class FragenkatalogForm(forms.ModelForm):
    class Meta:
        model = Fragenkatalog
        fields = ("titel", "beschreibung", "organisation")
        widgets = {
            "titel": forms.TextInput(attrs={"class": "form-control", "placeholder": "z. B. Zertifikatsprüfung Grundlagen"}),
            "beschreibung": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Optional: Zweck und Inhalt des Katalogs"}),
            "organisation": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user and not user.is_superuser:
            organisation_ids = user.profile.filter(rolle__in=[Rolle.TRAINER, Rolle.EXAM_OPERATOR], aktiv=True).values_list("organisation_id", flat=True)
            self.fields["organisation"].queryset = Organisation.objects.filter(id__in=organisation_ids)
        bind_system_form(self)


class FrageForm(forms.ModelForm):
    themen = forms.CharField(
        required=False,
        label="Themengebiete",
        help_text="Mehrere Themen mit Komma trennen, z. B. Datenschutz, Grundlagen.",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "z. B. Datenschutz, Grundlagen",
                "autocomplete": "off",
            }
        ),
    )

    class Meta:
        model = Frage
        fields = ("typ", "fragetext", "erklaerung", "bewertungshinweis", "schwierigkeit", "punkte", "eltern_szenario")

    def __init__(self, *args, fragenkatalog=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fragenkatalog = fragenkatalog
        self.fields["typ"].widget.attrs["class"] = "form-select"
        self.fields["schwierigkeit"].widget.attrs["class"] = "form-select"
        self.fields["punkte"].widget.attrs.update({"class": "form-control", "min": 1})
        self.fields["eltern_szenario"].widget.attrs["class"] = "form-select"
        if fragenkatalog:
            self.fields["eltern_szenario"].queryset = fragenkatalog.fragen.filter(typ=Frage.Typ.SZENARIO)
            if self.instance.pk:
                self.initial["themen"] = ", ".join(self.instance.tags.values_list("name", flat=True))

    def save(self, commit=True):
        frage = super().save(commit=commit)
        if commit:
            self.save_themen(frage)
        return frage

    def clean(self):
        data = super().clean()
        if data.get("typ") in [Frage.Typ.FREITEXT, Frage.Typ.SZENARIO]:
            schema = data.get("bewertungshinweis")
            if not schema or not schema.html.strip():
                self.add_error("bewertungshinweis", "Bitte legen Sie die erwarteten Inhalte und die Punktverteilung fest.")
        return data

    def save_themen(self, frage):
        if not self.fragenkatalog:
            return
        themen = {name.strip() for name in self.cleaned_data["themen"].split(",") if name.strip()}
        tags = [
            FragenTag.objects.get_or_create(name=name, organisation=self.fragenkatalog.organisation)[0]
            for name in sorted(themen)
        ]
        frage.tags.set(tags)


class AntwortForm(forms.ModelForm):
    class Meta:
        model = Antwort
        fields = ("antworttext", "ist_korrekt", "reihenfolge")


class ZuordnungsPaarForm(forms.ModelForm):
    class Meta:
        model = ZuordnungsPaar
        fields = ("linkes_element", "rechtes_element", "reihenfolge")


class PruefungForm(forms.ModelForm):
    class Meta:
        model = Pruefung
        fields = (
            "titel",
            "beschreibung",
            "organisation",
            "fragenkatalog",
            "anzahl_fragen",
            "zeitlimit_minuten",
            "bestehensgrenze_prozent",
            "max_versuche",
            "zufaellige_fragenreihenfolge",
            "zufaellige_antwortfolge",
            "ist_aktiv",
            "zertifikatsnummernart",
            "externe_nummern_prefix",
            "externe_nummern_naechste",
            "externe_nummern_ende",
            "pdf_antwortzeilen",
            "pdf_fusszeile",
        )

        help_texts = {
            "anzahl_fragen": "Gesamtzahl der Prüfungsfragen. Themenquoten reservieren einen Teil dieser Gesamtzahl; die übrigen Fragen werden zufällig aus dem Katalog ergänzt.",
        }

    def clean_pdf_antwortzeilen(self):
        value = self.cleaned_data["pdf_antwortzeilen"]
        if value < 1 or value > 20:
            raise forms.ValidationError("Bitte wählen Sie zwischen 1 und 20 Antwortzeilen.")
        return value

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user and not user.is_superuser:
            organisation_ids = user.profile.filter(rolle__in=[Rolle.TRAINER, Rolle.EXAM_OPERATOR], aktiv=True).values_list("organisation_id", flat=True)
            self.fields["organisation"].queryset = Organisation.objects.filter(id__in=organisation_ids)
            self.fields["fragenkatalog"].queryset = Fragenkatalog.objects.filter(organisation_id__in=organisation_ids)
        bind_system_form(self)


class PruefungsThemenquoteForm(forms.ModelForm):
    class Meta:
        model = PruefungsThemenquote
        fields = ("thema", "anzahl_fragen")
        widgets = {
            "thema": forms.Select(attrs={"class": "form-select form-select-sm", "data-topic-select": "true"}),
            "anzahl_fragen": forms.NumberInput(attrs={"class": "form-control form-control-sm", "min": 1}),
        }

    def __init__(self, *args, pruefung=None, **kwargs):
        super().__init__(*args, **kwargs)
        if pruefung and pruefung.fragenkatalog_id:
            self.fields["thema"].queryset = FragenTag.objects.filter(
                organisation=pruefung.organisation,
                frage__fragenkatalog=pruefung.fragenkatalog,
            ).distinct()


class BasePruefungsThemenquoteFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        if any(self.errors):
            return
        for form in self.forms:
            if not form.cleaned_data or form.cleaned_data.get("DELETE"):
                continue
            thema = form.cleaned_data.get("thema")
            anzahl = form.cleaned_data.get("anzahl_fragen")
            if thema and anzahl:
                vorhanden = Frage.objects.filter(
                    fragenkatalog=self.instance.fragenkatalog,
                    eltern_szenario__isnull=True,
                    tags=thema,
                ).count()
                if anzahl > vorhanden:
                    raise forms.ValidationError(
                        f"Für das Thema „{thema}“ sind nur {vorhanden} Fragen im gewählten Katalog vorhanden."
                    )
        quoten_summe = sum(
            form.cleaned_data.get("anzahl_fragen") or 0
            for form in self.forms
            if form.cleaned_data and not form.cleaned_data.get("DELETE")
        )
        if quoten_summe > self.instance.anzahl_fragen:
            raise forms.ValidationError(
                f"Die Themenquoten ergeben {quoten_summe} Fragen, die Prüfung enthält aber nur {self.instance.anzahl_fragen} Fragen insgesamt."
            )


PruefungsThemenquoteFormSet = inlineformset_factory(
    Pruefung,
    PruefungsThemenquote,
    form=PruefungsThemenquoteForm,
    formset=BasePruefungsThemenquoteFormSet,
    extra=0,
    can_delete=True,
)


class CSVImportForm(forms.Form):
    datei = forms.FileField()
    legacy_themen_prefix = re.compile(r"^\s*\[(?:\d+\s+)?(?P<thema>[^\]]+)\]\s*")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["datei"].widget.attrs["class"] = "form-control"

    def _quill_from_html(self, html):
        return Quill(json.dumps({"delta": "", "html": html or ""}))

    def _is_correct(self, value):
        return str(value or "").strip().lower() in {"1", "true", "wahr", "richtig", "ja", "yes", "x"}

    def importiere(self, fragenkatalog):
        handle = TextIOWrapper(self.cleaned_data["datei"].file, encoding="utf-8-sig")
        reader = csv.DictReader(handle, delimiter=";")
        required_columns = {"typ", "fragetext"}
        missing_columns = required_columns.difference(reader.fieldnames or [])
        if missing_columns:
            raise forms.ValidationError("CSV-Spalten fehlen: " + ", ".join(sorted(missing_columns)))

        erstellt = 0
        valid_types = {choice[0] for choice in Frage.Typ.choices}
        for line_number, row in enumerate(reader, start=2):
            typ = (row.get("typ") or "").strip().upper()
            fragetext = (row.get("fragetext") or "").strip()
            if not typ and not fragetext:
                continue
            if typ not in valid_types:
                raise forms.ValidationError(f"Zeile {line_number}: Unbekannter Fragetyp '{typ}'.")
            if not fragetext:
                raise forms.ValidationError(f"Zeile {line_number}: Fragetext fehlt.")

            themen = {name.strip() for name in (row.get("thema") or row.get("themen") or "").split(",") if name.strip()}
            if not themen:
                thema_match = self.legacy_themen_prefix.match(fragetext)
                if thema_match:
                    themen = {thema_match.group("thema").strip()}
                    fragetext = fragetext[thema_match.end():].strip()

            frage = Frage.objects.create(
                fragenkatalog=fragenkatalog,
                typ=typ,
                fragetext=self._quill_from_html(fragetext),
                erklaerung=self._quill_from_html(row.get("erklaerung")),
                punkte=int(row.get("punkte") or 1),
                schwierigkeit=(row.get("schwierigkeit") or Frage.Schwierigkeit.MITTEL).strip().upper(),
            )
            if themen:
                tags = [
                    FragenTag.objects.get_or_create(name=name, organisation=fragenkatalog.organisation)[0]
                    for name in sorted(themen)
                ]
                frage.tags.set(tags)
            if frage.typ in [Frage.Typ.SINGLE_CHOICE, Frage.Typ.MULTIPLE_CHOICE, Frage.Typ.WAHR_FALSCH]:
                for index in range(1, 9):
                    antworttext = row.get(f"antwort_{index}", "").strip()
                    if antworttext:
                        Antwort.objects.create(
                            frage=frage,
                            antworttext=antworttext,
                            ist_korrekt=self._is_correct(row.get(f"korrekt_{index}")),
                            reihenfolge=index,
                        )
            elif frage.typ == Frage.Typ.ZUORDNUNG:
                for index in range(1, 6):
                    links = row.get(f"links_{index}", "").strip()
                    rechts = row.get(f"rechts_{index}", "").strip()
                    if links and rechts:
                        ZuordnungsPaar.objects.create(
                            frage=frage,
                            linkes_element=links,
                            rechtes_element=rechts,
                            reihenfolge=index,
                        )
            erstellt += 1
        return erstellt


class FreitextBewertungForm(forms.ModelForm):
    class Meta:
        model = TeilnehmerAntwort
        fields = ("freitext_punkte", "freitext_kommentar")


class PruefungsFreigabeForm(forms.Form):
    nutzer = forms.ModelChoiceField(queryset=get_user_model().objects.none(), label="Teilnehmer")

    def __init__(self, *args, pruefung=None, **kwargs):
        super().__init__(*args, **kwargs)
        if pruefung is not None:
            self.fields["nutzer"].queryset = get_user_model().objects.filter(
                profile__organisation=pruefung.organisation,
                profile__rolle=Rolle.LEARNER,
                profile__aktiv=True,
            ).distinct().order_by("last_name", "first_name", "username")
