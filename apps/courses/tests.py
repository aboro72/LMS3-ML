import json
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from django_quill.quill import Quill

from apps.accounts.models import Rolle, User, UserProfile
from apps.certificates.models import Zertifikat
from apps.courses.forms import BegleitmaterialForm, KursForm, LektionForm
from apps.courses.models import (
    Abschnitt,
    Einschreibung,
    Kurs,
    KursBewertung,
    Lektion,
    Lernpfad,
    LernpfadEinschreibung,
    LernpfadKurs,
)
from apps.exams.models import Antwort, Frage, Fragenkatalog, Pruefung, PruefungsVersuch, TeilnehmerAntwort, ZuordnungsPaar
from apps.exams.services import MaxVersucheErreicht, pruefe_zeitlimit, speichere_antwort, starte_pruefung, werte_versuch_aus
from apps.organisations.models import Einladung, Organisation
from apps.payments.models import AuditLog, OrganisationZahlungseinstellungen, Rechnung, Zahlung, Zahlungsart, Zahlungseinstellungen, Zahlungsstatus
from apps.payments.services import bestaetige_zahlung, erstelle_zahlung


def quill_text(text="Test"):
    return Quill(json.dumps({"delta": {"ops": [{"insert": text}]}, "html": f"<p>{text}</p>"}))


@override_settings(SINGLE_SYSTEM_MODE=False)
class BaseLmsTestCase(TestCase):
    def setUp(self):
        for role in Rolle.values:
            Group.objects.get_or_create(name=role)
        self.org = Organisation.objects.create(name="Demo Org", slug="demo-org", kontakt_email="org@example.com")
        self.other_org = Organisation.objects.create(name="Other Org", slug="other-org", kontakt_email="other@example.com")
        self.trainer = User.objects.create_user(username="trainer", email="trainer@example.com", password="pw")
        self.learner = User.objects.create_user(username="learner", email="learner@example.com", password="pw")
        self.other = User.objects.create_user(username="other", email="other@example.com", password="pw")
        self.org_admin = User.objects.create_user(username="orgadmin", email="admin@example.com", password="pw")
        self.superuser = User.objects.create_superuser(username="root", email="root@example.com", password="pw")
        UserProfile.objects.create(nutzer=self.org_admin, organisation=self.org, rolle=Rolle.ORG_ADMIN)
        UserProfile.objects.create(nutzer=self.trainer, organisation=self.org, rolle=Rolle.TRAINER)
        UserProfile.objects.create(nutzer=self.learner, organisation=self.org, rolle=Rolle.LEARNER)
        self.kurs = Kurs.objects.create(
            titel="Python Grundlagen",
            slug="python-grundlagen",
            beschreibung=quill_text("Python"),
            organisation=self.org,
            erstellt_von=self.trainer,
            niveau="anfaenger",
            ist_veroeffentlicht=True,
            ist_kostenlos=False,
            preis=Decimal("100.00"),
        )
        self.free_course = Kurs.objects.create(
            titel="Gratis Kurs",
            slug="gratis-kurs",
            beschreibung=quill_text("Gratis"),
            organisation=self.org,
            erstellt_von=self.trainer,
            niveau="anfaenger",
            ist_veroeffentlicht=True,
            ist_kostenlos=True,
            preis=Decimal("0.00"),
        )
        self.other_course = Kurs.objects.create(
            titel="Fremder Kurs",
            slug="fremder-kurs",
            beschreibung=quill_text("Fremd"),
            organisation=self.other_org,
            erstellt_von=self.other,
            niveau="mittel",
            ist_veroeffentlicht=True,
            ist_kostenlos=True,
            preis=Decimal("0.00"),
        )
        self.abschnitt = Abschnitt.objects.create(kurs=self.kurs, titel="Start", reihenfolge=1)

    def create_paid_payment(self, user=None, course=None, amount=Decimal("100.00")):
        user = user or self.learner
        course = course or self.kurs
        gebuehr = (amount * Decimal("0.15")).quantize(Decimal("0.01"))
        return Zahlung.objects.create(
            nutzer=user,
            kurs=course,
            trainer=course.erstellt_von,
            zahlungsart=Zahlungsart.BANK_TRANSFER,
            status=Zahlungsstatus.BEZAHLT,
            betrag_brutto=amount,
            plattform_gebuehr=gebuehr,
            trainer_anteil=amount - gebuehr,
        )

    def create_exam(self, typ=Frage.Typ.SINGLE_CHOICE, points=2, pass_percent=50):
        katalog = Fragenkatalog.objects.create(titel="Katalog", organisation=self.org, erstellt_von=self.trainer)
        frage = Frage.objects.create(
            fragenkatalog=katalog,
            typ=typ,
            fragetext=quill_text("Frage"),
            punkte=points,
        )
        pruefung = Pruefung.objects.create(
            titel="Pruefung",
            organisation=self.org,
            fragenkatalog=katalog,
            anzahl_fragen=1,
            bestehensgrenze_prozent=pass_percent,
            zufaellige_fragenreihenfolge=False,
            zufaellige_antwortfolge=False,
            ist_aktiv=True,
        )
        return katalog, frage, pruefung


