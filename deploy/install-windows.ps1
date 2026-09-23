#Requires -RunAsAdministrator
<#
.SYNOPSIS
    ABoroLMS – Windows Server Installationsskript

.DESCRIPTION
    Installiert ABoroLMS auf Windows Server mit IIS als Reverse Proxy
    und Waitress als WSGI-Server.

    Unterstützte Datenbanken:
      postgresql  – PostgreSQL (Standard)
      mysql       – MariaDB / MySQL
      mssql       – Microsoft SQL Server Express
      Redis       – Redis für Celery-Aufgaben

.PARAMETER RepoUrl
    GitHub-URL des Repositories.

.PARAMETER InstallDir
    Installationsverzeichnis. Standard: C:\aborolms

.PARAMETER Domain
    Hostname der Anwendung. Standard: localhost

.PARAMETER DbEngine
    Datenbankmotor: postgresql | mysql | mssql
    Standard: postgresql

.PARAMETER DbPassword
    Datenbankpasswort (wird zufällig generiert wenn leer).

.PARAMETER SkipIIS
    IIS-Konfiguration überspringen.

.EXAMPLE
    .\install-windows.ps1 -RepoUrl "https://github.com/user/LMS.git" -Domain "lms.firma.de"

.EXAMPLE
    .\install-windows.ps1 -DbEngine mssql -Domain "lms.firma.de"

.EXAMPLE
    .\install-windows.ps1 -DbEngine mongodb -SkipIIS
#>
param(
    [string]$RepoUrl    = "https://github.com/YOUR_USERNAME/LMS.git",
    [string]$InstallDir = "C:\aborolms",
    [string]$Domain     = "localhost",
    [ValidateSet("postgresql","mysql","mssql")]
    [string]$DbEngine   = "postgresql",
    [string]$DbPassword = "",
    [switch]$SkipIIS,
    [switch]$Unattended
)

$ErrorActionPreference = "Stop"

$DbName      = "aborolms"
$DbUser      = "aborolms"
$AppPort     = 8000
$ServiceName = "ABoroLMS"
$LogDir      = "$InstallDir\logs"
$InstallerToken = ([guid]::NewGuid().ToString("N") + [guid]::NewGuid().ToString("N"))

# Passwort generieren
if (-not $DbPassword -and $DbEngine -ne "mongodb") {
    $DbPassword = -join ((48..57) + (65..90) + (97..122) |
        Get-Random -Count 28 | ForEach-Object { [char]$_ })
}

$SecretKey = -join ((33..126) | Where-Object { $_ -notin @(34, 39, 92) } |
    Get-Random -Count 50 | ForEach-Object { [char]$_ })

# --------------------------------------------------------------------------- #
# Hilfsfunktionen
# --------------------------------------------------------------------------- #
function Write-Step($n, $msg) {
    Write-Host ""
    Write-Host "[$n] $msg" -ForegroundColor Green
}

function Invoke-Choco($pkg) {
    choco install $pkg -y --no-progress --ignore-checksums 2>&1 |
        Where-Object { $_ -match "^(Error|WARNING)" } | Write-Host
}

function Refresh-Path {
    $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH", "Machine") + ";" +
                [System.Environment]::GetEnvironmentVariable("PATH", "User")
}

# --------------------------------------------------------------------------- #
# Zusammenfassung
# --------------------------------------------------------------------------- #
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host " ABoroLMS – Windows Installer" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host " Repo       : $RepoUrl"
Write-Host " InstallDir : $InstallDir"
Write-Host " Domain     : $Domain"
Write-Host " Datenbank  : $DbEngine"
Write-Host " Port       : $AppPort"
Write-Host "========================================================" -ForegroundColor Cyan
if (-not $Unattended) {
    $confirm = Read-Host "Fortfahren? [j/N]"
    if ($confirm -notmatch "^[jJ]$") { exit 0 }
}

