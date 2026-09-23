#!/usr/bin/env bash
# =============================================================================
# ABoroLMS – Linux-Installationsskript (Debian / Ubuntu)
#
# Verwendung:
#   sudo bash install-linux.sh [OPTIONEN]
#
# Optionen:
#   --webserver  nginx|apache2      Webserver (Standard: nginx)
#   --db         postgresql|mysql          Datenbank (Standard: postgresql)
#   --repo       <git-url>          GitHub-Repository-URL
#   --domain     <hostname>         Domain der Anwendung (Standard: localhost)
#   --db-pass    <passwort>         DB-Passwort (wird generiert wenn leer)
#   --unattended                       Keine Rückfrage anzeigen
#   --with-postfix                     Lokalen Postfix-Mailserver installieren
#
# Beispiele:
#   sudo bash install-linux.sh
#   sudo bash install-linux.sh --webserver apache2 --db mysql
#   sudo bash install-linux.sh --db mongodb --domain lms.firma.de
#   sudo bash install-linux.sh --repo https://github.com/USER/LMS.git --db postgresql
#
# Voraussetzungen:
#   - Debian 12 / Ubuntu 22.04 oder neuer
#   - Root-Rechte (sudo)
#   - Internetverbindung
# =============================================================================
set -eu
# pipefail ist für Bash sinnvoll, aber nicht auf jedem Minimal-System
# verfügbar. Der Installer bleibt auch ohne diese optionale Erweiterung
# lauffähig.
set -o pipefail 2>/dev/null || true

# --------------------------------------------------------------------------- #
# Standardwerte
# --------------------------------------------------------------------------- #
WEBSERVER="nginx"
DB="postgresql"
REPO_URL="https://github.com/YOUR_USERNAME/LMS.git"
APP_DIR="/opt/aborolms"
APP_USER="aborolms"
PYTHON_VERSION=""
PYTHON_COMMAND=""
DB_NAME="aborolms"
DB_USER="aborolms"
DB_PASS=""
DOMAIN="localhost"
UNATTENDED=false
WITH_POSTFIX=false
INSTALLER_TOKEN="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"

# --------------------------------------------------------------------------- #
# Argumente parsen
# --------------------------------------------------------------------------- #
while [[ $# -gt 0 ]]; do
  case "$1" in
    --webserver) WEBSERVER="$2"; shift 2 ;;
    --db)        DB="$2";        shift 2 ;;
    --repo)      REPO_URL="$2";  shift 2 ;;
    --domain)    DOMAIN="$2";    shift 2 ;;
    --db-pass)   DB_PASS="$2";   shift 2 ;;
    --unattended) UNATTENDED=true; shift ;;
    --with-postfix) WITH_POSTFIX=true; shift ;;
    *) echo "Unbekanntes Argument: $1"; exit 1 ;;
  esac
done

# Validierung
case "$WEBSERVER" in nginx|apache2) ;; *)
  echo "Fehler: --webserver muss 'nginx' oder 'apache2' sein."; exit 1 ;;
esac
case "$DB" in postgresql|mysql) ;; *)
  echo "Fehler: --db muss 'postgresql' oder 'mysql' sein."; exit 1 ;;
esac

# Passwort generieren wenn nicht angegeben (für postgresql und mysql)
if [[ -z "$DB_PASS" && "$DB" != "mongodb" ]]; then
  DB_PASS="$(openssl rand -base64 32 | tr -d '/+=\n' | head -c 32)"
fi

SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_urlsafe(50))')"

# --------------------------------------------------------------------------- #
# Zusammenfassung
# --------------------------------------------------------------------------- #
echo "========================================================"
echo " ABoroLMS – Linux-Installer"
echo "========================================================"
echo " Webserver : $WEBSERVER"
echo " Datenbank : $DB"
echo " Repo      : $REPO_URL"
echo " Appdir    : $APP_DIR"
echo " Domain    : $DOMAIN"
echo "========================================================"
if [[ "$UNATTENDED" != true ]]; then
  read -rp "Fortfahren? [j/N] " CONFIRM
  [[ "$CONFIRM" =~ ^[jJ]$ ]] || exit 0
fi

# --------------------------------------------------------------------------- #
# Hilfsfunktion: Paket installieren
# --------------------------------------------------------------------------- #
apt_install() { apt-get install -y --no-install-recommends "$@"; }

