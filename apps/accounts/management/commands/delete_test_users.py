from django.core.management.base import BaseCommand, CommandError

from apps.accounts.management.commands.create_test_users import TEST_USERS
from apps.accounts.models import User


class Command(BaseCommand):
    help = "Loescht die von create_test_users verwalteten Testkonten."

    def add_arguments(self, parser):
        parser.add_argument(
            "--confirm",
            action="store_true",
            help="Loeschung tatsaechlich ausfuehren.",
        )

    def handle(self, *args, **options):
        usernames = [definition["username"] for definition in TEST_USERS]
        users = list(User.objects.filter(username__in=usernames).order_by("username"))

        if not users:
            self.stdout.write(self.style.WARNING("Keine verwalteten Testkonten gefunden."))
            return

        self.stdout.write("Gefundene Testkonten:")
        for user in users:
            self.stdout.write(f"- {user.username} ({user.email})")

        if not options["confirm"]:
            raise CommandError(
                "Nur Vorschau. Zum Loeschen den Befehl erneut mit --confirm ausfuehren."
            )

        count = len(users)
        User.objects.filter(pk__in=[user.pk for user in users]).delete()
        self.stdout.write(self.style.SUCCESS(f"{count} Testkonto/konten geloescht."))
