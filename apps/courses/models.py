from django.conf import settings
from django.db import models
from django_quill.fields import QuillField


class Niveau(models.TextChoices):
    ANFAENGER = "anfaenger", "Anfaenger"
    MITTEL = "mittel", "Mittel"
    FORTGESCHRITTEN = "fortgeschritten", "Fortgeschritten"


class KursKategorie(models.Model):
    organisation = models.ForeignKey("organisations.Organisation", on_delete=models.CASCADE, related_name="kurskategorien")
    name = models.CharField(max_length=120)
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.CASCADE, related_name="unterkategorien")

    class Meta:
        ordering = ["parent__name", "name"]
        constraints = [models.UniqueConstraint(fields=["organisation", "parent", "name"], name="unique_course_category_per_org_parent")]
        verbose_name = "Kurskategorie"
        verbose_name_plural = "Kurskategorien"

    def __str__(self):
        return f"{self.parent.name} / {self.name}" if self.parent else self.name

    @classmethod
    def standardkategorien_anlegen(cls, organisation):
        defaults = {
            "IT": ["Softwareentwicklung", "Administration", "Sonstiges"],
            "Wirtschaft": ["Büro und Verwaltung", "Finanzen", "Sonstiges"],
            "Sprachen": ["Deutsch", "Englisch", "Sonstige Sprachen"],
            "Persönliche Entwicklung": ["Kommunikation", "Führung", "Sonstiges"],
            "Gesundheit und Sicherheit": ["Arbeitssicherheit", "Gesundheit", "Sonstiges"],
            "Sonstige": [],
        }
        for name, children in defaults.items():
            parent, _ = cls.objects.get_or_create(organisation=organisation, parent=None, name=name)
            for child in children:
                cls.objects.get_or_create(organisation=organisation, parent=parent, name=child)


class Kurs(models.Model):
    class Angebotstyp(models.TextChoices):
        KURS = "KURS", "Kompletter Kurs"
        ZERTIFIKAT = "ZERTIFIKAT", "Reine Zertifikatsprüfung"

    titel = models.CharField(max_length=300)
    slug = models.SlugField(unique=True)
    beschreibung = QuillField(blank=True)
    thumbnail = models.ImageField(upload_to="thumbnails/", blank=True)
    organisation = models.ForeignKey("organisations.Organisation", on_delete=models.CASCADE)
    kategorie = models.ForeignKey(KursKategorie, null=True, blank=True, on_delete=models.SET_NULL, related_name="kurse")
    erstellt_von = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    sprache = models.CharField(max_length=10, default="de")
    niveau = models.CharField(max_length=20, choices=Niveau.choices)
    angebotstyp = models.CharField(max_length=12, choices=Angebotstyp.choices, default=Angebotstyp.KURS)
    ist_veroeffentlicht = models.BooleanField(default=False)
    ist_kostenlos = models.BooleanField(default=True)
    preis = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    pruefung = models.ForeignKey(
        "exams.Pruefung",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="kurse",
    )
    erstellt_am = models.DateTimeField(auto_now_add=True)
    geaendert_am = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["titel"]
        verbose_name = "Kurs"
        verbose_name_plural = "Kurse"

    def __str__(self):
        return self.titel

    @property
    def ist_zertifikatspruefung(self):
        # A certificate course without a linked exam is invalid legacy data.
        # Treat it as a normal course in read-only views so navigation never
        # tries to reverse an exam URL with an empty primary key.
        return self.angebotstyp == self.Angebotstyp.ZERTIFIKAT and self.pruefung_id is not None

    @property
    def dauer_minuten(self):
        return sum(lektion.dauer_minuten for abschnitt in self.abschnitte.all() for lektion in abschnitt.lektionen.all())


