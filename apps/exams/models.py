from django.conf import settings
from django.db import models
from django_quill.fields import QuillField

from apps.security.fields import EncryptedTextField


class Fragenkatalog(models.Model):
    titel = models.CharField(max_length=300)
    beschreibung = models.TextField(blank=True)
    organisation = models.ForeignKey("organisations.Organisation", on_delete=models.CASCADE)
    erstellt_von = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    erstellt_am = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["titel"]
        verbose_name = "Fragenkatalog"
        verbose_name_plural = "Fragenkataloge"

    def __str__(self):
        return self.titel


class FragenTag(models.Model):
    name = models.CharField(max_length=50)
    organisation = models.ForeignKey("organisations.Organisation", on_delete=models.CASCADE)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["name", "organisation"], name="unique_question_tag_org")]
        ordering = ["name"]
        verbose_name = "Fragen-Tag"
        verbose_name_plural = "Fragen-Tags"

    def __str__(self):
        return self.name


class Frage(models.Model):
    class Typ(models.TextChoices):
        SINGLE_CHOICE = "SC", "Single Choice"
        MULTIPLE_CHOICE = "MC", "Multiple Choice"
        WAHR_FALSCH = "WF", "Wahr / Falsch"
        FREITEXT = "FT", "Freitext"
        ZUORDNUNG = "ZO", "Zuordnung"
        SZENARIO = "SZ", "Szenario (Case Study)"

    class Schwierigkeit(models.TextChoices):
        LEICHT = "L", "Leicht"
        MITTEL = "M", "Mittel"
        SCHWER = "S", "Schwer"

    fragenkatalog = models.ForeignKey(Fragenkatalog, on_delete=models.CASCADE, related_name="fragen")
    typ = models.CharField(max_length=2, choices=Typ.choices)
    fragetext = QuillField()
    erklaerung = QuillField(blank=True)
    bewertungshinweis = QuillField(blank=True, verbose_name="Bewertungsschema")
    schwierigkeit = models.CharField(max_length=1, choices=Schwierigkeit.choices, default=Schwierigkeit.MITTEL)
    punkte = models.PositiveIntegerField(default=1)
    aktiv = models.BooleanField(default=True)
    tags = models.ManyToManyField(FragenTag, blank=True)
    eltern_szenario = models.ForeignKey("self", on_delete=models.CASCADE, null=True, blank=True, related_name="teilfragen")

    class Meta:
        ordering = ["id"]
        verbose_name = "Frage"
        verbose_name_plural = "Fragen"

    def __str__(self):
        return f"{self.get_typ_display()} - {self.fragenkatalog}"


class Antwort(models.Model):
    frage = models.ForeignKey(Frage, on_delete=models.CASCADE, related_name="antworten")
    antworttext = models.TextField()
    ist_korrekt = models.BooleanField(default=False)
    reihenfolge = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["reihenfolge"]
        verbose_name = "Antwort"
        verbose_name_plural = "Antworten"

    def __str__(self):
        return self.antworttext[:80]


class ZuordnungsPaar(models.Model):
    frage = models.ForeignKey(Frage, on_delete=models.CASCADE, related_name="zuordnungen")
    linkes_element = models.CharField(max_length=500)
    rechtes_element = models.CharField(max_length=500)
    reihenfolge = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["reihenfolge"]
        verbose_name = "Zuordnungspaar"
        verbose_name_plural = "Zuordnungspaare"

    def __str__(self):
        return f"{self.linkes_element} -> {self.rechtes_element}"


