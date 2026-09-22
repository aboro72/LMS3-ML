from django.conf import settings
from django.core.checks import Error, Warning, register

from .crypto import get_field_fernet


@register()
def field_encryption_key_check(app_configs, **kwargs):
    key = getattr(settings, "FIELD_ENCRYPTION_KEY", "")
    if not key:
        if getattr(settings, "DEBUG", False):
            return [Warning(
                "FIELD_ENCRYPTION_KEY ist nicht gesetzt. Verschluesselte Felder koennen nicht produktiv genutzt werden.",
                id="aborolms.W001",
            )]
        return [Error(
            "FIELD_ENCRYPTION_KEY muss in Produktion gesetzt sein.",
            id="aborolms.E001",
        )]
    try:
        get_field_fernet()
    except Exception as exc:
        return [Error(str(exc), id="aborolms.E002")]
    return []

@register(deploy=True)
def production_readiness_check(app_configs, **kwargs):
    issues = []
    if not getattr(settings, "PRODUCTION", False):
        issues.append(Error("Produktionspruefung mit --settings=config.settings.production ausfuehren.", id="aborolms.E010"))
    if settings.FIELD_ENCRYPTION_KEY == "j3BQv31KKjfteqM5y4LTfhQf3ru51qCz_02cxydQaDI=":
        issues.append(Error("Der oeffentliche Entwicklungs-Key darf nicht produktiv verwendet werden.", id="aborolms.E011"))
    if "*" in settings.ALLOWED_HOSTS or not settings.ALLOWED_HOSTS or all(
        host in {"localhost", "127.0.0.1", "[::1]"} for host in settings.ALLOWED_HOSTS
    ):
        issues.append(Error("ALLOWED_HOSTS muss die konkreten Produktionsdomains enthalten.", id="aborolms.E012"))
    if settings.EMAIL_BACKEND in {
        "django.core.mail.backends.console.EmailBackend",
        "django.core.mail.backends.locmem.EmailBackend",
        "django.core.mail.backends.dummy.EmailBackend",
        "django.core.mail.backends.filebased.EmailBackend",
    }:
        issues.append(Warning("Kein produktiver E-Mail-Versand konfiguriert.", id="aborolms.W010"))
    elif settings.EMAIL_BACKEND == "django.core.mail.backends.smtp.EmailBackend" and not settings.EMAIL_HOST:
        issues.append(Error("SMTP-Backend benoetigt EMAIL_HOST.", id="aborolms.E013"))
    if settings.EMAIL_USE_TLS and settings.EMAIL_USE_SSL:
        issues.append(Error("EMAIL_USE_TLS und EMAIL_USE_SSL nicht gleichzeitig aktivieren.", id="aborolms.E014"))
    if settings.DATABASES["default"]["ENGINE"] == "django.db.backends.sqlite3":
        issues.append(Warning("SQLite: Nebenlaeufigkeit und Backup auf dem Ziel-Datenbanksystem pruefen.", id="aborolms.W011"))
    return issues
