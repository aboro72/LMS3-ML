from .base import *  # noqa: F403


DEBUG = True

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",  # noqa: F405
    }
}

# Nur fuer lokale Entwicklung. Produktion muss FIELD_ENCRYPTION_KEY aus .env setzen.
FIELD_ENCRYPTION_KEY = config(
    "FIELD_ENCRYPTION_KEY",
    default="j3BQv31KKjfteqM5y4LTfhQf3ru51qCz_02cxydQaDI=",
)  # noqa: F405