class Pruefung(models.Model):
    class Zertifikatsnummernart(models.TextChoices):
        INTERN = "INTERN", "Interne fortlaufende Nummer"
        EXTERN = "EXTERN", "Externer Nummernbereich"
    titel = models.CharField(max_length=300)
    beschreibung = models.TextField(blank=True)
    organisation = models.ForeignKey("organisations.Organisation", on_delete=models.CASCADE)
    fragenkatalog = models.ForeignKey(Fragenkatalog, on_delete=models.CASCADE)
    anzahl_fragen = models.PositiveIntegerField()
    zeitlimit_minuten = models.PositiveIntegerField(null=True, blank=True)
    bestehensgrenze_prozent = models.PositiveIntegerField(default=70)
    max_versuche = models.PositiveIntegerField(null=True, blank=True)
    zufaellige_fragenreihenfolge = models.BooleanField(default=True)
    zufaellige_antwortfolge = models.BooleanField(default=True)
    kein_zurueck = models.BooleanField(default=False)
    ist_aktiv = models.BooleanField(default=True)
    zertifikatsnummernart = models.CharField(max_length=10, choices=Zertifikatsnummernart.choices, default=Zertifikatsnummernart.INTERN)
    externe_nummern_prefix = models.CharField(max_length=40, blank=True)
    externe_nummern_naechste = models.PositiveIntegerField(default=1)
    externe_nummern_ende = models.PositiveIntegerField(null=True, blank=True)
    pdf_antwortzeilen = models.PositiveIntegerField(default=6, verbose_name="Antwortzeilen im PDF")
    pdf_fusszeile = models.CharField(max_length=200, blank=True, default="", verbose_name="PDF-Fusszeile")
    erstellt_am = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["titel"]
        verbose_name = "Pruefung"
        verbose_name_plural = "Pruefungen"

    def __str__(self):
        return self.titel


class Pruefungsversion(models.Model):
    """Unveraenderlicher Snapshot der Pruefungsparameter und gezogenen Fragen."""

    pruefung = models.ForeignKey(Pruefung, on_delete=models.CASCADE, related_name="versionen")
    versionsnummer = models.PositiveIntegerField()
    erstellt_von = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    erstellt_am = models.DateTimeField(auto_now_add=True)
    snapshot = models.JSONField(default=dict)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["pruefung", "versionsnummer"], name="unique_exam_version_number")]
        ordering = ["-versionsnummer"]
        verbose_name = "Pruefungsversion"
        verbose_name_plural = "Pruefungsversionen"

    def __str__(self):
        return f"{self.pruefung} v{self.versionsnummer}"


class PruefungsThemenquote(models.Model):
    pruefung = models.ForeignKey(Pruefung, on_delete=models.CASCADE, related_name="themenquoten")
    thema = models.ForeignKey(FragenTag, on_delete=models.CASCADE, related_name="pruefungsquoten")
    anzahl_fragen = models.PositiveIntegerField(verbose_name="Anzahl Fragen")

    class Meta:
        constraints = [models.UniqueConstraint(fields=["pruefung", "thema"], name="unique_exam_topic_quota")]
        ordering = ["thema__name"]
        verbose_name = "Themenquote"
        verbose_name_plural = "Themenquoten"

    def __str__(self):
        return f"{self.pruefung}: {self.anzahl_fragen} aus {self.thema}"


class PruefungsAnmeldung(models.Model):
    nutzer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="pruefungsanmeldungen")
    pruefung = models.ForeignKey(Pruefung, on_delete=models.CASCADE, related_name="anmeldungen")
    angemeldet_am = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["nutzer", "pruefung"], name="unique_user_exam_registration")]
        ordering = ["-angemeldet_am"]
        verbose_name = "Prüfungsanmeldung"
        verbose_name_plural = "Prüfungsanmeldungen"


class PruefungsFreigabe(models.Model):
    """Serverseitige Freigabe einer konkreten Zertifikatspruefung fuer einen Teilnehmer."""

    pruefung = models.ForeignKey(Pruefung, on_delete=models.CASCADE, related_name="freigaben")
    nutzer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="pruefungsfreigaben")
    freigegeben_von = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="erteilte_pruefungsfreigaben",
    )
    freigegeben_am = models.DateTimeField(auto_now_add=True)
    widerrufen_am = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["pruefung", "nutzer"], name="unique_exam_release_user")]
        ordering = ["nutzer__last_name", "nutzer__first_name", "nutzer__username"]
        verbose_name = "Pruefungsfreigabe"
        verbose_name_plural = "Pruefungsfreigaben"

    @property
    def ist_aktiv(self):
        return self.widerrufen_am is None

    def __str__(self):
        return f"{self.pruefung} - {self.nutzer}"