# ===========================================================================#
# SCHRITT 1 – Chocolatey                                                      #
# ===========================================================================#
Write-Step "1/10" "Chocolatey prüfen / installieren..."
if (-not (Get-Command choco -ErrorAction SilentlyContinue)) {
    Set-ExecutionPolicy Bypass -Scope Process -Force
    [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.SecurityProtocolType]::Tls12
    Invoke-Expression ((New-Object System.Net.WebClient).DownloadString(
        'https://community.chocolatey.org/install.ps1'))
    Refresh-Path
}
Invoke-Choco "redis-64"
Start-Service -Name "Redis" -ErrorAction SilentlyContinue

# ===========================================================================#
# SCHRITT 2 – Basis-Pakete (immer)                                            #
# ===========================================================================#
Write-Step "2/10" "Basis-Pakete installieren (Python 3.12, Git, NSSM)..."
foreach ($pkg in @("python312", "git", "nssm")) { Invoke-Choco $pkg }
Refresh-Path

# ===========================================================================#
# SCHRITT 3 – GTK3-Runtime (für WeasyPrint PDF-Export)                       #
# ===========================================================================#
Write-Step "3/10" "GTK3-Runtime für WeasyPrint installieren..."
$GtkDir = "C:\Program Files\GTK3-Runtime Win64"
if (-not (Test-Path $GtkDir)) {
    $GtkInstaller = "$env:TEMP\gtk3-runtime.exe"
    $GtkUrl = "https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases/download/2022-01-04/gtk3-runtime-3.24.31-2022-01-04-ts-win64.exe"
    Write-Host "  Lade GTK3 herunter..."
    Invoke-WebRequest -Uri $GtkUrl -OutFile $GtkInstaller -UseBasicParsing
    Start-Process -FilePath $GtkInstaller -ArgumentList "/S" -Wait
    Remove-Item $GtkInstaller -Force -ErrorAction SilentlyContinue
} else {
    Write-Host "  GTK3-Runtime bereits vorhanden."
}
$GtkBin = "$GtkDir\bin"
if ($env:PATH -notlike "*GTK3*") {
    $env:PATH += ";$GtkBin"
    [System.Environment]::SetEnvironmentVariable(
        "PATH",
        [System.Environment]::GetEnvironmentVariable("PATH", "Machine") + ";$GtkBin",
        "Machine")
}

# ===========================================================================#
# SCHRITT 4 – Datenbank-Server installieren                                   #
# ===========================================================================#
Write-Step "4/10" "Datenbank-Server installieren ($DbEngine)..."

switch ($DbEngine) {
    "postgresql" {
        Invoke-Choco "postgresql"
        Refresh-Path
    }
    "mysql" {
        # MariaDB ist der empfohlene Drop-in-Ersatz und über Chocolatey einfacher zu installieren
        Invoke-Choco "mariadb"
        Refresh-Path
        # Sicherstellen, dass der MariaDB-Dienst läuft
        Start-Service -Name "MariaDB" -ErrorAction SilentlyContinue
    }
    "mssql" {
        # SQL Server 2022 Express (kostenlos)
        Invoke-Choco "sql-server-2022"
        Invoke-Choco "sqlserver-odbcdriver"   # ODBC Driver 17/18 for SQL Server
        Invoke-Choco "sqlserver-cmdlineutils"  # sqlcmd
        Refresh-Path
    }
    "mongodb" {
        Invoke-Choco "mongodb"
        Refresh-Path
        # mongosh für DB-Setup
        Invoke-Choco "mongosh"
        Start-Service -Name "MongoDB" -ErrorAction SilentlyContinue
    }
}

# ===========================================================================#
# SCHRITT 5 – Repository klonen / aktualisieren                               #
# ===========================================================================#
Write-Step "5/10" "Repository klonen..."
if (Test-Path "$InstallDir\.git") {
    git -C $InstallDir pull --ff-only
} else {
    git clone $RepoUrl $InstallDir
}

# ===========================================================================#
# SCHRITT 6 – Virtualenv und Python-Pakete                                    #
# ===========================================================================#
Write-Step "6/10" "Virtualenv und Python-Abhängigkeiten installieren..."
$PythonExe = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $PythonExe) { $PythonExe = "C:\Python312\python.exe" }

