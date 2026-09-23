from pathlib import Path

from django.contrib.messages import constants as messages
from decouple import Csv, config


BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = config("SECRET_KEY", default="django-insecure-change-me-in-production")
FIELD_ENCRYPTION_KEY = config("FIELD_ENCRYPTION_KEY", default="")
DEBUG = config("DEBUG", default=False, cast=bool)
ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="localhost,127.0.0.1", cast=Csv())

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "django_quill",
    "apps.accounts",
    "apps.organisations",
    "apps.courses",
    "apps.exams",
    "apps.payments",
    "apps.certificates",
    "apps.security",
    "apps.installer",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "apps.organisations.middleware.TenantRedirectMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.accounts.context_processors.rollen_context",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

AUTH_USER_MODEL = "accounts.User"

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

SITE_ID = 1
LOGIN_URL = "account_login"
LOGIN_REDIRECT_URL = "dashboard"
LOGOUT_REDIRECT_URL = config("LOGOUT_REDIRECT_URL", default="home")
SINGLE_SYSTEM_MODE = config("SINGLE_SYSTEM_MODE", default=True, cast=bool)
SINGLE_SYSTEM_BRAND_NAME = config("SINGLE_SYSTEM_BRAND_NAME", default="ML Gruppe")
SINGLE_SYSTEM_DOMAIN = config("SINGLE_SYSTEM_DOMAIN", default="ml-gruppe.de")
SINGLE_SYSTEM_ORGANISATION_SLUG = config("SINGLE_SYSTEM_ORGANISATION_SLUG", default="ml-gruppe")
SINGLE_SYSTEM_PRIMARY_COLOR = config("SINGLE_SYSTEM_PRIMARY_COLOR", default="#0c437b")
SINGLE_SYSTEM_SECONDARY_COLOR = config("SINGLE_SYSTEM_SECONDARY_COLOR", default="#2fb2bf")
SINGLE_SYSTEM_NAVBAR_COLOR = config("SINGLE_SYSTEM_NAVBAR_COLOR", default="#2b2e34")
SINGLE_SYSTEM_BACKGROUND_COLOR = config("SINGLE_SYSTEM_BACKGROUND_COLOR", default="#f9f9fb")
PAYMENTS_ENABLED = config("PAYMENTS_ENABLED", default=True, cast=bool)
PAYMENTS_ALLOW_SINGLE_SYSTEM = config("PAYMENTS_ALLOW_SINGLE_SYSTEM", default=False, cast=bool)
ACCOUNT_LOGIN_METHODS = {"email", "username"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "username*", "password1*", "password2*"]
ACCOUNT_EMAIL_VERIFICATION = "optional"
ACCOUNT_FORMS = {"login": "apps.accounts.forms.BootstrapLoginForm"}
ACCOUNT_ADAPTER = "apps.accounts.adapters.OrganisationAccountAdapter"

MESSAGE_TAGS = {
    messages.ERROR: "danger",
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "de"
TIME_ZONE = "Europe/Berlin"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

MEDIA_URL = config("MEDIA_URL", default="/media/")
MEDIA_ROOT = Path(config("MEDIA_ROOT", default=str(BASE_DIR / "media")))
MAX_VIDEO_UPLOAD_MB = config("MAX_VIDEO_UPLOAD_MB", default=500, cast=int)
MAX_DOCUMENT_UPLOAD_MB = config("MAX_DOCUMENT_UPLOAD_MB", default=50, cast=int)
MAX_IMAGE_UPLOAD_MB = config("MAX_IMAGE_UPLOAD_MB", default=10, cast=int)
ALLOWED_VIDEO_EXTENSIONS = config("ALLOWED_VIDEO_EXTENSIONS", default=".mp4,.webm,.mov,.m4v", cast=Csv())
ALLOWED_DOCUMENT_EXTENSIONS = config("ALLOWED_DOCUMENT_EXTENSIONS", default=".pdf,.doc,.docx,.ppt,.pptx,.xls,.xlsx,.txt,.zip", cast=Csv())
ALLOWED_IMAGE_EXTENSIONS = config("ALLOWED_IMAGE_EXTENSIONS", default=".jpg,.jpeg,.png,.webp,.svg", cast=Csv())

EMAIL_BACKEND = config(
    "EMAIL_BACKEND",
    default="django.core.mail.backends.console.EmailBackend",
)
DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default="noreply@aborosoft.de")

PLATFORM_COMMISSION_PERCENT = config("PLATFORM_COMMISSION_PERCENT", default=15, cast=int)
PAYMENT_DEMO_AUTOCONFIRM = config("PAYMENT_DEMO_AUTOCONFIRM", default=True, cast=bool)
DEMO_DATA_ALLOW_PRODUCTION = config("DEMO_DATA_ALLOW_PRODUCTION", default=False, cast=bool)
STRIPE_PUBLIC_KEY = config("STRIPE_PUBLIC_KEY", default="")
STRIPE_SECRET_KEY = config("STRIPE_SECRET_KEY", default="")
PAYPAL_CLIENT_ID = config("PAYPAL_CLIENT_ID", default="")
PAYPAL_SECRET = config("PAYPAL_SECRET", default="")

# Der Assistent wird ausschließlich durch den Bootstrap mit einem geheimen
# Token aktiviert und nach erfolgreicher Einrichtung wieder deaktiviert.
INSTALLER_ENABLED = config("INSTALLER_ENABLED", default=False, cast=bool)
INSTALLER_TOKEN = config("INSTALLER_TOKEN", default="")
REDIS_URL = config("REDIS_URL", default="redis://127.0.0.1:6379/0")
CELERY_BROKER_URL = config("CELERY_BROKER_URL", default=REDIS_URL)
CELERY_RESULT_BACKEND = config("CELERY_RESULT_BACKEND", default=REDIS_URL)

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
