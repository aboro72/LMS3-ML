from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase, TestCase, override_settings

from .crypto import decrypt_text, encrypt_text, generate_field_encryption_key, is_encrypted_value


class FieldEncryptionTests(SimpleTestCase):
    def test_generate_key_can_encrypt_and_decrypt(self):
        key = generate_field_encryption_key()
        with override_settings(FIELD_ENCRYPTION_KEY=key):
            encrypted = encrypt_text("Max Mustermann")
            self.assertTrue(is_encrypted_value(encrypted))
            self.assertNotIn("Max Mustermann", encrypted)
            self.assertEqual(decrypt_text(encrypted), "Max Mustermann")

    def test_empty_values_are_preserved(self):
        key = generate_field_encryption_key()
        with override_settings(FIELD_ENCRYPTION_KEY=key):
            self.assertEqual(encrypt_text(""), "")
            self.assertIsNone(encrypt_text(None))
            self.assertEqual(decrypt_text(""), "")
            self.assertIsNone(decrypt_text(None))

    def test_encrypt_is_idempotent_for_existing_ciphertext(self):
        key = generate_field_encryption_key()
        with override_settings(FIELD_ENCRYPTION_KEY=key):
            encrypted = encrypt_text("secret")
            self.assertEqual(encrypt_text(encrypted), encrypted)

    def test_missing_key_raises_clear_error(self):
        with override_settings(FIELD_ENCRYPTION_KEY=""):
            with self.assertRaises(ImproperlyConfigured):
                encrypt_text("secret")

    def test_invalid_key_raises_clear_error(self):
        with override_settings(FIELD_ENCRYPTION_KEY="not-a-fernet-key"):
            with self.assertRaises(ImproperlyConfigured):
                encrypt_text("secret")

class ProductionReadinessTests(TestCase):
    @override_settings(PRODUCTION=False, FIELD_ENCRYPTION_KEY="j3BQv31KKjfteqM5y4LTfhQf3ru51qCz_02cxydQaDI=", ALLOWED_HOSTS=["*"], EMAIL_BACKEND="django.core.mail.backends.console.EmailBackend")
    def test_development_configuration_is_rejected(self):
        from .checks import production_readiness_check
        ids = {issue.id for issue in production_readiness_check(None)}
        self.assertTrue({"aborolms.E010", "aborolms.E011", "aborolms.E012", "aborolms.W010"} <= ids)

    @override_settings(PRODUCTION=True, FIELD_ENCRYPTION_KEY="", ALLOWED_HOSTS=["lms.example.com"], EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend", EMAIL_HOST="smtp.example.com", EMAIL_USE_TLS=True, EMAIL_USE_SSL=True)
    def test_conflicting_smtp_modes_are_rejected(self):
        from .checks import production_readiness_check
        self.assertIn("aborolms.E014", {issue.id for issue in production_readiness_check(None)})

    @override_settings(SECURE_SSL_REDIRECT=True, SECURE_HSTS_SECONDS=3600, SECURE_CONTENT_TYPE_NOSNIFF=True, SECURE_REFERRER_POLICY="same-origin", ALLOWED_HOSTS=["testserver"])
    def test_https_redirect_and_security_headers(self):
        from django.http import HttpResponse
        from django.middleware.security import SecurityMiddleware
        from django.test import RequestFactory
        middleware = SecurityMiddleware(lambda request: HttpResponse("ok"))
        factory = RequestFactory()
        response = middleware(factory.get("/"))
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response["Location"], "https://testserver/")
        response = middleware(factory.get("/", secure=True))
        self.assertEqual(response["Strict-Transport-Security"], "max-age=3600")
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")
        self.assertEqual(response["Referrer-Policy"], "same-origin")


    @override_settings(DEBUG=False, DEMO_DATA_ALLOW_PRODUCTION=False)
    def test_demo_command_is_blocked_before_database_writes(self):
        from django.core.management import call_command, CommandError
        with self.assertRaisesMessage(CommandError, "Entwicklungsumgebung"):
            call_command("create_demo_data")