class UploadValidationTests(BaseLmsTestCase):
    @override_settings(MAX_VIDEO_UPLOAD_MB=1, ALLOWED_VIDEO_EXTENSIONS=(".mp4", ".webm"))
    def test_video_upload_validation_rejects_wrong_extension(self):
        upload = SimpleUploadedFile("video.exe", b"x", content_type="application/octet-stream")
        form = LektionForm(data={"titel": "Video", "typ": Lektion.Typ.VIDEO, "reihenfolge": 1, "dauer_minuten": 5}, files={"datei": upload})
        self.assertFalse(form.is_valid())
        self.assertIn("Video-Upload", str(form.errors))

    @override_settings(MAX_VIDEO_UPLOAD_MB=1, ALLOWED_VIDEO_EXTENSIONS=(".mp4",))
    def test_video_upload_validation_rejects_too_large_file(self):
        upload = SimpleUploadedFile("video.mp4", b"x" * (1024 * 1024 + 1), content_type="video/mp4")
        form = LektionForm(data={"titel": "Video", "typ": Lektion.Typ.VIDEO, "reihenfolge": 1, "dauer_minuten": 5}, files={"datei": upload})
        self.assertFalse(form.is_valid())
        self.assertIn("maximal 1 MB", str(form.errors))

    @override_settings(MAX_DOCUMENT_UPLOAD_MB=1, ALLOWED_DOCUMENT_EXTENSIONS=(".pdf",))
    def test_document_upload_validation_accepts_allowed_extension(self):
        upload = SimpleUploadedFile("skript.pdf", b"pdf", content_type="application/pdf")
        form = BegleitmaterialForm(data={"titel": "Skript", "reihenfolge": 1}, files={"datei": upload})
        self.assertTrue(form.is_valid(), form.errors)