class Abschnitt(models.Model):
    kurs = models.ForeignKey(Kurs, on_delete=models.CASCADE, related_name="abschnitte")
    titel = models.CharField(max_length=200)
    reihenfolge = models.PositiveIntegerField(default=0)
    ist_veroeffentlicht = models.BooleanField(default=True)

    class Meta:
        ordering = ["reihenfolge"]
        verbose_name = "Abschnitt"
        verbose_name_plural = "Abschnitte"

    def __str__(self):
        return f"{self.kurs}: {self.titel}"


class Lektion(models.Model):
    class Typ(models.TextChoices):
        VIDEO = "VIDEO", "Video"
        DOKUMENT = "DOKUMENT", "Dokument"
        TEXT = "TEXT", "Text/HTML"
        QUIZ = "QUIZ", "Mini-Quiz"

    abschnitt = models.ForeignKey(Abschnitt, on_delete=models.CASCADE, related_name="lektionen")
    titel = models.CharField(max_length=200)
    typ = models.CharField(max_length=20, choices=Typ.choices)
    reihenfolge = models.PositiveIntegerField(default=0)
    inhalt = QuillField(blank=True)
    video_url = models.URLField(blank=True)
    datei = models.FileField(upload_to="lektionen/", blank=True)
    video_thumbnail = models.ImageField(upload_to="lektion-thumbnails/", blank=True)
    dauer_minuten = models.PositiveIntegerField(default=0)
    ist_vorschau = models.BooleanField(default=False)

    class Meta:
        ordering = ["reihenfolge"]
        verbose_name = "Lektion"
        verbose_name_plural = "Lektionen"

    def __str__(self):
        return f"{self.abschnitt}: {self.titel}"


class Begleitmaterial(models.Model):
    lektion = models.ForeignKey(Lektion, on_delete=models.CASCADE, related_name="materialien")
    titel = models.CharField(max_length=200)
    datei = models.FileField(upload_to="begleitmaterial/")
    reihenfolge = models.PositiveIntegerField(default=0)
    erstellt_am = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["reihenfolge", "titel"]
        verbose_name = "Begleitmaterial"
        verbose_name_plural = "Begleitmaterialien"

    def __str__(self):
        return f"{self.lektion}: {self.titel}"


class Uebungsfrage(models.Model):
    lektion = models.ForeignKey(Lektion, on_delete=models.CASCADE, related_name="uebungsfragen")
    frage = models.TextField()
    erklaerung = models.TextField(blank=True)
    reihenfolge = models.PositiveIntegerField(default=0)
    aktiv = models.BooleanField(default=True)

    class Meta:
        ordering = ["reihenfolge", "id"]
        verbose_name = "Uebungsfrage"
        verbose_name_plural = "Uebungsfragen"

    def __str__(self):
        return f"{self.lektion}: {self.frage[:80]}"


class Uebungsantwort(models.Model):
    frage = models.ForeignKey(Uebungsfrage, on_delete=models.CASCADE, related_name="antworten")
    antwort = models.CharField(max_length=500)
    ist_korrekt = models.BooleanField(default=False)
    reihenfolge = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["reihenfolge", "id"]
        verbose_name = "Uebungsantwort"
        verbose_name_plural = "Uebungsantworten"

    def __str__(self):
        return self.antwort[:80]


class Einschreibung(models.Model):
    nutzer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    kurs = models.ForeignKey(Kurs, on_delete=models.CASCADE)
    eingeschrieben_am = models.DateTimeField(auto_now_add=True)
    abgeschlossen_am = models.DateTimeField(null=True, blank=True)
    fortschritt_prozent = models.PositiveIntegerField(default=0)
    bezahlt = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["nutzer", "kurs"], name="unique_user_course_enrollment")
        ]
        verbose_name = "Einschreibung"
        verbose_name_plural = "Einschreibungen"

    def __str__(self):
        return f"{self.nutzer} - {self.kurs}"

    def aktualisiere_fortschritt(self):
        lektionen_gesamt = Lektion.objects.filter(abschnitt__kurs=self.kurs).count()
        if lektionen_gesamt == 0:
            self.fortschritt_prozent = 0
        else:
            abgeschlossen = self.lektionsfortschritt_set.count()
            self.fortschritt_prozent = round((abgeschlossen / lektionen_gesamt) * 100)
        self.save(update_fields=["fortschritt_prozent"])


