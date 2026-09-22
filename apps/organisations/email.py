from django.conf import settings
from django.core.mail import EmailMultiAlternatives


def fuelle_emailvorlage(vorlage, **werte):
    for schluessel, wert in werte.items():
        vorlage = vorlage.replace("{{ " + schluessel + " }}", str(wert or ""))
    return vorlage


def sende_org_email(organisation, betreff, text_nachricht, empfaenger, html_nachricht=None):
    """
    Versendet eine E-Mail über den SMTP-Server der Organisation (falls konfiguriert)
    oder den Plattform-Standard-SMTP.

    empfaenger: str oder list[str]
    """
    if isinstance(empfaenger, str):
        empfaenger = [empfaenger]

    email_config = None
    if organisation is not None:
        try:
            email_config = organisation.email_konfiguration
        except Exception:
            pass

    if email_config and email_config.aktiv and email_config.smtp_host:
        from_email = email_config.get_from_email() or settings.DEFAULT_FROM_EMAIL
        reply_to = [email_config.antwort_email] if email_config.antwort_email else None
        connection = email_config.get_connection()
    else:
        from_email = settings.DEFAULT_FROM_EMAIL
        reply_to = None
        connection = None

    msg = EmailMultiAlternatives(
        subject=betreff,
        body=text_nachricht,
        from_email=from_email,
        to=empfaenger,
        reply_to=reply_to,
        connection=connection,
    )
    if html_nachricht:
        msg.attach_alternative(html_nachricht, "text/html")

    msg.send()