class CourseAccessAndReviewTests(BaseLmsTestCase):
    def test_reine_zertifikatspruefung_benoetigt_eine_zugeordnete_pruefung(self):
        katalog, _, pruefung = self.create_exam()
        form = KursForm(data={
            "titel": "Netzwerk Zertifikat",
            "beschreibung": "",
            "organisation": self.org.pk,
            "sprache": "de",
            "niveau": "anfaenger",
            "angebotstyp": Kurs.Angebotstyp.ZERTIFIKAT,
            "pruefung": pruefung.pk,
            "ist_kostenlos": "on",
            "preis": "0",
        })

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.save(commit=False).angebotstyp, Kurs.Angebotstyp.ZERTIFIKAT)

    def test_trainer_can_create_course_with_title_only_and_automatic_slug(self):
        self.client.force_login(self.trainer)

        response = self.client.post(
            reverse("trainer_course_create"),
            {
                "titel": "Netzwerk Technik",
                "organisation": self.org.pk,
                "sprache": "de",
                "niveau": "anfaenger",
                "angebotstyp": Kurs.Angebotstyp.KURS,
                "ist_kostenlos": "on",
                "preis": "0",
            },
        )

        kurs = Kurs.objects.get(titel="Netzwerk Technik")
        self.assertRedirects(response, reverse("trainer_course_edit", kwargs={"slug": "netzwerk-technik"}))
        self.assertEqual(kurs.slug, "netzwerk-technik")

    def test_unpaid_user_is_redirected_to_checkout_for_paid_course(self):
        self.client.force_login(self.learner)
        response = self.client.get(reverse("course_learn", kwargs={"slug": self.kurs.slug}))
        self.assertRedirects(response, reverse("course_checkout", kwargs={"slug": self.kurs.slug}))

    def test_free_course_is_immediately_accessible_and_enrolled(self):
        self.client.force_login(self.learner)
        response = self.client.get(reverse("course_learn", kwargs={"slug": self.free_course.slug}))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            Einschreibung.objects.filter(
                nutzer=self.learner,
                kurs=self.free_course,
                bezahlt=True,
            ).exists()
        )

    def test_paid_user_can_open_course_learning_view(self):
        Einschreibung.objects.create(nutzer=self.learner, kurs=self.kurs, bezahlt=True)
        self.client.force_login(self.learner)
        response = self.client.get(reverse("course_learn", kwargs={"slug": self.kurs.slug}))
        self.assertEqual(response.status_code, 200)

    def test_unenrolled_user_cannot_review_course(self):
        self.client.force_login(self.other)
        response = self.client.post(reverse("course_review", kwargs={"slug": self.kurs.slug}), {"sterne": 5, "kommentar": "Nope"})
        self.assertRedirects(response, reverse("course_detail", kwargs={"slug": self.kurs.slug}))
        self.assertFalse(KursBewertung.objects.filter(kurs=self.kurs, nutzer=self.other).exists())

    def test_enrolled_user_can_create_and_update_single_review(self):
        Einschreibung.objects.create(nutzer=self.learner, kurs=self.kurs, bezahlt=True)
        self.client.force_login(self.learner)
        self.client.post(reverse("course_review", kwargs={"slug": self.kurs.slug}), {"sterne": 4, "kommentar": "Gut"})
        self.client.post(reverse("course_review", kwargs={"slug": self.kurs.slug}), {"sterne": 5, "kommentar": "Besser"})
        self.assertEqual(KursBewertung.objects.filter(kurs=self.kurs, nutzer=self.learner).count(), 1)
        bewertung = KursBewertung.objects.get(kurs=self.kurs, nutzer=self.learner)
        self.assertEqual(bewertung.sterne, 5)
        self.assertEqual(bewertung.kommentar, "Besser")

    def test_trainer_course_list_only_contains_trainer_role_organisations(self):
        UserProfile.objects.create(nutzer=self.trainer, organisation=self.other_org, rolle=Rolle.LEARNER)
        self.client.force_login(self.trainer)
        response = self.client.get(reverse("trainer_course_list"))
        self.assertContains(response, self.kurs.titel)
        self.assertNotContains(response, self.other_course.titel)


class LearningPathTests(BaseLmsTestCase):
    def test_learning_path_enrollment_creates_path_and_free_course_enrollment_only(self):
        lernpfad = Lernpfad.objects.create(titel="Pfad", slug="pfad", organisation=self.org, erstellt_von=self.trainer, ist_veroeffentlicht=True)
        LernpfadKurs.objects.create(lernpfad=lernpfad, kurs=self.free_course, reihenfolge=1)
        LernpfadKurs.objects.create(lernpfad=lernpfad, kurs=self.kurs, reihenfolge=2)
        self.client.force_login(self.learner)
        response = self.client.post(reverse("learning_path_enroll", kwargs={"slug": lernpfad.slug}))
        self.assertRedirects(response, reverse("learning_path_detail", kwargs={"slug": lernpfad.slug}))
        self.assertTrue(LernpfadEinschreibung.objects.filter(nutzer=self.learner, lernpfad=lernpfad).exists())
        self.assertTrue(Einschreibung.objects.filter(nutzer=self.learner, kurs=self.free_course, bezahlt=True).exists())
        self.assertFalse(Einschreibung.objects.filter(nutzer=self.learner, kurs=self.kurs, bezahlt=True).exists())

    def test_learning_path_progress_counts_completed_courses(self):
        lernpfad = Lernpfad.objects.create(titel="Pfad", slug="pfad", organisation=self.org, erstellt_von=self.trainer, ist_veroeffentlicht=True)
        LernpfadKurs.objects.create(lernpfad=lernpfad, kurs=self.free_course, reihenfolge=1)
        LernpfadKurs.objects.create(lernpfad=lernpfad, kurs=self.kurs, reihenfolge=2)
        pfad_einschreibung = LernpfadEinschreibung.objects.create(nutzer=self.learner, lernpfad=lernpfad)
        Einschreibung.objects.create(nutzer=self.learner, kurs=self.free_course, bezahlt=True, fortschritt_prozent=100)
        Einschreibung.objects.create(nutzer=self.learner, kurs=self.kurs, bezahlt=True, fortschritt_prozent=50)
        self.assertEqual(pfad_einschreibung.fortschritt_prozent, 50)


