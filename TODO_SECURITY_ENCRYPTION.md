# TODO Sicherheit, Datenschutz und Verschluesselung

Stand: 2026-06-29

## Aktualisierung 2026-09-23

- Aktuelle Gesamtvalidierung: `manage.py check` OK, keine offenen Migrationen, **47 Tests OK**.
- ML-Einzelsystem: Zahlungen deaktiviert; historische Zahlungsdaten bleiben geschützt und lesbar.
- Noch offen bleiben Rechnungs-/Adress-Hybridmodell, Hash-Lookups, Datenexport, Löschung/Anonymisierung, Backup-/Restore-Prüfung und Key-Rotation.
- Zusätzlich offen: MIME-/Virenscan für Uploads, Videoverarbeitung und rechtliche Datenschutzprüfung.

## Zuletzt erledigt

- 2026-06-29 12:36 - Historische Validierung abgeschlossen: `check` OK, keine offenen Migrationen, 37 Tests OK. Die aktuelle Gesamtprüfung vom 23.09.2026 umfasst 47 Tests.

## Ziel

Sensible Daten sollen schrittweise besser geschuetzt werden. Fokus: Namen, Adressen, Zahlungsdaten, Rechnungen, Provider-Referenzen, SMTP-Secrets und Audit-Daten. Datenbank-Dumps sollen ausserhalb der Django-Anwendung moeglichst unlesbar sein, ohne Kernfunktionen wie Login, Suche, Dashboards und Zahlungsreports zu zerstoeren.

## Arbeitspakete

### 1. Bestandsaufnahme

- [x] Anforderungen und Grenzen der Verschluesselung im Projekt dokumentieren.
- [x] Pruefen, ob `cryptography` bereits installiert ist. Ergebnis: nicht installiert, Dependency muss ergaenzt werden.
- [x] Sensible Felder nach Risiko und technischer Machbarkeit klassifizieren. Erste Phase: Secrets, SMTP-Passwort, Bankdaten und Provider-/Betreiberdaten.
- [x] Felder markieren, die nicht direkt verschluesselt werden sollten, weil sie fuer Suche, Filter, Summen oder Joins gebraucht werden. Betraege, Status, IDs, Slugs und Reporting-Felder bleiben vorerst unverschluesselt.

### 2. Technische Basis

- [x] Eigenes Security-Modul fuer feldbasierte Verschluesselung anlegen.
- [x] Separaten `FIELD_ENCRYPTION_KEY` in Settings und `.env.example` vorsehen.
- [x] Systemcheck fuer fehlenden oder unsicheren Encryption-Key ergaenzen.
- [x] Unit-Tests fuer Encrypt/Decrypt, leere Werte und Key-Fehler ergaenzen.

### 3. Erste Verschluesselungsphase

- [x] SMTP-Passwort verschluesselt speichern.
- [x] Payment-Secrets verschluesselt speichern: Stripe Secret, PayPal Secret.
- [x] Bankdaten verschluesselt speichern: IBAN, BIC, Kontoinhaber, Bankname.
- [x] Provider-Referenz und Betreiber-Notiz pruefen und verschluesseln.

### 4. Rechnungs- und Adressdaten

- [ ] Rechnungs-Empfaengername verschluesseln oder Hybridmodell mit Lookup-Feld planen.
- [ ] Rechnungs-E-Mail verschluesseln oder mit Hash-Lookup absichern.
- [ ] Zukuenftige Adressfelder als verschluesselte Felder planen.
- [ ] Export-/Anzeige-Views auf entschluesselte Darstellung pruefen.

### 5. Suchbarkeit und Hash-Lookups

- [ ] Normalisierte Hash-Felder fuer exakte Suche planen, z. B. E-Mail.
- [ ] Admin-Suche fuer verschluesselte Felder anpassen.
- [ ] Migrationstrategie fuer bestehende Klartextdaten definieren.

### 6. Audit, Datenschutz und Betrieb

- [ ] Audit-Log fuer sensible Aktionen erweitern.
- [ ] Datenexport pro Nutzer/Organisation planen.
- [ ] Loesch-/Anonymisierungsworkflow planen.
- [ ] Backup-/Restore-Prozess mit verschluesselten Feldern dokumentieren.
- [ ] Key-Rotation-Konzept dokumentieren.

### 7. Validierung

- [x] `python manage.py check` ausfuehren. Ergebnis: OK.
- [x] `python manage.py makemigrations --check --dry-run` ausfuehren. Ergebnis: No changes detected.
- [x] `python manage.py test` ausführen. Letzte Gesamtprüfung: 47 Tests OK.
- [x] Ergebnis in dieser Datei dokumentieren.

## Notizen

- Nicht pauschal alle Daten verschluesseln. Felder fuer Summen, Filter und Reporting brauchen oft Klartext oder separate technische Felder.
- Django-Passwoerter bleiben gehasht, nicht verschluesselt.
- Der normale `SECRET_KEY` soll nicht als alleiniger Feldverschluesselungs-Key verwendet werden.
## Feldklassifizierung 2026-06-29

### Phase 1: Direkt verschluesselbar

- `OrganisationEmailKonfiguration.smtp_password`
- `Zahlungseinstellungen.stripe_secret_key`
- `Zahlungseinstellungen.paypal_secret`
- `Zahlungseinstellungen.iban`
- `Zahlungseinstellungen.bic`
- `Zahlungseinstellungen.kontoinhaber`
- `Zahlungseinstellungen.bankname`
- `Zahlung.provider_referenz`
- `Zahlung.betreiber_notiz`

### Phase 2: Hybridmodell empfohlen

- `Rechnung.empfaenger_name`
- `Rechnung.empfaenger_email`
- zukuenftige Rechnungsadresse
- Nutzername/E-Mail im Account-Kontext

Grund: Anzeige braucht Klartext in Django, Suche/Zuordnung braucht Hash- oder separate Lookup-Felder.

### Vorerst nicht verschluesseln

- Geldbetraege (`betrag_brutto`, `trainer_anteil`, `plattform_gebuehr`), da Summen und Dashboards darauf basieren.
- Statusfelder, Rollen, Slugs, IDs, Fremdschluessel und Zeitstempel.
- Rechnungsnummern, weil sie fuer Suche und Belegreferenzen gebraucht werden.
