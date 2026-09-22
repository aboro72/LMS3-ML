from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from cryptography.fernet import Fernet, InvalidToken

ENCRYPTION_PREFIX = "enc:v1:"


def generate_field_encryption_key():
    return Fernet.generate_key().decode("ascii")


def get_field_fernet():
    key = getattr(settings, "FIELD_ENCRYPTION_KEY", "")
    if not key:
        raise ImproperlyConfigured("FIELD_ENCRYPTION_KEY ist nicht gesetzt.")
    try:
        return Fernet(key.encode("ascii") if isinstance(key, str) else key)
    except Exception as exc:
        raise ImproperlyConfigured("FIELD_ENCRYPTION_KEY ist kein gueltiger Fernet-Key.") from exc


def is_encrypted_value(value):
    return isinstance(value, str) and value.startswith(ENCRYPTION_PREFIX)


def encrypt_text(value):
    if value in (None, ""):
        return value
    if is_encrypted_value(value):
        return value
    token = get_field_fernet().encrypt(str(value).encode("utf-8")).decode("ascii")
    return f"{ENCRYPTION_PREFIX}{token}"


def decrypt_text(value):
    if value in (None, ""):
        return value
    if not is_encrypted_value(value):
        return value
    token = value[len(ENCRYPTION_PREFIX):]
    try:
        return get_field_fernet().decrypt(token.encode("ascii")).decode("utf-8")
    except InvalidToken as exc:
        raise ImproperlyConfigured("Verschluesselter Wert kann mit FIELD_ENCRYPTION_KEY nicht entschluesselt werden.") from exc