class OrganisationInvitationTests(BaseLmsTestCase):
    def test_org_dashboard_counts_paid_revenue_and_platform_share(self):
        self.create_paid_payment()
        self.client.force_login(self.org_admin)
        response = self.client.get(reverse("org_admin_dashboard", kwargs={"slug": self.org.slug}))
        self.assertContains(response, "100,00 EUR")
        self.assertContains(response, "85,00 EUR")
        self.assertContains(response, "15,00 EUR")

    def test_invitation_acceptance_creates_profile_and_audit_log(self):
        invite = Einladung.objects.create(organisation=self.org, email=self.learner.email, rolle=Rolle.LEARNER, eingeladen_von=self.org_admin)
        self.client.force_login(self.learner)
        response = self.client.get(reverse("org_invitation_accept", kwargs={"token": invite.token}))
        self.assertRedirects(response, reverse("dashboard"))
        self.assertTrue(UserProfile.objects.filter(nutzer=self.learner, organisation=self.org, rolle=Rolle.LEARNER).exists())
        self.assertTrue(AuditLog.objects.filter(action="einladung_angenommen", object_id=str(invite.pk)).exists())
        invite.refresh_from_db()
        self.assertIsNotNone(invite.akzeptiert_am)

    def test_invitation_wrong_email_does_not_create_profile(self):
        invite = Einladung.objects.create(organisation=self.org, email="someone@example.com", rolle=Rolle.LEARNER, eingeladen_von=self.org_admin)
        self.client.force_login(self.learner)
        response = self.client.get(reverse("org_invitation_accept", kwargs={"token": invite.token}))
        self.assertRedirects(response, reverse("dashboard"))
        self.assertFalse(UserProfile.objects.filter(nutzer=self.learner, organisation=self.org, rolle=Rolle.LEARNER, eingeladen_am__gte=invite.erstellt_am).exists())

    def test_expired_invitation_does_not_create_profile(self):
        invite = Einladung.objects.create(
            organisation=self.other_org,
            email=self.learner.email,
            rolle=Rolle.LEARNER,
            eingeladen_von=self.org_admin,
            abgelaufen_am=timezone.now() - timedelta(days=1),
        )
        self.client.force_login(self.learner)
        self.client.get(reverse("org_invitation_accept", kwargs={"token": invite.token}))
        self.assertFalse(UserProfile.objects.filter(nutzer=self.learner, organisation=self.other_org, rolle=Rolle.LEARNER).exists())