class LektionsFortschritt(models.Model):
    einschreibung = models.ForeignKey(Einschreibung, on_delete=models.CASCADE)
    lektion = models.ForeignKey(Lektion, on_delete=models.CASCADE)
    abgeschlossen_am = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["einschreibung", "lektion"], name="unique_lesson_progress")
        ]
        verbose_name = "Lektionsfortschritt"
        verbose_name_plural = "Lektionsfortschritte"

    def __str__(self):
        return f"{self.einschreibung} - {self.lektion}"

class KursBewertung(models.Model):
    kurs = models.ForeignKey(Kurs, on_delete=models.CASCADE, related_name="bewertungen")
    nutzer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="kursbewertungen")
    sterne = models.PositiveSmallIntegerField(default=5)
    kommentar = models.TextField(blank=True)
    erstellt_am = models.DateTimeField(auto_now_add=True)
    geaendert_am = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["kurs", "nutzer"], name="unique_course_review_user"),
            models.CheckConstraint(condition=models.Q(sterne__gte=1, sterne__lte=5), name="course_review_stars_1_5"),
        ]
        ordering = ["-erstellt_am"]
        verbose_name = "Kursbewertung"
        verbose_name_plural = "Kursbewertungen"

    def __str__(self):
        return f"{self.kurs} - {self.nutzer}: {self.sterne}/5"


class Lernpfad(models.Model):
    titel = models.CharField(max_length=300)
    slug = models.SlugField(unique=True)
    beschreibung = models.TextField(blank=True)
    organisation = models.ForeignKey("organisations.Organisation", on_delete=models.CASCADE, related_name="lernpfade")
    erstellt_von = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    ist_veroeffentlicht = models.BooleanField(default=False)
    erstellt_am = models.DateTimeField(auto_now_add=True)
    geaendert_am = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["titel"]
        verbose_name = "Lernpfad"
        verbose_name_plural = "Lernpfade"

    def __str__(self):
        return self.titel


class LernpfadKurs(models.Model):
    lernpfad = models.ForeignKey(Lernpfad, on_delete=models.CASCADE, related_name="pfad_kurse")
    kurs = models.ForeignKey(Kurs, on_delete=models.CASCADE, related_name="lernpfad_links")
    reihenfolge = models.PositiveIntegerField(default=0)
    pflichtkurs = models.BooleanField(default=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["lernpfad", "kurs"], name="unique_learning_path_course")]
        ordering = ["reihenfolge", "kurs__titel"]
        verbose_name = "Lernpfad-Kurs"
        verbose_name_plural = "Lernpfad-Kurse"

    def __str__(self):
        return f"{self.lernpfad}: {self.kurs}"


class LernpfadEinschreibung(models.Model):
    nutzer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="lernpfad_einschreibungen")
    lernpfad = models.ForeignKey(Lernpfad, on_delete=models.CASCADE, related_name="einschreibungen")
    eingeschrieben_am = models.DateTimeField(auto_now_add=True)
    abgeschlossen_am = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["nutzer", "lernpfad"], name="unique_user_learning_path")]
        ordering = ["-eingeschrieben_am"]
        verbose_name = "Lernpfad-Einschreibung"
        verbose_name_plural = "Lernpfad-Einschreibungen"

    def __str__(self):
        return f"{self.nutzer} - {self.lernpfad}"

    @property
    def fortschritt_prozent(self):
        kurs_ids = list(self.lernpfad.pfad_kurse.values_list("kurs_id", flat=True))
        if not kurs_ids:
            return 0
        abgeschlossene = Einschreibung.objects.filter(
            nutzer=self.nutzer,
            kurs_id__in=kurs_ids,
            fortschritt_prozent__gte=100,
        ).count()
        return round((abgeschlossene / len(kurs_ids)) * 100)