& $PythonExe -m venv "$InstallDir\.venv"
$Pip  = "$InstallDir\.venv\Scripts\pip.exe"
$Py   = "$InstallDir\.venv\Scripts\python.exe"

& $Pip install --upgrade pip
& $Pip install -r "$InstallDir\requirements\production.txt"
& $Pip install waitress   # reiner Python WSGI-Server (kein C-Compiler nötig)
$FieldEncryptionKey = & $Py -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Datenbankspezifische Python-Treiber
switch ($DbEngine) {
    "postgresql" {
        & $Pip install "psycopg2-binary>=2.9"
    }
    "mysql" {
        # mysqlclient benötigt Visual C++ Build Tools; PyMySQL ist der einfachere Weg auf Windows
        try {
            & $Pip install "mysqlclient>=2.1"
        } catch {
            Write-Host "  mysqlclient konnte nicht installiert werden, verwende PyMySQL..." -ForegroundColor Yellow
            & $Pip install "PyMySQL>=1.1" cryptography
        }
    }
    "mssql" {
        & $Pip install "mssql-django>=1.4" "pyodbc>=5.0"
    }
    "mongodb" {
        & $Pip install "django-mongodb-backend" "pymongo>=4.6"
        Write-Host "  HINWEIS: MongoDB ist kein unterstütztes Produktionsziel für Django 6.1.1." -ForegroundColor Yellow
    }
}

# ===========================================================================#
# SCHRITT 7 – Datenbank und Benutzer anlegen                                  #
# ===========================================================================#
Write-Step "7/10" "Datenbank '$DbName' anlegen..."
$DatabaseUrl = ""

switch ($DbEngine) {
    "postgresql" {
        $env:PGPASSWORD = "postgres"
        $PsqlExe = (Get-ChildItem "C:\Program Files\PostgreSQL" -Filter "psql.exe" -Recurse -ErrorAction SilentlyContinue |
                    Sort-Object LastWriteTime -Descending | Select-Object -First 1).FullName
        if (-not $PsqlExe) { $PsqlExe = "psql" }

        & $PsqlExe -U postgres -c @"
DO `$`$ BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='$DbUser') THEN
    CREATE USER $DbUser WITH PASSWORD '$DbPassword';
  END IF;
END `$`$;
"@
        & $PsqlExe -U postgres -c "SELECT 1 FROM pg_database WHERE datname='$DbName'" |
            ForEach-Object { if ($_ -notmatch "^\s*1") {
                & $PsqlExe -U postgres -c "CREATE DATABASE $DbName OWNER $DbUser ENCODING 'UTF8';"
            }}
        Remove-Item env:PGPASSWORD -ErrorAction SilentlyContinue
        $DatabaseUrl = "postgres://${DbUser}:${DbPassword}@localhost:5432/${DbName}"
    }

    "mysql" {
        $MysqlExe = (Get-Command mysql -ErrorAction SilentlyContinue).Source
        if (-not $MysqlExe) {
            $MysqlExe = (Get-ChildItem "C:\Program Files\MariaDB*" -Filter "mysql.exe" -Recurse -ErrorAction SilentlyContinue |
                         Select-Object -First 1).FullName
        }
        $SqlCmds = @"
CREATE DATABASE IF NOT EXISTS ``$DbName`` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS '$DbUser'@'localhost' IDENTIFIED BY '$DbPassword';
GRANT ALL PRIVILEGES ON ``$DbName``.* TO '$DbUser'@'localhost';
FLUSH PRIVILEGES;
"@
        $SqlCmds | & $MysqlExe -u root 2>&1
        $DatabaseUrl = "mysql://${DbUser}:${DbPassword}@localhost:3306/${DbName}"
    }

    "mssql" {
        # SQL Server: Windows-Auth für Setup verwenden
        $SqlcmdExe = (Get-Command sqlcmd -ErrorAction SilentlyContinue).Source
        if (-not $SqlcmdExe) { $SqlcmdExe = "sqlcmd" }

        & $SqlcmdExe -S "localhost\SQLEXPRESS" -E -Q @"
IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = '$DbName')
    CREATE DATABASE [$DbName];
