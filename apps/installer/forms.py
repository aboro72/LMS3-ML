from django import forms


class InstallerForm(forms.Form):
    brand_name = forms.CharField(label="Name der Installation", max_length=120)
    domain = forms.CharField(
        label="Domain",
        max_length=255,
        help_text="Zum Beispiel lms.example.de. Für lokale Installation: localhost.",
    )
    database_url = forms.CharField(
        label="PostgreSQL-Verbindung",
        max_length=500,
        widget=forms.PasswordInput(render_value=True),
        help_text="Zum Beispiel postgres://lms:Passwort@127.0.0.1:5432/lms",
    )
    admin_username = forms.CharField(label="Admin-Benutzername", max_length=150)
    admin_email = forms.EmailField(label="Admin-E-Mail")
    admin_password = forms.CharField(label="Admin-Passwort", min_length=12, widget=forms.PasswordInput)
    email_host = forms.CharField(label="SMTP-Server", max_length=255, required=False)
    email_port = forms.IntegerField(label="SMTP-Port", min_value=1, max_value=65535, initial=587, required=False)
    email_user = forms.CharField(label="SMTP-Benutzer", max_length=255, required=False)
    email_password = forms.CharField(label="SMTP-Passwort", max_length=500, required=False, widget=forms.PasswordInput)
    email_from = forms.EmailField(label="Absender-E-Mail", required=False)

