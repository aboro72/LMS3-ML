from django import forms

from .models import OrganisationZahlungseinstellungen, Zahlungsart, Zahlungseinstellungen


class CheckoutForm(forms.Form):
    zahlungsart = forms.ChoiceField(
        choices=Zahlungsart.choices,
        widget=forms.RadioSelect,
        label="Zahlungsart",
    )

    def __init__(self, *args, payment_settings=None, **kwargs):
        super().__init__(*args, **kwargs)
        if payment_settings:
            self.fields["zahlungsart"].choices = payment_settings.aktive_zahlungsarten()


class PaymentSwitchForm(forms.ModelForm):
    class Meta:
        model = Zahlungseinstellungen
        fields = ("payment_aktiv",)


class OrganisationZahlungseinstellungenForm(forms.ModelForm):
    class Meta:
        model = OrganisationZahlungseinstellungen
        fields = ("payment_aktiv", "stripe_aktiv", "stripe_public_key", "stripe_secret_key", "paypal_aktiv", "paypal_client_id", "paypal_secret", "ueberweisung_aktiv", "kontoinhaber", "iban", "bic", "bankname")
        widgets = {
            "payment_aktiv": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "stripe_aktiv": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "paypal_aktiv": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "ueberweisung_aktiv": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "stripe_public_key": forms.TextInput(attrs={"class": "form-control"}),
            "stripe_secret_key": forms.PasswordInput(render_value=True, attrs={"class": "form-control"}),
            "paypal_client_id": forms.TextInput(attrs={"class": "form-control"}),
            "paypal_secret": forms.PasswordInput(render_value=True, attrs={"class": "form-control"}),
            "kontoinhaber": forms.TextInput(attrs={"class": "form-control"}), "iban": forms.TextInput(attrs={"class": "form-control"}), "bic": forms.TextInput(attrs={"class": "form-control"}), "bankname": forms.TextInput(attrs={"class": "form-control"}),
        }