IF NOT EXISTS (SELECT name FROM sys.server_principals WHERE name = '$DbUser')
BEGIN
    CREATE LOGIN [$DbUser] WITH PASSWORD = '$DbPassword';
END
USE [$DbName];
IF NOT EXISTS (SELECT name FROM sys.database_principals WHERE name = '$DbUser')
BEGIN
    CREATE USER [$DbUser] FOR LOGIN [$DbUser];
    ALTER ROLE db_owner ADD MEMBER [$DbUser];
END
"@ 2>&1

        # MSSQL nutzt keine DATABASE_URL – stattdessen separate Variablen
        $DatabaseUrl = ""
    }

    "mongodb" {
        if (Get-Command mongosh -ErrorAction SilentlyContinue) {
            mongosh --quiet --eval "db.getSiblingDB('$DbName').runCommand({ping:1})" 2>&1 | Out-Null
        }
        Write-Host "  MongoDB läuft. Authentifizierung muss ggf. manuell konfiguriert werden." -ForegroundColor Yellow
        $DatabaseUrl = ""
    }
}

# ===========================================================================#
# SCHRITT 8 – .env-Datei erstellen                                            #
# ===========================================================================#
Write-Step "8/10" ".env-Datei erstellen..."
$EnvFile = "$InstallDir\.env"

if (-not (Test-Path $EnvFile)) {
    switch ($DbEngine) {
        "postgresql" {
            $DbBlock = "DB_ENGINE=postgresql`nDATABASE_URL=$DatabaseUrl"
        }
        "mysql" {
            $DbBlock = "DB_ENGINE=mysql`nDATABASE_URL=$DatabaseUrl"
        }
        "mssql" {
            $DbBlock = "DB_ENGINE=mssql`nDB_NAME=$DbName`nDB_USER=$DbUser`nDB_PASSWORD=$DbPassword`nDB_HOST=localhost\SQLEXPRESS`nDB_PORT=1433"
        }
        "mongodb" {
            $DbBlock = "DB_ENGINE=mongodb`nDB_NAME=$DbName`nDB_HOST=localhost`nDB_PORT=27017`nDB_USER=`nDB_PASSWORD="
        }
    }

    @"
SECRET_KEY=$SecretKey
DEBUG=False
$DbBlock
ALLOWED_HOSTS=${Domain},localhost,127.0.0.1
MEDIA_ROOT=$InstallDir\media\
MEDIA_URL=/media/
SECURE_SSL_REDIRECT=False

EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
DEFAULT_FROM_EMAIL=noreply@${Domain}

PLATFORM_COMMISSION_PERCENT=15
PAYMENT_DEMO_AUTOCONFIRM=False
PAYMENTS_ENABLED=False
PAYMENTS_ALLOW_SINGLE_SYSTEM=False
REDIS_URL=redis://127.0.0.1:6379/0
CELERY_BROKER_URL=redis://127.0.0.1:6379/0
CELERY_RESULT_BACKEND=redis://127.0.0.1:6379/0
FIELD_ENCRYPTION_KEY=$FieldEncryptionKey
INSTALLER_ENABLED=True
INSTALLER_TOKEN=$InstallerToken
STRIPE_PUBLIC_KEY=
STRIPE_SECRET_KEY=
PAYPAL_CLIENT_ID=
PAYPAL_SECRET=
"@ | Set-Content -Path $EnvFile -Encoding utf8

    Write-Host "  .env erstellt. SECURE_SSL_REDIRECT nach HTTPS-Setup auf True setzen."
} else {
    Write-Host "  .env existiert bereits, wird nicht überschrieben."
}

# Django-Umgebung vorbereiten
$env:DJANGO_SETTINGS_MODULE = "config.settings.production"

& $Py "$InstallDir\manage.py" migrate --noinput
& $Py "$InstallDir\manage.py" collectstatic --noinput

New-Item -ItemType Directory -Path "$InstallDir\media" -Force | Out-Null
New-Item -ItemType Directory -Path $LogDir -Force | Out-Null

