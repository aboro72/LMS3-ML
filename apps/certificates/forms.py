from django import forms

from .models import ZertifikatDesign


class ZertifikatDesignForm(forms.ModelForm):
    class Meta:
        model = ZertifikatDesign
        fields = ["primary_color", "secondary_color", "org_display_name", "footer_text", "signature_line", "unterschrift_1", "unterschrift_2", "logo"]
        widgets = {
            "primary_color": forms.TextInput(attrs={"type": "color", "class": "form-control form-control-color"}),
            "secondary_color": forms.TextInput(attrs={"type": "color", "class": "form-control form-control-color"}),
            "org_display_name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Leer = Organisationsname"}),
            "footer_text": forms.TextInput(attrs={"class": "form-control", "placeholder": "z.B. Diese Zertifizierung wurde von Muster GmbH ausgestellt."}),
            "signature_line": forms.TextInput(attrs={"class": "form-control", "placeholder": "z.B. Geschäftsführung"}),
            "unterschrift_1": forms.ClearableFileInput(attrs={"class": "form-control", "accept": "image/png,image/jpeg"}),
            "unterschrift_2": forms.ClearableFileInput(attrs={"class": "form-control", "accept": "image/png,image/jpeg"}),
            "logo": forms.ClearableFileInput(attrs={"class": "form-control"}),
        }
        labels = {
            "primary_color": "Hauptfarbe (Rahmen, Titel)",
            "secondary_color": "Akzentfarbe (Name, Divider, Ecken)",
            "org_display_name": "Anzeigename im Zertifikat",
            "footer_text": "Zusätzlicher Fußzeilentext",
            "signature_line": "Unterschriftenzeile",
            "unterschrift_1": "Unterschrift 1",
            "unterschrift_2": "Unterschrift 2",
            "logo": "Logo (wird oben im Zertifikat angezeigt)",
        }
