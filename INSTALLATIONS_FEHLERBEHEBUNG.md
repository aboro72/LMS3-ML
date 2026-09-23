# Installations- und Proxy-Fehlerbehebung

Diese Anleitung gilt für Django 6.1.1 mit Python 3.12, 3.13 oder 3.14, PostgreSQL, Gunicorn, Redis/Celery und ISPConfig als Reverse Proxy.

## 1. Installer mit Bash starten

Nicht mit `sh` starten und Windows-Zeilenumbrüche entfernen:

```bash
sudo apt-get update
sudo apt-get install --reinstall -y bash dos2unix
sudo dos2unix /opt/aborolms/deploy/install-linux.sh
sudo chmod +x /opt/aborolms/deploy/install-linux.sh
```

Korrekte Ausführung:

```bash
sudo /bin/bash /opt/aborolms/deploy/install-linux.sh \
  --repo "https://github.com/aboro72/LMS3-ML.git" \
  --domain "lms-3.ml-projekt.de" \
  --db-pass "NICHT_IN_DOKUMENTATION_EINTRAGEN" \
  --unattended
```

Die Repo-URL muss eine reine URL sein. Nicht aus Chat-Markdown kopieren:

```text
Falsch: [https://example.org/repo.git](https://example.org/repo.git)
Richtig: https://example.org/repo.git
```

## 2. Python und Django prüfen

```bash
python3 --version
/opt/aborolms/.venv/bin/python --version
/opt/aborolms/.venv/bin/python -m django --version
```

Django 6.1.1 benötigt Python 3.12, 3.13 oder 3.14. Python 3.11 ist nicht ausreichend.

## 3. Fehlende Python-Pakete

Bei `ModuleNotFoundError`, zum Beispiel `reportlab`, immer die virtuelle Umgebung verwenden:

```bash
cd /opt/aborolms
sudo -u aborolms .venv/bin/python -m pip install -r requirements/production.txt
```

Einzelne Pakete können so nachinstalliert werden:

```bash
sudo -u aborolms .venv/bin/python -m pip install reportlab psycopg2-binary
```

Nicht das systemweite `pip` verwenden. Sonst erscheint häufig `externally-managed-environment`.

## 4. Alte `.env` verhindert PostgreSQL

Der Installer überschreibt eine vorhandene `.env` absichtlich nicht. Prüfe deshalb:

```bash
sudo grep '^DB_ENGINE=' /opt/aborolms/.env
```

Für PostgreSQL muss die Datei enthalten:

```env
DB_ENGINE=postgresql
DATABASE_URL=postgresql://BENUTZER:PASSWORT@127.0.0.1:5432/DATENBANK
```

Die aktive Datenbank kann geprüft werden:

```bash
cd /opt/aborolms
sudo -u aborolms env DJANGO_SETTINGS_MODULE=config.settings.production \
  .venv/bin/python -c \
  "from django.conf import settings; print(settings.DATABASES['default']['ENGINE'])"
```

Erwartet wird `django.db.backends.postgresql`.

## 5. Migrationen manuell ausführen

```bash
cd /opt/aborolms

sudo -u aborolms env DJANGO_SETTINGS_MODULE=config.settings.production \
  .venv/bin/python manage.py check

sudo -u aborolms env DJANGO_SETTINGS_MODULE=config.settings.production \
  .venv/bin/python manage.py migrate --noinput

sudo -u aborolms env DJANGO_SETTINGS_MODULE=config.settings.production \
  .venv/bin/python manage.py collectstatic --noinput
```

## 6. systemd-Service fehlt

Wenn `Unit aborolms.service not found` erscheint, ist der Installer vor Schritt 8 abgebrochen. Nach der Fehlerbehebung den Installer erneut vollständig ausführen.

```bash
sudo systemctl daemon-reload
sudo systemctl status aborolms --no-pager
sudo systemctl status aborolms-celery --no-pager
```

## 7. Gunicorn muss auf TCP-Port 8000 lauschen

Für einen entfernten ISPConfig-Reverse-Proxy darf Gunicorn nicht nur an einem Unix-Socket lauschen:

```bash
sudo grep -- '--bind' /etc/systemd/system/aborolms.service
```

Erwartet wird:

```text
--bind 0.0.0.0:8000
```

Falls noch ein Unix-Socket eingetragen ist:

```bash
sudo sed -i \
  's#--bind unix:/run/aborolms/gunicorn.sock#--bind 0.0.0.0:8000#' \
  /etc/systemd/system/aborolms.service

sudo systemctl daemon-reload
sudo systemctl restart aborolms
```

Prüfen:

```bash
sudo ss -ltnp | grep ':8000'
curl -i http://127.0.0.1:8000/
```

## 8. ISPConfig zeigt 502 Bad Gateway

Vom ISPConfig-Server testen:

```bash
curl -i \
  -H "Host: lms-3.ml-projekt.de" \
  http://192.168.0.101:8000/
```

Der ISPConfig-Upstream muss auf `http://192.168.0.101:8000` zeigen. Gültige Nginx-Direktiven sind:

```nginx
location / {
    proxy_pass http://192.168.0.101:8000;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_read_timeout 120s;
    proxy_connect_timeout 60s;
    client_max_body_size 500M;
}
```

Kein Markdown, keine Backslashes vor Unterstrichen und keine URL in eckigen Klammern eintragen. Danach:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

## 9. Django zeigt Bad Request (400)

In `/opt/aborolms/.env` müssen Domain und Proxy-Host erlaubt sein:

```env
ALLOWED_HOSTS=lms-3.ml-projekt.de,www.lms-3.ml-projekt.de,192.168.0.101,127.0.0.1,localhost
CSRF_TRUSTED_ORIGINS=https://lms-3.ml-projekt.de,http://lms-3.ml-projekt.de
TRUST_PROXY_SSL_HEADER=True
```

Falsch wären zum Beispiel `TRUST\_PROXY\_SSL\_HEADER` oder eine Markdown-URL bei `CSRF_TRUSTED_ORIGINS`.

Danach:

```bash
sudo systemctl restart aborolms
curl -i -H "Host: lms-3.ml-projekt.de" http://127.0.0.1:8000/
```

## 10. Installer zeigt 404

Der Installer liefert absichtlich 404, wenn er deaktiviert ist oder der Token nicht stimmt:

```env
INSTALLER_ENABLED=True
INSTALLER_TOKEN=NEUER_ZUFÄLLIGER_TOKEN
```

Nach Änderung:

```bash
sudo systemctl restart aborolms
```

Nach erfolgreicher Installation wird der Installer automatisch deaktiviert. Installer-Tokens niemals in Tickets, Screenshots oder Chatverläufen weitergeben.

## 11. Logs

```bash
sudo systemctl status aborolms --no-pager
sudo journalctl -u aborolms -n 100 --no-pager
sudo journalctl -u aborolms-celery -n 100 --no-pager
sudo nginx -t
```

Immer zuerst den ersten Fehler beheben. Folgefehler wie ein fehlendes `collectstatic` entstehen häufig nur, weil Django vorher wegen einer Paket-, Datenbank- oder Host-Konfiguration nicht starten konnte.