# ===========================================================================#
# SCHRITT 9 – Waitress als Windows-Dienst (NSSM)                             #
# ===========================================================================#
Write-Step "9/10" "Waitress-Dienst mit NSSM einrichten..."

$RunScript = "$InstallDir\deploy\run_waitress.py"
@"
import os, sys
sys.path.insert(0, r'$InstallDir')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')
from waitress import serve
from config.wsgi import application
serve(application, host='127.0.0.1', port=$AppPort, threads=8, channel_timeout=120)
"@ | Set-Content -Path $RunScript -Encoding utf8

# Alten Dienst entfernen falls vorhanden
nssm stop $ServiceName 2>&1 | Out-Null
nssm remove $ServiceName confirm 2>&1 | Out-Null

nssm install $ServiceName $Py $RunScript
nssm set $ServiceName AppDirectory $InstallDir
nssm set $ServiceName AppEnvironmentExtra "DJANGO_SETTINGS_MODULE=config.settings.production"
nssm set $ServiceName AppStdout "$LogDir\waitress.log"
nssm set $ServiceName AppStderr "$LogDir\waitress-error.log"
nssm set $ServiceName AppRotateFiles 1
nssm set $ServiceName AppRotateBytes 5000000
nssm set $ServiceName Start SERVICE_AUTO_START
nssm start $ServiceName

$CeleryServiceName = "ABoroLMS-Celery"
nssm stop $CeleryServiceName 2>&1 | Out-Null
nssm remove $CeleryServiceName confirm 2>&1 | Out-Null
nssm install $CeleryServiceName $Py "-m celery -A config.celery worker --loglevel=INFO"
nssm set $CeleryServiceName AppDirectory $InstallDir
nssm set $CeleryServiceName AppEnvironmentExtra "DJANGO_SETTINGS_MODULE=config.settings.production"
nssm set $CeleryServiceName AppStdout "$LogDir\celery.log"
nssm set $CeleryServiceName AppStderr "$LogDir\celery-error.log"
nssm set $CeleryServiceName Start SERVICE_AUTO_START
nssm start $CeleryServiceName

Write-Host "  Waitress läuft auf http://127.0.0.1:$AppPort"