class PruefungsbogenArchiv(models.Model):
    """Unveraenderliche Offline-Fassung mit der beim Erstellen gezogenen Fragenfolge."""
    pruefung = models.ForeignKey(Pruefung, on_delete=models.CASCADE, related_name="offline_boegen")
    erstellt_von = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    erstellt_am = models.DateTimeField(auto_now_add=True)
    fragen_reihenfolge = models.JSONField(default=list)
    teilnehmer_pdf = models.FileField(upload_to="pruefungsboegen/teilnehmer/")
    loesung_pdf = models.FileField(upload_to="pruefungsboegen/loesungen/")

    class Meta:
        ordering = ["-erstellt_am"]
        verbose_name = "Offline-Pruefungsbogen"
        verbose_name_plural = "Offline-Pruefungsboegen"

    def __str__(self):
        return f"{self.pruefung} – {self.erstellt_am:%d.%m.%Y %H:%M}"


class PruefungsVersuch(models.Model):
    class Status(models.TextChoices):
        LAUFEND = "LAUFEND", "Laufend"
        AUSSTEHEND = "AUSSTEHEND", "Freitext-Bewertung ausstehend"
        ABGESCHLOSSEN = "ABGESCHLOSSEN", "Abgeschlossen"
        ABGELAUFEN = "ABGELAUFEN", "Zeitlimit ueberschritten"
        ABGEBROCHEN = "ABGEBROCHEN", "Abgebrochen"

    nutzer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    pruefung = models.ForeignKey(Pruefung, on_delete=models.CASCADE)
    pruefungsversion = models.ForeignKey("Pruefungsversion", on_delete=models.PROTECT, null=True, blank=True, related_name="versuche")
    versuch_nummer = models.PositiveIntegerField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.LAUFEND)
    gestartet_am = models.DateTimeField(auto_now_add=True)
    aktive_sekunden = models.PositiveIntegerField(default=0)
    aktive_phase_begonnen_am = models.DateTimeField(null=True, blank=True)
    letzte_aktivitaet_am = models.DateTimeField(null=True, blank=True)
    pausiert_am = models.DateTimeField(null=True, blank=True)
    abgeschlossen_am = models.DateTimeField(null=True, blank=True)
    punkte_erreicht = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    punkte_gesamt = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    prozent_erreicht = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    bestanden = models.BooleanField(default=False)
    fragen_reihenfolge = models.JSONField(default=list)
    ergebnis_verschluesselt = EncryptedTextField(blank=True)
    einsehbar_bis = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["nutzer", "pruefung", "versuch_nummer"], name="unique_user_exam_attempt")]
        ordering = ["-gestartet_am"]
        verbose_name = "Pruefungsversuch"
        verbose_name_plural = "Pruefungsversuche"

    def __str__(self):
        return f"{self.nutzer} - {self.pruefung} #{self.versuch_nummer}"


class TeilnehmerAntwort(models.Model):
    versuch = models.ForeignKey(PruefungsVersuch, on_delete=models.CASCADE, related_name="antworten")
    frage = models.ForeignKey(Frage, on_delete=models.CASCADE)
    ausgewaehlte_antworten = models.ManyToManyField(Antwort, blank=True)
    freitext_antwort = models.TextField(blank=True)
    freitext_punkte = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    freitext_kommentar = models.TextField(blank=True)
    freitext_bewertet_von = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="bewertungen")
    freitext_bewertet_am = models.DateTimeField(null=True, blank=True)
    zuordnung_json = models.JSONField(null=True, blank=True)
    ist_korrekt = models.BooleanField(null=True)
    punkte_vergeben = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["versuch", "frage"], name="unique_attempt_question_answer")]
        verbose_name = "Teilnehmerantwort"
        verbose_name_plural = "Teilnehmerantworten"

    def __str__(self):
        return f"{self.versuch} - Frage {self.frage_id}"