# ===========================================================================#
# SCHRITT 1 – System-Pakete                                                   #
# ===========================================================================#
echo ""
echo "[1/9] System-Pakete aktualisieren..."
apt-get update -qq

# Python-Version aus den tatsächlich verfügbaren Debian/Ubuntu-Paketquellen
# wählen. Django 6.1.1 unterstützt Python 3.12, 3.13 und 3.14.
for candidate in 3.14 3.13 3.12; do
  if apt-cache show "python${candidate}-venv" >/dev/null 2>&1 && \
     apt-cache show "python${candidate}-dev" >/dev/null 2>&1; then
    PYTHON_VERSION="$candidate"
    PYTHON_COMMAND="python${candidate}"
    break
  fi
done

if [[ -z "$PYTHON_COMMAND" ]] && command -v python3 >/dev/null 2>&1; then
  PYTHON_COMMAND="python3"
  PYTHON_VERSION="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
  if [[ "$(python3 -c 'import sys; print(sys.version_info < (3, 12))')" == "True" ]]; then
    echo "Fehler: Django 6.1.1 benötigt Python 3.12, 3.13 oder 3.14; gefunden wurde $PYTHON_VERSION."
    exit 1
  fi
fi

if [[ -z "$PYTHON_COMMAND" ]]; then
  echo "Fehler: Keine unterstützte Python-Version gefunden. Django 6.1.1 benötigt Python 3.12, 3.13 oder 3.14 mit venv und dev-Paket."
  exit 1
fi

echo "  Python: $PYTHON_COMMAND ($PYTHON_VERSION)"

# Basis-Pakete (immer benötigt)
apt_install \
  "$PYTHON_COMMAND" \
  "${PYTHON_COMMAND}-venv" \
  "${PYTHON_COMMAND}-dev" \
  python3-pip \
  build-essential \
  git \
  curl \
  libffi-dev \
  shared-mime-info \
  libpango-1.0-0 \
  libpangoft2-1.0-0 \
  libpangocairo-1.0-0 \
  libcairo2 \
  libgdk-pixbuf2.0-0 \
  redis-server \
  "$WEBSERVER"

if [[ "$WITH_POSTFIX" == true ]]; then
  apt_install postfix
fi

# Datenbankspezifische Pakete
case "$DB" in
  postgresql)
    apt_install postgresql postgresql-contrib libpq-dev
    ;;
  mysql)
    apt_install mariadb-server libmariadb-dev pkg-config
    ;;
  mongodb)
    # MongoDB GPG-Key und Repository einrichten (Community Edition)
    if ! command -v mongod &>/dev/null; then
      curl -fsSL https://www.mongodb.org/static/pgp/server-7.0.asc \
        | gpg --dearmor -o /usr/share/keyrings/mongodb-server-7.0.gpg
      echo "deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg ] \
https://repo.mongodb.org/apt/ubuntu $(lsb_release -cs)/mongodb-org/7.0 multiverse" \
        > /etc/apt/sources.list.d/mongodb-org-7.0.list
      apt-get update -qq
      apt_install mongodb-org
    fi
    ;;
esac

# ===========================================================================#
# SCHRITT 2 – System-Nutzer                                                   #
# ===========================================================================#
echo ""
echo "[2/9] System-Nutzer '$APP_USER' anlegen..."
id "$APP_USER" &>/dev/null || useradd --system --shell /usr/sbin/nologin --home "$APP_DIR" "$APP_USER"

# ===========================================================================#
# SCHRITT 3 – Repository                                                      #
# ===========================================================================#
echo ""
echo "[3/9] Repository klonen / aktualisieren..."
if [[ -d "$APP_DIR/.git" ]]; then
  sudo -u "$APP_USER" git -C "$APP_DIR" pull --ff-only
else
  mkdir -p "$APP_DIR"
  git clone "$REPO_URL" "$APP_DIR"
  chown -R "$APP_USER:$APP_USER" "$APP_DIR"
fi

# ===========================================================================#
# SCHRITT 4 – Python-Virtualenv und Abhängigkeiten                            #
# ===========================================================================#
echo ""
echo "[4/9] Python-Virtualenv und Abhängigkeiten installieren..."
sudo -u "$APP_USER" "$PYTHON_COMMAND" -m venv "$APP_DIR/.venv"
PIP="$APP_DIR/.venv/bin/pip"