# ===========================================================================#
# SCHRITT 10 – IIS als Reverse Proxy (optional)                              #
# ===========================================================================#
if (-not $SkipIIS) {
    Write-Step "10/10" "IIS + URL Rewrite + ARR installieren und konfigurieren..."

    # IIS-Feature aktivieren
    $IisFeatures = @(
        "IIS-WebServerRole", "IIS-WebServer", "IIS-CommonHttpFeatures",
        "IIS-StaticContent", "IIS-DefaultDocument", "IIS-HttpErrors",
        "IIS-ApplicationDevelopment", "IIS-ISAPIExtensions", "IIS-ISAPIFilter",
        "IIS-HttpCompressionStatic", "IIS-ManagementConsole"
    )
    foreach ($f in $IisFeatures) {
        Enable-WindowsOptionalFeature -Online -FeatureName $f -All -NoRestart -ErrorAction SilentlyContinue | Out-Null
    }

    # URL Rewrite und ARR via Chocolatey
    Invoke-Choco "urlrewrite"
    Invoke-Choco "iis-arr"

    # ARR-Proxy global aktivieren
    try {
        $arrConf = [xml](Get-Content "C:\Windows\System32\inetsrv\config\applicationHost.config")
        $proxySection = $arrConf.configuration.'system.webServer'.proxy
        if ($null -ne $proxySection) {
            $proxySection.enabled = "true"
            $arrConf.Save("C:\Windows\System32\inetsrv\config\applicationHost.config")
        }
    } catch {
        Write-Host "  ARR-Proxy-Aktivierung übersprungen – bitte manuell in IIS-Manager aktivieren." -ForegroundColor Yellow
    }

    # Statische/Medien-Verzeichnisse
    $WebRoot = "C:\inetpub\wwwroot\aborolms"
    New-Item -ItemType Directory -Path $WebRoot -Force | Out-Null
    New-Item -ItemType Junction -Path "$WebRoot\static" -Target "$InstallDir\staticfiles" -Force -ErrorAction SilentlyContinue | Out-Null
    New-Item -ItemType Junction -Path "$WebRoot\media"  -Target "$InstallDir\media"       -Force -ErrorAction SilentlyContinue | Out-Null

    # web.config mit Reverse-Proxy-Regeln
    @"
<?xml version="1.0" encoding="UTF-8"?>
<configuration>
  <system.webServer>
    <rewrite>
      <rules>
        <rule name="Static" stopProcessing="true">
          <match url="^static/(.*)" />
          <action type="Rewrite" url="static/{R:1}" />
        </rule>
        <rule name="Media" stopProcessing="true">
          <match url="^media/(.*)" />
          <action type="Rewrite" url="media/{R:1}" />
        </rule>
        <rule name="ReverseProxy" stopProcessing="true">
          <match url="(.*)" />
          <action type="Rewrite" url="http://127.0.0.1:$AppPort/{R:1}" />
        </rule>
      </rules>
    </rewrite>
    <staticContent>
      <clientCache cacheControlMode="UseMaxAge" cacheControlMaxAge="30.00:00:00" />
    </staticContent>
    <security>
      <requestFiltering>
        <requestLimits maxAllowedContentLength="524288000" />
      </requestFiltering>
    </security>
  </system.webServer>
</configuration>
"@ | Set-Content -Path "$WebRoot\web.config" -Encoding utf8

    # IIS-Website anlegen
    try {
        Import-Module WebAdministration -ErrorAction Stop
        if (-not (Get-Website -Name $ServiceName -ErrorAction SilentlyContinue)) {
            New-Website -Name $ServiceName -PhysicalPath $WebRoot -Port 80 -HostHeader $Domain | Out-Null
        }
        Write-Host "  IIS-Website '$ServiceName' (Port 80, Host: $Domain) eingerichtet."
    } catch {
        Write-Host "  IIS WebAdministration nicht verfügbar – Website manuell einrichten." -ForegroundColor Yellow
        Write-Host "    Web-Root: $WebRoot"
        Write-Host "    Proxy → http://127.0.0.1:$AppPort"
    }
} else {
    Write-Step "10/10" "IIS wird übersprungen (-SkipIIS). Waitress: http://127.0.0.1:$AppPort"
}

# --------------------------------------------------------------------------- #
# Abschluss
# --------------------------------------------------------------------------- #
Write-Host ""
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host " Installation abgeschlossen!" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Nächste Schritte:" -ForegroundColor White
Write-Host ""
Write-Host "  1. Installationsassistent öffnen:"
Write-Host "     http://${Domain}/install/${InstallerToken}/"
Write-Host "     Nach Abschluss wird der Assistent automatisch deaktiviert."
Write-Host ""
Write-Host "  2. Demo-Daten laden (optional):"
Write-Host "     .\.venv\Scripts\python.exe manage.py create_demo_data"
Write-Host ""
Write-Host "  3. HTTPS – nach Einrichtung SECURE_SSL_REDIRECT=True in .env setzen:"
Write-Host "     https://www.win-acme.com/ (Let's Encrypt für IIS)"
Write-Host ""
Write-Host "  4. .env anpassen (SMTP, Zahlungs-Keys):"
Write-Host "     notepad $EnvFile"
Write-Host ""
Write-Host "  5. Dienststatus prüfen:"
Write-Host "     nssm status $ServiceName"
Write-Host "     Get-Content $LogDir\waitress.log -Tail 50"
Write-Host ""
if ($DbEngine -ne "mongodb") {
    Write-Host "  Datenbankpasswort (sicher aufbewahren!): $DbPassword" -ForegroundColor Yellow
}
if ($DbEngine -eq "mongodb") {
    Write-Host "  MongoDB läuft ohne Authentifizierung – für Produktion absichern!" -ForegroundColor Yellow
    Write-Host "  Doku: https://www.mongodb.com/docs/manual/security/"
}