class PaymentAndInvoiceTests(BaseLmsTestCase):
    def setUp(self):
        super().setUp()
        payment_settings = Zahlungseinstellungen.load()
        payment_settings.payment_aktiv = True
        payment_settings.ueberweisung_aktiv = True
        payment_settings.save()
        OrganisationZahlungseinstellungen.objects.create(
            organisation=self.org,
            payment_aktiv=True,
            ueberweisung_aktiv=True,
            iban="DE12345678901234567890",
        )

    def test_payment_split_uses_configured_commission(self):
        with override_settings(PLATFORM_COMMISSION_PERCENT=20):
            gebuehr, trainer = Zahlung.berechne_aufteilung(Decimal("49.99"))
        self.assertEqual(gebuehr, Decimal("10.00"))
        self.assertEqual(trainer, Decimal("39.99"))

    def test_create_payment_writes_audit_log(self):
        zahlung = erstelle_zahlung(self.kurs, self.learner, Zahlungsart.BANK_TRANSFER)
        self.assertEqual(zahlung.betrag_brutto, Decimal("100.00"))
        self.assertTrue(AuditLog.objects.filter(action="zahlung_erstellt", object_id=str(zahlung.pk)).exists())

    def test_payment_confirmation_creates_invoice_audit_and_enrollment(self):
        zahlung = Zahlung.objects.create(
            nutzer=self.learner,
            kurs=self.kurs,
            trainer=self.trainer,
            zahlungsart=Zahlungsart.BANK_TRANSFER,
            status=Zahlungsstatus.OFFEN,
            betrag_brutto=Decimal("100.00"),
            plattform_gebuehr=Decimal("15.00"),
            trainer_anteil=Decimal("85.00"),
        )
        bestaetige_zahlung(zahlung, provider_referenz="manual", actor=self.org_admin)
        zahlung.refresh_from_db()
        self.assertEqual(zahlung.status, Zahlungsstatus.BEZAHLT)
        self.assertTrue(Rechnung.objects.filter(zahlung=zahlung).exists())
        self.assertTrue(AuditLog.objects.filter(action="zahlung_bestaetigt", object_id=str(zahlung.pk)).exists())
        self.assertTrue(Einschreibung.objects.filter(nutzer=self.learner, kurs=self.kurs, bezahlt=True).exists())

    def test_payment_confirmation_is_idempotent(self):
        zahlung = self.create_paid_payment()
        Rechnung.objects.create(
            zahlung=zahlung,
            rechnungsnummer="RE-2099-0001",
            empfaenger_name="Learner",
            empfaenger_email="learner@example.com",
            betrag_netto=zahlung.betrag_brutto,
            betrag_brutto=zahlung.betrag_brutto,
        )
        bestaetige_zahlung(zahlung, provider_referenz="again", actor=self.org_admin)
        self.assertEqual(Rechnung.objects.filter(zahlung=zahlung).count(), 1)

    def test_invoice_detail_is_private_to_owner_but_superuser_can_access(self):
        zahlung = self.create_paid_payment()
        rechnung = Rechnung.objects.create(
            zahlung=zahlung,
            rechnungsnummer="RE-2099-0001",
            empfaenger_name="Learner",
            empfaenger_email="learner@example.com",
            betrag_netto=zahlung.betrag_brutto,
            betrag_brutto=zahlung.betrag_brutto,
        )
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(reverse("invoice_detail", kwargs={"rechnungsnummer": rechnung.rechnungsnummer})).status_code, 404)
        self.client.force_login(self.learner)
        self.assertEqual(self.client.get(reverse("invoice_detail", kwargs={"rechnungsnummer": rechnung.rechnungsnummer})).status_code, 200)
        self.client.force_login(self.superuser)
        self.assertEqual(self.client.get(reverse("invoice_detail", kwargs={"rechnungsnummer": rechnung.rechnungsnummer})).status_code, 200)

    def test_payment_settings_singleton_and_active_methods(self):
        settings_obj = Zahlungseinstellungen.load()
        settings_obj.stripe_aktiv = True
        settings_obj.paypal_aktiv = True
        settings_obj.save()
        self.assertEqual(Zahlungseinstellungen.objects.count(), 1)
        settings_obj.demo_autoconfirm = True
        settings_obj.save()
        with override_settings(DEBUG=True):
            methods = dict(Zahlungseinstellungen.load().aktive_zahlungsarten())
        self.assertIn(Zahlungsart.STRIPE, methods)
        self.assertIn(Zahlungsart.GOOGLE_PAY, methods)
        self.assertIn(Zahlungsart.PAYPAL, methods)
        self.assertIn(Zahlungsart.BANK_TRANSFER, methods)