sudo -u "$APP_USER" "$PIP" install --upgrade pip
sudo -u "$APP_USER" "$PIP" install -r "$APP_DIR/requirements/production.txt"
sudo -u "$APP_USER" "$PIP" install gunicorn

# Datenbankspezifische Python-Pakete
case "$DB" in
  postgresql)
    sudo -u "$APP_USER" "$PIP" install "psycopg2-binary>=2.9"
    ;;
  mysql)
    # mysqlclient (C-Extension, benötigt libmariadb-dev)
    sudo -u "$APP_USER" "$PIP" install "mysqlclient>=2.1" || \
      sudo -u "$APP_USER" "$PIP" install "PyMySQL>=1.1" cryptography
    ;;
  mongodb)
    # django-mongodb-backend (experimentell, Django 6 Unterstützung in Entwicklung)
    sudo -u "$APP_USER" "$PIP" install "django-mongodb-backend" "pymongo>=4.6"
    echo "  HINWEIS: MongoDB-Unterstützung in Django 6 ist experimentell."
    echo "  Einige Django-ORM-Features (z.B. JOIN-basierte QuerySets) sind nicht verfügbar."
    ;;
esac

# ===========================================================================#
# SCHRITT 5 – Datenbank einrichten                                            #
# ===========================================================================#
echo ""
echo "[5/9] Datenbank '$DB_NAME' einrichten..."

case "$DB" in
  postgresql)
    systemctl is-active --quiet postgresql || systemctl start postgresql

    sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='${DB_USER}'" \
      | grep -q 1 || \
      sudo -u postgres psql -c "CREATE USER ${DB_USER} WITH PASSWORD '${DB_PASS}';"

    sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'" \
      | grep -q 1 || \
      sudo -u postgres createdb -O "${DB_USER}" "${DB_NAME}"

    DATABASE_URL="postgres://${DB_USER}:${DB_PASS}@localhost:5432/${DB_NAME}"
    ;;

  mysql)
    systemctl is-active --quiet mariadb || systemctl start mariadb

    mysql -u root <<SQL
