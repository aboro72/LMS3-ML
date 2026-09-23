import hmac
import json
import os
import subprocess
import sys
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.http import Http404
from django.shortcuts import redirect, render
from django.utils.crypto import get_random_string
from django.views import View
from cryptography.fernet import Fernet

from .forms import InstallerForm


class InstallerView(View):
    template_name = "installer/index.html"

    def dispatch(self, request, *args, **kwargs):
        configured_token = getattr(settings, "INSTALLER_TOKEN", "")
        supplied_token = kwargs.get("token", "")
        if not getattr(settings, "INSTALLER_ENABLED", False) or not configured_token:
            raise Http404("Installationsassistent ist deaktiviert.")
        if not hmac.compare_digest(str(supplied_token), str(configured_token)):
            raise Http404("Ungültiger Installationsschlüssel.")
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name, {"form": self._initial_form()})

    def post(self, request, *args, **kwargs):
        form = InstallerForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {"form": form})

        try:
            env_path = self._write_environment(form.cleaned_data)
            self._run_migrations(env_path)
            self._create_admin(form.cleaned_data, env_path)
        except (OSError, subprocess.CalledProcessError, RuntimeError) as exc:
            form.add_error(None, f"Installation konnte nicht abgeschlossen werden: {exc}")
            return render(request, self.template_name, {"form": form})

        self._disable_installer(env_path)
        messages.success(request, "Installation abgeschlossen. Bitte melde dich mit dem neuen Admin-Konto an.")
        return redirect("account_login")

    @staticmethod
    def _initial_form():
        return InstallerForm(initial={
            "brand_name": getattr(settings, "SINGLE_SYSTEM_BRAND_NAME", "ML Gruppe"),
            "domain": getattr(settings, "SINGLE_SYSTEM_DOMAIN", "localhost"),
            "database_url": os.environ.get("DATABASE_URL", "postgres://lms:CHANGE_ME@127.0.0.1:5432/lms"),
            "email_port": 587,
        })

    @staticmethod
    def _env_path():
        return Path(settings.BASE_DIR) / ".env"

    def _write_environment(self, values):
        env_path = self._env_path()
        existing = env_path.read_text(encoding="utf-8") if env_path.exists() else ""
        generated = {
            "SECRET_KEY": os.environ.get("SECRET_KEY") or get_random_string(64),
            "FIELD_ENCRYPTION_KEY": os.environ.get("FIELD_ENCRYPTION_KEY") or Fernet.generate_key().decode(),
            "DEBUG": "False",
            "PRODUCTION": "True",
            "SINGLE_SYSTEM_MODE": "True",
            "SINGLE_SYSTEM_BRAND_NAME": values["brand_name"],
            "SINGLE_SYSTEM_DOMAIN": values["domain"],
            "ALLOWED_HOSTS": values["domain"],
            "CSRF_TRUSTED_ORIGINS": f"https://{values['domain']}" if values["domain"] != "localhost" else "",
            "DB_ENGINE": "postgresql",
            "DATABASE_URL": values["database_url"],
            "EMAIL_BACKEND": "django.core.mail.backends.smtp.EmailBackend" if values["email_host"] else "django.core.mail.backends.console.EmailBackend",
            "EMAIL_HOST": values["email_host"],
            "EMAIL_PORT": values["email_port"] or 587,
            "EMAIL_HOST_USER": values["email_user"],
            "EMAIL_HOST_PASSWORD": values["email_password"],
            "DEFAULT_FROM_EMAIL": values["email_from"] or f"noreply@{values['domain']}",
            "REDIS_URL": os.environ.get("REDIS_URL", "redis://127.0.0.1:6379/0"),
            "PAYMENTS_ENABLED": "False",
            "PAYMENTS_ALLOW_SINGLE_SYSTEM": "False",
            "INSTALLER_ENABLED": "False",
            "INSTALLER_TOKEN": "",
        }
        lines = existing.splitlines()
        for key, value in generated.items():
            replacement = f"{key}={value}"
            found = False
            for index, line in enumerate(lines):
                if line.startswith(f"{key}="):
                    lines[index] = replacement
                    found = True
                    break
            if not found:
                lines.append(replacement)
        env_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
        if os.name != "nt":
            env_path.chmod(0o640)
        return env_path

    @staticmethod
    def _run_migrations(env_path):
        environment = os.environ.copy()
        environment["DJANGO_SETTINGS_MODULE"] = "config.settings.production"
        environment["INSTALLER_ENABLED"] = "False"
        result = subprocess.run(
            [sys.executable, str(Path(settings.BASE_DIR) / "manage.py"), "migrate", "--noinput"],
            cwd=settings.BASE_DIR,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode:
            raise RuntimeError(result.stderr[-2000:] or result.stdout[-2000:])

    @staticmethod
    def _create_admin(values, env_path):
        environment = os.environ.copy()
        environment["DJANGO_SETTINGS_MODULE"] = "config.settings.production"
        code = (
            "from apps.accounts.models import User; "
            f"u, _ = User.objects.get_or_create(username={json.dumps(values['admin_username'])}, defaults={{'email': {json.dumps(values['admin_email'])}}}); "
            f"u.email={json.dumps(values['admin_email'])}; u.is_staff=True; u.is_superuser=True; u.set_password({json.dumps(values['admin_password'])}); u.save()"
        )
        result = subprocess.run(
            [sys.executable, str(Path(settings.BASE_DIR) / "manage.py"), "shell", "-c", code],
            cwd=settings.BASE_DIR,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode:
            raise RuntimeError(result.stderr[-2000:] or result.stdout[-2000:])

    @staticmethod
    def _disable_installer(env_path):
        lines = env_path.read_text(encoding="utf-8").splitlines()
        for index, line in enumerate(lines):
            if line.startswith("INSTALLER_ENABLED="):
                lines[index] = "INSTALLER_ENABLED=False"
            if line.startswith("INSTALLER_TOKEN="):
                lines[index] = "INSTALLER_TOKEN="
        env_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")

