from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError

from .models import User


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)
    geburtsdatum = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))

    class Meta:
        model = User
        fields = ("username", "email", "first_name", "last_name", "geburtsdatum", "geburtsort", "password1", "password2")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({"class": "form-control"})

    def save(self, commit=True):
        user = super().save(commit=False)
        user.geburtsdatum = self.cleaned_data.get("geburtsdatum").isoformat() if self.cleaned_data.get("geburtsdatum") else ""
        if commit:
            user.save()
        return user


class ProfilForm(forms.ModelForm):
    geburtsdatum = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}))

    class Meta:
        model = User
        fields = ("first_name", "last_name", "geburtsdatum", "geburtsort")
        widgets = {"first_name": forms.TextInput(attrs={"class": "form-control"}), "last_name": forms.TextInput(attrs={"class": "form-control"}), "geburtsort": forms.TextInput(attrs={"class": "form-control"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.geburtsdatum:
            self.initial["geburtsdatum"] = self.instance.geburtsdatum

    def save(self, commit=True):
        user = super().save(commit=False)
        user.geburtsdatum = self.cleaned_data.get("geburtsdatum").isoformat() if self.cleaned_data.get("geburtsdatum") else ""
        if commit:
            user.save()
        return user


from allauth.account.forms import LoginForm as AllauthLoginForm


class BootstrapLoginForm(AllauthLoginForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["login"].widget.attrs.update({"class": "form-control"})
        self.fields["password"].widget.attrs.update({"class": "form-control"})
        self.fields["remember"].widget.attrs.update({"class": "form-check-input"})

    def clean_login(self):
        login = super().clean_login()
        aliases = {
            "super-admin": "superadmin",
            "superadmin": "superadmin",
            "org-admin": "orgadmin",
            "orgadmin": "orgadmin",
            "trainer": "trainer",
            "pruefer": "examiner",
            "prüfer": "examiner",
            "examiner": "examiner",
            "lernender": "learner",
            "learner": "learner",
        }
        return aliases.get(login.casefold(), login)

    def clean_password(self):
        password = self.cleaned_data["password"]
        return password.strip()


class OrganisationLoginForm(BootstrapLoginForm):
    def clean(self):
        cleaned_data = super().clean()
        organisation = getattr(self.request, "tenant_org", None)
        if organisation and getattr(self, "user", None) and not (
            self.user.is_superuser
            or self.user.profile.filter(organisation=organisation, aktiv=True).exists()
        ):
            raise ValidationError("Dieses Konto ist für diese Organisation nicht freigeschaltet.")
        return cleaned_data