CREATE DATABASE IF NOT EXISTS \`${DB_NAME}\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS '${DB_USER}'@'localhost' IDENTIFIED BY '${DB_PASS}';
GRANT ALL PRIVILEGES ON \`${DB_NAME}\`.* TO '${DB_USER}'@'localhost';
FLUSH PRIVILEGES;
SQL

    DATABASE_URL="mysql://${DB_USER}:${DB_PASS}@localhost:3306/${DB_NAME}"
    ;;

  mongodb)
    systemctl is-active --quiet mongod || systemctl start mongod
    systemctl enable mongod

    # Datenbank und (optionaler) Nutzer anlegen
    if command -v mongosh &>/dev/null; then
      mongosh --quiet --eval "
        use ${DB_NAME};
        db.runCommand({ ping: 1 });
      " > /dev/null 2>&1 || true
    fi

    # Für MongoDB nutzen wir separate DB_* Variablen statt DATABASE_URL
    DATABASE_URL=""
    echo "  MongoDB läuft ohne Authentifizierung (Development-Modus)."
    echo "  Für Produktionssicherheit: mongosh → db.createUser() ausführen"
    echo "  und in .env DB_USER + DB_PASSWORD eintragen."
    ;;
esac

# ===========================================================================#
# SCHRITT 6 – .env-Datei erstellen                                            #
# ===========================================================================#
echo ""
echo "[6/9] .env-Datei erstellen..."
ENV_FILE="$APP_DIR/.env"

if [[ ! -f "$ENV_FILE" ]]; then
  if [[ "$DB" == "mysql" ]]; then
    DB_BLOCK="DB_ENGINE=mysql
DATABASE_URL=${DATABASE_URL}"
  else
    DB_BLOCK="DB_ENGINE=postgresql
DATABASE_URL=${DATABASE_URL}"
  fi

  cat > "$ENV_FILE" <<EOF
SECRET_KEY=${SECRET_KEY}
DEBUG=False
${DB_BLOCK}
ALLOWED_HOSTS=${DOMAIN},www.${DOMAIN}
MEDIA_ROOT=${APP_DIR}/media/
MEDIA_URL=/media/
SECURE_SSL_REDIRECT=False

EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
DEFAULT_FROM_EMAIL=noreply@${DOMAIN}

PLATFORM_COMMISSION_PERCENT=15
PAYMENT_DEMO_AUTOCONFIRM=False
STRIPE_PUBLIC_KEY=
STRIPE_SECRET_KEY=
PAYPAL_CLIENT_ID=
PAYPAL_SECRET=
REDIS_URL=redis://127.0.0.1:6379/0
CELERY_BROKER_URL=redis://127.0.0.1:6379/0
CELERY_RESULT_BACKEND=redis://127.0.0.1:6379/0
PAYMENTS_ENABLED=False
PAYMENTS_ALLOW_SINGLE_SYSTEM=False
INSTALLER_ENABLED=True
INSTALLER_TOKEN=${INSTALLER_TOKEN}
EOF

  chown "$APP_USER:$APP_USER" "$ENV_FILE"
  chmod 640 "$ENV_FILE"
  echo "  .env erstellt. Bitte SMTP-Einstellungen und Zahlungs-Keys nachtragen."
  echo "  SECURE_SSL_REDIRECT=False – nach HTTPS-Setup auf True setzen!"
else
  echo "  .env existiert bereits, wird nicht überschrieben."
fi

# Bei einem abgebrochenen oder früheren Lauf fehlende Installer-/Workerwerte
# ergänzen, ohne bestehende Datenbank- oder Geheimwerte zu überschreiben.
ensure_env_key() {
  local key="$1"
  local value="$2"
  if ! grep -q "^${key}=" "$ENV_FILE"; then
    printf '%s\n' "${key}=${value}" >> "$ENV_FILE"
  fi
}

ensure_env_key "REDIS_URL" "redis://127.0.0.1:6379/0"
ensure_env_key "CELERY_BROKER_URL" "redis://127.0.0.1:6379/0"
ensure_env_key "CELERY_RESULT_BACKEND" "redis://127.0.0.1:6379/0"
ensure_env_key "PAYMENTS_ENABLED" "False"
ensure_env_key "PAYMENTS_ALLOW_SINGLE_SYSTEM" "False"
ensure_env_key "INSTALLER_ENABLED" "True"
ensure_env_key "INSTALLER_TOKEN" "$INSTALLER_TOKEN"
chown "$APP_USER:$APP_USER" "$ENV_FILE"
chmod 640 "$ENV_FILE"

# ===========================================================================#
# SCHRITT 7 – Django vorbereiten                                              #
# ===========================================================================#
echo ""
echo "[7/9] Migrationen und statische Dateien..."
DJANGO_SETTINGS_MODULE="config.settings.production"
export DJANGO_SETTINGS_MODULE
PYTHON="$APP_DIR/.venv/bin/python"

sudo -u "$APP_USER" "$PYTHON" "$APP_DIR/manage.py" migrate --noinput
sudo -u "$APP_USER" "$PYTHON" "$APP_DIR/manage.py" collectstatic --noinput

mkdir -p "$APP_DIR/media"
chown -R "$APP_USER:$APP_USER" "$APP_DIR/media" "$APP_DIR/staticfiles"

# ===========================================================================#
# SCHRITT 8 – Gunicorn als systemd-Service                                    #
# ===========================================================================#
echo ""
echo "[8/9] Gunicorn-systemd-Service einrichten..."

mkdir -p /run/aborolms
chown "$APP_USER:$APP_USER" /run/aborolms

cat > /etc/systemd/system/aborolms.service <<EOF
[Unit]
Description=ABoroLMS Gunicorn Daemon
After=network.target

[Service]
User=${APP_USER}
Group=${APP_USER}
WorkingDirectory=${APP_DIR}
EnvironmentFile=${APP_DIR}/.env
Environment=DJANGO_SETTINGS_MODULE=config.settings.production
ExecStart=${APP_DIR}/.venv/bin/gunicorn \\
    --workers 4 \\
    --bind 0.0.0.0:8000 \\
    --timeout 120 \\
    config.wsgi:application
RuntimeDirectory=aborolms
RuntimeDirectoryMode=0750
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now aborolms.service

cat > /etc/systemd/system/aborolms-celery.service <<EOF
[Unit]
Description=ABoroLMS Celery Worker
After=network.target redis-server.service
Requires=redis-server.service

[Service]
User=${APP_USER}
Group=${APP_USER}
WorkingDirectory=${APP_DIR}
EnvironmentFile=${APP_DIR}/.env
Environment=DJANGO_SETTINGS_MODULE=config.settings.production
ExecStart=${APP_DIR}/.venv/bin/celery -A config.celery worker --loglevel=INFO
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl enable --now redis-server.service
systemctl enable --now aborolms-celery.service

# ===========================================================================#
# SCHRITT 9 – Webserver konfigurieren                                         #
# ===========================================================================#
echo ""
echo "[9/9] $WEBSERVER konfigurieren..."

if [[ "$WEBSERVER" == "nginx" ]]; then
  cat > /etc/nginx/sites-available/aborolms <<NGINX
server {
    listen 80;
    server_name ${DOMAIN} www.${DOMAIN};

    client_max_body_size 500M;

    location /static/ {
        alias ${APP_DIR}/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location /media/ {
        alias ${APP_DIR}/media/;
        expires 7d;
    }

    location / {
        proxy_pass http://unix:/run/aborolms/gunicorn.sock;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_connect_timeout 60s;
        proxy_read_timeout 120s;
    }
}
NGINX

  ln -sf /etc/nginx/sites-available/aborolms /etc/nginx/sites-enabled/aborolms
  rm -f /etc/nginx/sites-enabled/default
  nginx -t && systemctl reload nginx

elif [[ "$WEBSERVER" == "apache2" ]]; then
  a2enmod proxy proxy_http proxy_uwsgi headers rewrite
  cat > /etc/apache2/sites-available/aborolms.conf <<APACHE
<VirtualHost *:80>
    ServerName ${DOMAIN}
    ServerAlias www.${DOMAIN}

    Alias /static/ ${APP_DIR}/staticfiles/
    Alias /media/  ${APP_DIR}/media/

    <Directory ${APP_DIR}/staticfiles>
        Require all granted
        Options -Indexes
        ExpiresActive On
        ExpiresDefault "access plus 30 days"
    </Directory>
    <Directory ${APP_DIR}/media>
        Require all granted
        Options -Indexes
    </Directory>

    ProxyPreserveHost On
    ProxyPass /static/ !
    ProxyPass /media/  !
    ProxyPass / unix:/run/aborolms/gunicorn.sock|http://localhost/
    ProxyPassReverse / http://localhost/

    RequestHeader set X-Forwarded-Proto "http"
    LimitRequestBody 524288000
</VirtualHost>
APACHE

  a2enmod expires || true
  a2ensite aborolms
  a2dissite 000-default || true
  apachectl configtest && systemctl reload apache2
fi

# --------------------------------------------------------------------------- #
# Abschluss
# --------------------------------------------------------------------------- #
echo ""
echo "========================================================"
echo " Installation abgeschlossen!"
echo "========================================================"
echo ""
echo "Nächste Schritte:"
echo ""
echo "  1. Installationsassistent öffnen:"
echo "     http://${DOMAIN}/install/${INSTALLER_TOKEN}/"
echo "     Nach Abschluss wird der Assistent automatisch deaktiviert."
echo ""
echo "  2. Demo-Daten laden (optional):"
echo "     sudo -u ${APP_USER} ${APP_DIR}/.venv/bin/python ${APP_DIR}/manage.py create_demo_data"
echo ""
echo "  3. HTTPS konfigurieren (empfohlen) – danach SECURE_SSL_REDIRECT=True in .env:"
echo "     apt install certbot python3-certbot-${WEBSERVER}"
echo "     certbot --${WEBSERVER} -d ${DOMAIN}"
echo ""
echo "  4. .env bearbeiten (SMTP, Zahlungs-Keys):"
echo "     nano ${ENV_FILE}"
echo ""
echo "  5. Dienststatus prüfen:"
echo "     journalctl -u aborolms -f"
echo ""
if [[ "$DB" != "mongodb" ]]; then
  echo "  Datenbankpasswort (sicher aufbewahren!): ${DB_PASS}"
fi
