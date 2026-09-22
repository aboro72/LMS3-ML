from django import forms

from apps.accounts.models import Rolle

from .models import (
    Einladung,
    Organisation,
    OrganisationDesign,
    OrganisationEmailKonfiguration,
    OrganisationStartseite,
)


RESERVIERTE_MANDANTEN_SLUGS = {"admin", "accounts", "kurse", "lernpfade", "trainer", "examiner", "pruefungen", "zahlungen", "rechnungen", "organisationen", "superadmin", "media", "static", "o", "dashboard", "hilfe"}


class OrganisationSignupForm(forms.ModelForm):
    class Meta:
        model = Organisation
        fields = ("name", "slug", "kontakt_email", "website", "weiterleitungs_url")

    def clean_slug(self):
        slug = self.cleaned_data["slug"].strip().lower()
        if slug in RESERVIERTE_MANDANTEN_SLUGS:
            raise forms.ValidationError("Dieser Slug ist fuer Systemseiten reserviert.")
        if Organisation.objects.filter(slug=slug).exists():
            raise forms.ValidationError("Dieser Slug ist bereits vergeben.")
        return slug


class EinladungForm(forms.Form):
    email = forms.EmailField(label="E-Mail-Adresse")
    rolle = forms.ChoiceField(
        choices=[
            (Rolle.EXAM_OPERATOR, "Prüfungsoperator"),
            (Rolle.TRAINER, "Trainer"),
            (Rolle.EXAMINER, "Prüfer"),
            (Rolle.LEARNER, "Lernender"),
        ],
        label="Rolle",
    )
    pruefung = forms.ModelChoiceField(
        queryset=None, required=False,
        label="Direkt zu einer Zertifikatspruefung anmelden",
        help_text="Optional. Nach Annahme der Einladung wird der Lernende sofort fuer diese Pruefung angemeldet.",
    )

    def __init__(self, *args, organisation=None, ist_trainer=False, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.exams.models import Pruefung
        self.fields["email"].widget.attrs["class"] = "form-control"
        self.fields["rolle"].widget.attrs["class"] = "form-select"
        self.fields["pruefung"].widget.attrs["class"] = "form-select"
        self.fields["pruefung"].queryset = Pruefung.objects.filter(
            organisation=organisation, ist_aktiv=True
        ).order_by("titel") if organisation else Pruefung.objects.none()
        if ist_trainer:
            self.fields["rolle"].choices = [(Rolle.LEARNER, "Lernender")]
            self.fields["rolle"].initial = Rolle.LEARNER

    def clean(self):
        data = super().clean()
        if data.get("pruefung") and data.get("rolle") != Rolle.LEARNER:
            self.add_error("rolle", "Eine Pruefungsanmeldung ist nur fuer Lernende moeglich.")
        return data


class OrganisationWeiterleitungForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from django.conf import settings
        if settings.SINGLE_SYSTEM_MODE:
            self.fields.pop("weiterleitungs_url", None)

    class Meta:
        model = Organisation
        fields = ["weiterleitungs_url"]
        widgets = {
            "weiterleitungs_url": forms.URLInput(attrs={"class": "form-control", "placeholder": "https://kunde.example/"}),
        }


class OrganisationEmailKonfigForm(forms.ModelForm):
    smtp_password = forms.CharField(
        widget=forms.PasswordInput(render_value=True, attrs={"class": "form-control", "autocomplete": "new-password"}),
        required=False,
        label="SMTP-Passwort",
        help_text="Leer lassen, um das gespeicherte Passwort beizubehalten.",
    )

    class Meta:
        model = OrganisationEmailKonfiguration
        fields = [
            "aktiv",
            "absender_name",
            "absender_email",
            "antwort_email",
            "smtp_host",
            "smtp_port",
            "smtp_user",
            "smtp_password",
            "smtp_use_tls",
            "smtp_use_ssl",
            "einladung_betreff",
            "einladung_text",
            "passwort_reset_betreff",
            "passwort_reset_text",
        ]
        widgets = {
            "aktiv": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "absender_name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Meine Firma Academy"}),
            "absender_email": forms.EmailInput(attrs={"class": "form-control", "placeholder": "academy@meinefirma.de"}),
            "antwort_email": forms.EmailInput(attrs={"class": "form-control", "placeholder": "support@meinefirma.de"}),
            "smtp_host": forms.TextInput(attrs={"class": "form-control", "placeholder": "smtp.gmail.com"}),
            "smtp_port": forms.NumberInput(attrs={"class": "form-control"}),
            "smtp_user": forms.TextInput(attrs={"class": "form-control", "placeholder": "academy@meinefirma.de"}),
            "smtp_use_tls": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "smtp_use_ssl": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "einladung_betreff": forms.TextInput(attrs={"class": "form-control"}),
            "einladung_text": forms.Textarea(attrs={"class": "form-control", "rows": 7}),
            "passwort_reset_betreff": forms.TextInput(attrs={"class": "form-control"}),
            "passwort_reset_text": forms.Textarea(attrs={"class": "form-control", "rows": 7}),
        }

    def clean(self):
        data = super().clean()
        if data.get("smtp_use_tls") and data.get("smtp_use_ssl"):
            raise forms.ValidationError(
                "TLS (Port 587) und SSL (Port 465) können nicht gleichzeitig aktiviert sein. "
                "Bitte wählen Sie nur eine Option."
            )
        return data

    def save(self, commit=True):
        instance = super().save(commit=False)
        # Passwort nur überschreiben wenn ein neues eingegeben wurde
        if not self.cleaned_data.get("smtp_password"):
            if instance.pk:
                instance.smtp_password = OrganisationEmailKonfiguration.objects.get(pk=instance.pk).smtp_password
        if commit:
            instance.save()
        return instance


class OrganisationDesignForm(forms.ModelForm):
    class Meta:
        model = OrganisationDesign
        fields = [
            "primary_color",
            "secondary_color",
            "navbar_farbe",
            "hintergrund_farbe",
            "logo",
            "favicon",
            "custom_css",
        ]
        widgets = {
            "primary_color": forms.TextInput(attrs={"type": "color", "class": "form-control form-control-color"}),
            "secondary_color": forms.TextInput(attrs={"type": "color", "class": "form-control form-control-color"}),
            "navbar_farbe": forms.TextInput(attrs={"type": "color", "class": "form-control form-control-color"}),
            "hintergrund_farbe": forms.TextInput(attrs={"type": "color", "class": "form-control form-control-color"}),
            "logo": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "favicon": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "custom_css": forms.Textarea(attrs={
                "class": "form-control font-monospace",
                "rows": 8,
                "placeholder": "/* Nur für erfahrene Nutzer */\n.course-card { border-radius: 0; }",
            }),
        }


class OrganisationStartseiteForm(forms.ModelForm):
    class Meta:
        model = OrganisationStartseite
        fields = [
            "aktiv",
            "hero_titel",
            "hero_untertitel",
            "hero_bild",
            "hero_button_text",
            "inhalt",
        ]
        widgets = {
            "aktiv": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "hero_titel": forms.TextInput(attrs={"class": "form-control", "placeholder": "Willkommen bei unserer Lernplattform"}),
            "hero_untertitel": forms.TextInput(attrs={"class": "form-control", "placeholder": "Starten Sie noch heute mit unseren Kursen."}),
            "hero_bild": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "hero_button_text": forms.TextInput(attrs={"class": "form-control"}),
        }