class ExamServiceTests(BaseLmsTestCase):
    def test_single_choice_correct_attempt_passes_and_creates_certificate(self):
        _, frage, pruefung = self.create_exam(Frage.Typ.SINGLE_CHOICE, points=2, pass_percent=50)
        correct = Antwort.objects.create(frage=frage, antworttext="Richtig", ist_korrekt=True)
        Antwort.objects.create(frage=frage, antworttext="Falsch", ist_korrekt=False)
        versuch = starte_pruefung(pruefung, self.learner)
        speichere_antwort(versuch, frage, {"antworten": [correct.id]})
        werte_versuch_aus(versuch)
        versuch.refresh_from_db()
        self.assertTrue(versuch.bestanden)
        self.assertEqual(versuch.punkte_erreicht, Decimal("2.00"))
        self.assertTrue(Zertifikat.objects.filter(pruefungsversuch=versuch, nutzer=self.learner).exists())

    def test_multiple_choice_partial_answer_gets_zero_points(self):
        _, frage, pruefung = self.create_exam(Frage.Typ.MULTIPLE_CHOICE, points=3, pass_percent=50)
        correct1 = Antwort.objects.create(frage=frage, antworttext="A", ist_korrekt=True)
        Antwort.objects.create(frage=frage, antworttext="B", ist_korrekt=True)
        versuch = starte_pruefung(pruefung, self.learner)
        speichere_antwort(versuch, frage, {"antworten": [correct1.id]})
        werte_versuch_aus(versuch)
        versuch.refresh_from_db()
        self.assertFalse(versuch.bestanden)
        self.assertEqual(versuch.punkte_erreicht, Decimal("0.00"))

    def test_freetext_attempt_waits_for_manual_review_then_can_pass(self):
        _, frage, pruefung = self.create_exam(Frage.Typ.FREITEXT, points=5, pass_percent=50)
        versuch = starte_pruefung(pruefung, self.learner)
        speichere_antwort(versuch, frage, {"freitext_antwort": "Antwort"})
        werte_versuch_aus(versuch)
        versuch.refresh_from_db()
        self.assertEqual(versuch.status, PruefungsVersuch.Status.AUSSTEHEND)
        self.assertFalse(Zertifikat.objects.filter(pruefungsversuch=versuch).exists())
        antwort = TeilnehmerAntwort.objects.get(versuch=versuch, frage=frage)
        antwort.freitext_punkte = Decimal("4.00")
        antwort.save(update_fields=["freitext_punkte"])
        werte_versuch_aus(versuch)
        versuch.refresh_from_db()
        self.assertEqual(versuch.status, PruefungsVersuch.Status.ABGESCHLOSSEN)
        self.assertTrue(versuch.bestanden)
        self.assertTrue(Zertifikat.objects.filter(pruefungsversuch=versuch).exists())

    def test_matching_question_awards_partial_points(self):
        _, frage, pruefung = self.create_exam(Frage.Typ.ZUORDNUNG, points=4, pass_percent=50)
        pair1 = ZuordnungsPaar.objects.create(frage=frage, linkes_element="A", rechtes_element="1")
        pair2 = ZuordnungsPaar.objects.create(frage=frage, linkes_element="B", rechtes_element="2")
        versuch = starte_pruefung(pruefung, self.learner)
        speichere_antwort(versuch, frage, {"zuordnung_json": {str(pair1.id): "1", str(pair2.id): "wrong"}})
        werte_versuch_aus(versuch)
        versuch.refresh_from_db()
        self.assertEqual(versuch.punkte_erreicht, Decimal("2.00"))
        self.assertTrue(versuch.bestanden)

    def test_max_attempts_are_enforced(self):
        _, frage, pruefung = self.create_exam(Frage.Typ.SINGLE_CHOICE)
        pruefung.max_versuche = 1
        pruefung.save(update_fields=["max_versuche"])
        starte_pruefung(pruefung, self.learner)
        with self.assertRaises(MaxVersucheErreicht):
            starte_pruefung(pruefung, self.learner)

    def test_time_limit_marks_attempt_expired(self):
        _, frage, pruefung = self.create_exam(Frage.Typ.SINGLE_CHOICE)
        pruefung.zeitlimit_minuten = 1
        pruefung.save(update_fields=["zeitlimit_minuten"])
        versuch = starte_pruefung(pruefung, self.learner)
        PruefungsVersuch.objects.filter(pk=versuch.pk).update(
            gestartet_am=timezone.now() - timedelta(minutes=5),
            aktive_phase_begonnen_am=timezone.now() - timedelta(minutes=5),
        )
        versuch.refresh_from_db()
        self.assertTrue(pruefe_zeitlimit(versuch))
        versuch.refresh_from_db()
        self.assertEqual(versuch.status, PruefungsVersuch.Status.ABGELAUFEN)


