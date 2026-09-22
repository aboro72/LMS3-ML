from django.contrib.auth.models import AbstractUser
from django.db import models
from apps.security.fields import EncryptedCharField


class Rolle(models.TextChoices):
    SUPERADMIN = "superadmin", "Super-Admin"
    ORG_ADMIN = "org_admin", "Org-Admin"
    TRAINER = "trainer", "Trainer"
    EXAM_OPERATOR = "exam_operator", "Prüfungsoperator"
    EXAMINER = "examiner", "Pruefer"
    LEARNER = "learner", "Lernender"


class User(AbstractUser):
    avatar = models.ImageField(upload_to="avatars/", blank=True)
    bio = models.TextField(blank=True)
    bevorzugte_sprache = models.CharField(max_length=10, default="de")
    geburtsdatum = EncryptedCharField(blank=True, verbose_name="Geburtsdatum")
    geburtsort = EncryptedCharField(blank=True, verbose_name="Geburtsort")
    erstellt_am = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.get_full_name() or self.username


class UserProfile(models.Model):
    nutzer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="profile")
    organisation = models.ForeignKey("organisations.Organisation", on_delete=models.CASCADE)
    rolle = models.CharField(max_length=20, choices=Rolle.choices)
    eingeladen_am = models.DateTimeField(auto_now_add=True)
    aktiv = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["nutzer", "organisation", "rolle"],
                name="unique_user_organisation_role",
            )
        ]
        verbose_name = "Benutzerprofil"
        verbose_name_plural = "Benutzerprofile"

    def __str__(self):
        return f"{self.nutzer} - {self.organisation} ({self.get_rolle_display()})"
