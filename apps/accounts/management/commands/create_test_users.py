from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

from apps.accounts.models import Rolle, User, UserProfile
from apps.organisations.models import Organisation


TEST_USERS = [
    {
        "username": "superadmin",
        "email": "superadmin@example.com",
        "first_name": "Super",
        "last_name": "Admin",
        "rolle": Rolle.SUPERADMIN,
        "superuser": True,
    },
    {
        "username": "trainer",
        "email": "trainer@example.com",
        "first_name": "Test",
        "last_name": "Trainer",
        "rolle": Rolle.TRAINER,
    },
    {
        "username": "exam_operator",
        "email": "exam_operator@example.com",
        "first_name": "Test",
        "last_name": "Prüfungsoperator",
        "rolle": Rolle.EXAM_OPERATOR,
    },
    {
        "username": "examiner",
        "email": "examiner@example.com",
        "first_name": "Test",
        "last_name": "Prüfer",
        "rolle": Rolle.EXAMINER,
    },
    {
        "username": "learner",
        "email": "learner@example.com",
        "first_name": "Test",
        "last_name": "Lernender",
        "rolle": Rolle.LEARNER,
    },
]


class Command(BaseCommand):
    help = "Legt sichere Testbenutzer fuer das ML-Einzelsystem an oder aktualisiert sie."

    def add_arguments(self, parser):
        parser.add_argument(
            "--password",
            default="ChangeMe123!",
            help="Passwort fuer alle Testbenutzer (Standard: ChangeMe123!).",
        )

    def handle(self, *args, **options):
        password = options["password"]
        organisation, _ = Organisation.objects.get_or_create(
            slug="ml-gruppe",
            defaults={
                "name": "ML Gruppe",
                "kontakt_email": "noreply@ml-gruppe.de",
            },
        )
        for rolle in Rolle:
            Group.objects.get_or_create(name=rolle.value)

        for definition in TEST_USERS:
            user, created = User.objects.get_or_create(
                username=definition["username"],
                defaults={
                    "email": definition["email"],
                    "first_name": definition["first_name"],
                    "last_name": definition["last_name"],
                },
            )
            user.email = definition["email"]
            user.first_name = definition["first_name"]
            user.last_name = definition["last_name"]
            user.is_staff = bool(definition.get("superuser"))
            user.is_superuser = bool(definition.get("superuser"))
            user.set_password(password)
            user.save()
            user.groups.add(Group.objects.get(name=definition["rolle"].value))
            if not definition.get("superuser"):
                UserProfile.objects.get_or_create(
                    nutzer=user,
                    organisation=organisation,
                    rolle=definition["rolle"],
                    defaults={"aktiv": True},
                )
            state = "angelegt" if created else "aktualisiert"
            self.stdout.write(f"{definition['username']}: {state} ({definition['rolle'].label})")

        self.stdout.write(self.style.SUCCESS("ML-Testbenutzer sind bereit."))