class CertificateViewTests(BaseLmsTestCase):
    def test_certificate_verify_is_public(self):
        _, frage, pruefung = self.create_exam(Frage.Typ.SINGLE_CHOICE)
        versuch = PruefungsVersuch.objects.create(nutzer=self.learner, pruefung=pruefung, versuch_nummer=1, bestanden=True, status=PruefungsVersuch.Status.ABGESCHLOSSEN)
        zertifikat = Zertifikat.objects.create(nutzer=self.learner, pruefungsversuch=versuch)
        response = self.client.get(reverse("cert_verify", kwargs={"code": zertifikat.code}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, str(zertifikat.code))

    def test_certificate_download_only_for_owner(self):
        _, frage, pruefung = self.create_exam(Frage.Typ.SINGLE_CHOICE)
        versuch = PruefungsVersuch.objects.create(nutzer=self.learner, pruefung=pruefung, versuch_nummer=1, bestanden=True, status=PruefungsVersuch.Status.ABGESCHLOSSEN)
        zertifikat = Zertifikat.objects.create(nutzer=self.learner, pruefungsversuch=versuch)
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(reverse("cert_download", kwargs={"code": zertifikat.code})).status_code, 404)
        self.client.force_login(self.learner)
        with patch("apps.certificates.views.generiere_zertifikat_pdf", return_value=b"pdf"):
            response = self.client.get(reverse("cert_download", kwargs={"code": zertifikat.code}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
class TrainerExamTenantIsolationTests(BaseLmsTestCase):
    def test_trainer_catalog_list_only_contains_trainer_role_organisations(self):
        UserProfile.objects.create(nutzer=self.trainer, organisation=self.other_org, rolle=Rolle.LEARNER)
        own_catalog = Fragenkatalog.objects.create(titel="Eigener Katalog", organisation=self.org, erstellt_von=self.trainer)
        other_catalog = Fragenkatalog.objects.create(titel="Fremder Katalog", organisation=self.other_org, erstellt_von=self.other)
        self.client.force_login(self.trainer)
        response = self.client.get(reverse("trainer_catalog_list"))
        self.assertContains(response, own_catalog.titel)
        self.assertNotContains(response, other_catalog.titel)

    def test_trainer_exam_list_only_contains_trainer_role_organisations(self):
        UserProfile.objects.create(nutzer=self.trainer, organisation=self.other_org, rolle=Rolle.LEARNER)
        own_catalog = Fragenkatalog.objects.create(titel="Eigener Katalog", organisation=self.org, erstellt_von=self.trainer)
        other_catalog = Fragenkatalog.objects.create(titel="Fremder Katalog", organisation=self.other_org, erstellt_von=self.other)
        own_exam = Pruefung.objects.create(
            titel="Eigene Pruefung",
            organisation=self.org,
            fragenkatalog=own_catalog,
            anzahl_fragen=1,
            bestehensgrenze_prozent=50,
        )
        other_exam = Pruefung.objects.create(
            titel="Fremde Pruefung",
            organisation=self.other_org,
            fragenkatalog=other_catalog,
            anzahl_fragen=1,
            bestehensgrenze_prozent=50,
        )
        self.client.force_login(self.trainer)
        response = self.client.get(reverse("trainer_exam_list"))
        self.assertContains(response, own_exam.titel)
        self.assertNotContains(response, other_exam.titel)

class TrainerCourseEditIsolationTests(BaseLmsTestCase):
    def test_other_roles_cannot_read_or_modify_course(self):
        self.client.force_login(self.trainer)
        url = reverse("trainer_course_edit", kwargs={"slug": self.other_course.slug})
        for role in (Rolle.LEARNER, Rolle.ORG_ADMIN):
            with self.subTest(role=role):
                profile = UserProfile.objects.create(
                    nutzer=self.trainer, organisation=self.other_org, rolle=role,
                )
                self.assertEqual(self.client.get(url).status_code, 404)
                # A forged POST must not move the foreign course into an allowed organisation.
                response = self.client.post(url, {
                    "titel": "Uebernommener Kurs",
                    "slug": self.other_course.slug,
                    "beschreibung": json.dumps({"delta": "", "html": "<p>Test</p>"}),
                    "organisation": self.org.pk,
                    "sprache": "de",
                    "niveau": "mittel",
                    "ist_kostenlos": True,
                    "preis": "0.00",
                })
                self.assertEqual(response.status_code, 404)
                self.other_course.refresh_from_db()
                self.assertEqual(self.other_course.organisation_id, self.other_org.pk)
                self.assertEqual(self.other_course.titel, "Fremder Kurs")
                profile.delete()

    def test_inactive_trainer_cannot_edit_course(self):
        UserProfile.objects.create(
            nutzer=self.trainer, organisation=self.other_org, rolle=Rolle.TRAINER, aktiv=False,
        )
        self.client.force_login(self.trainer)
        url = reverse("trainer_course_edit", kwargs={"slug": self.other_course.slug})
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.post(url, {}).status_code, 404)

    def test_active_trainer_and_superuser_can_edit_course(self):
        self.client.force_login(self.trainer)
        url = reverse("trainer_course_edit", kwargs={"slug": self.kurs.slug})
        self.assertEqual(self.client.get(url).status_code, 200)
        self.client.force_login(self.superuser)
        url = reverse("trainer_course_edit", kwargs={"slug": self.other_course.slug})
        self.assertEqual(self.client.get(url).status_code, 200)


class EncryptedModelFieldTests(BaseLmsTestCase):
    def test_payment_settings_secrets_are_encrypted_in_database(self):
        settings_obj = Zahlungseinstellungen.load()
        settings_obj.stripe_secret_key = "sk_test_secret"
        settings_obj.paypal_secret = "paypal-secret"
        settings_obj.iban = "DE02120300000000202051"
        settings_obj.kontoinhaber = "Max Mustermann"
        settings_obj.save()

        loaded = Zahlungseinstellungen.load()
        self.assertEqual(loaded.stripe_secret_key, "sk_test_secret")
        self.assertEqual(loaded.paypal_secret, "paypal-secret")
        self.assertEqual(loaded.iban, "DE02120300000000202051")
        self.assertEqual(loaded.kontoinhaber, "Max Mustermann")

        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT stripe_secret_key, paypal_secret, iban, kontoinhaber FROM payments_zahlungseinstellungen WHERE id = %s",
                [settings_obj.pk],
            )
            raw = cursor.fetchone()
        self.assertTrue(raw[0].startswith("enc:v1:"))
        self.assertNotIn("sk_test_secret", raw[0])
        self.assertNotIn("DE02120300000000202051", raw[2])

    def test_payment_provider_reference_and_note_are_encrypted_in_database(self):
        zahlung = Zahlung.objects.create(
            nutzer=self.learner,
            kurs=self.kurs,
            trainer=self.trainer,
            zahlungsart=Zahlungsart.BANK_TRANSFER,
            status=Zahlungsstatus.OFFEN,
            betrag_brutto=Decimal("100.00"),
            plattform_gebuehr=Decimal("15.00"),
            trainer_anteil=Decimal("85.00"),
            provider_referenz="provider-123",
            betreiber_notiz="interne notiz",
        )
        loaded = Zahlung.objects.get(pk=zahlung.pk)
        self.assertEqual(loaded.provider_referenz, "provider-123")
        self.assertEqual(loaded.betreiber_notiz, "interne notiz")
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT provider_referenz, betreiber_notiz FROM payments_zahlung WHERE id = %s",
                [zahlung.pk],
            )
            raw = cursor.fetchone()
        self.assertTrue(raw[0].startswith("enc:v1:"))
        self.assertTrue(raw[1].startswith("enc:v1:"))
        self.assertNotIn("provider-123", raw[0])
        self.assertNotIn("interne notiz", raw[1])
