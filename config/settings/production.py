import dj_database_url

from .base import *  # noqa: F403

DEBUG = False
PRODUCTION = True
# Statische Dateien in der Produktion direkt über die Django-Anwendung
# ausliefern; der ISPConfig-Proxy muss keinen lokalen Dateipfad kennen.
MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")  # noqa: F405
PAYMENT_DEMO_AUTOCONFIRM = False
PAYMENTS_ENABLED = config("PAYMENTS_ENABLED", default=False, cast=bool)  # noqa: F405
PAYMENTS_ALLOW_SINGLE_SYSTEM = config("PAYMENTS_ALLOW_SINGLE_SYSTEM", default=False, cast=bool)  # noqa: F405
SINGLE_SYSTEM_MODE = config("SINGLE_SYSTEM_MODE", default=True, cast=bool)  # noqa: F405
SINGLE_SYSTEM_ORGANISATION_SLUG = config("SINGLE_SYSTEM_ORGANISATION_SLUG", default="ml-gruppe")  # noqa: F405

# --------------------------------------------------------------------------- #
# Datenbankmotor
# DB_ENGINE: postgresql | mysql | mssql
# --------------------------------------------------------------------------- #
DB_ENGINE = config("DB_ENGINE", default="postgresql")  # noqa: F405

if DB_ENGINE == "mssql":
    DATABASES = {
        "default": {
            "ENGINE": "mssql",
            "NAME": config("DB_NAME"),  # noqa: F405
            "USER": config("DB_USER"),  # noqa: F405
            "PASSWORD": config("DB_PASSWORD"),  # noqa: F405
            "HOST": config("DB_HOST", default="localhost"),  # noqa: F405
            "PORT": config("DB_PORT", default="1433"),  # noqa: F405
            "OPTIONS": {
                "driver": "ODBC Driver 17 for SQL Server",
                "unicode_results": True,
            },
        }
    }
elif DB_ENGINE == "mysql":
    # PyMySQL als reines Python-Fallback, falls mysqlclient nicht kompiliert
    try:
        import MySQLdb  # noqa: F401 – mysqlclient vorhanden
    except ImportError:
        import pymysql
        pymysql.install_as_MySQLdb()
    DATABASES = {
        "default": dj_database_url.config(
            default=config("DATABASE_URL"),  # noqa: F405
            conn_max_age=600,
        )
    }
else:
    # postgresql (Standard)
    database_url = config("DATABASE_URL", default="")  # noqa: F405
    if database_url:
        DATABASES = {"default": dj_database_url.config(default=database_url, conn_max_age=600)}
    elif INSTALLER_ENABLED:  # noqa: F405
        # Temporäre Datenbank für den Web-Assistenten. Nach dem Speichern der
        # PostgreSQL-Verbindung führt der Assistent Migrationen neu aus.
        DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "installer.sqlite3"}}  # noqa: F405
    else:
        raise RuntimeError("DATABASE_URL fehlt. PostgreSQL-Verbindung in .env konfigurieren.")

CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True
CSRF_TRUSTED_ORIGINS = config(
    "CSRF_TRUSTED_ORIGINS",
    default=",".join(
        f"https://{host}"
        for host in ALLOWED_HOSTS  # noqa: F405
        if host not in {"localhost", "127.0.0.1"}
    ),
    cast=Csv(),  # noqa: F405
)
SECURE_SSL_REDIRECT = config("SECURE_SSL_REDIRECT", default=True, cast=bool)  # noqa: F405
ALLAUTH_TRUSTED_PROXY_COUNT = config("ALLAUTH_TRUSTED_PROXY_COUNT", default=1, cast=int)  # noqa: F405

if config("AWS_STORAGE_BUCKET_NAME", default=""):  # noqa: F405
    INSTALLED_APPS += ["storages"]  # noqa: F405
    STORAGES = {
        "default": {"BACKEND": "storages.backends.s3.S3Storage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
    AWS_ACCESS_KEY_ID = config("AWS_ACCESS_KEY_ID", default="")  # noqa: F405
    AWS_SECRET_ACCESS_KEY = config("AWS_SECRET_ACCESS_KEY", default="")  # noqa: F405
    AWS_STORAGE_BUCKET_NAME = config("AWS_STORAGE_BUCKET_NAME")  # noqa: F405

if not config("AWS_STORAGE_BUCKET_NAME", default=""):  # noqa: F405
    STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
        },
    }

# Erst nach HTTPS-Pruefung auf einen laengeren Zeitraum erhoehen.
SECURE_HSTS_SECONDS = config("SECURE_HSTS_SECONDS", default=3600, cast=int)
SECURE_HSTS_INCLUDE_SUBDOMAINS = config("SECURE_HSTS_INCLUDE_SUBDOMAINS", default=False, cast=bool)
SECURE_HSTS_PRELOAD = config("SECURE_HSTS_PRELOAD", default=False, cast=bool)
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
# Nur aktivieren, wenn der vorgeschaltete Proxy den Header ueberschreibt
# und die Anwendung nicht direkt aus dem Internet erreichbar ist.
if config("TRUST_PROXY_SSL_HEADER", default=False, cast=bool):
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

EMAIL_HOST = config("EMAIL_HOST", default="")
EMAIL_PORT = config("EMAIL_PORT", default=587, cast=int)
EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = config("EMAIL_USE_TLS", default=True, cast=bool)
EMAIL_USE_SSL = config("EMAIL_USE_SSL", default=False, cast=bool)
EMAIL_TIMEOUT = 15
