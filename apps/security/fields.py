from django.db import models

from .crypto import decrypt_text, encrypt_text, is_encrypted_value


class EncryptedTextField(models.TextField):
    description = "TextField encrypted with FIELD_ENCRYPTION_KEY"

    def from_db_value(self, value, expression, connection):
        return decrypt_text(value)

    def to_python(self, value):
        value = super().to_python(value)
        return decrypt_text(value)

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        return encrypt_text(value)

    def value_to_string(self, obj):
        value = self.value_from_object(obj)
        return "" if value is None else str(value)


class EncryptedCharField(EncryptedTextField):
    description = "CharField stored encrypted with FIELD_ENCRYPTION_KEY"

    def __init__(self, *args, **kwargs):
        kwargs.pop("max_length", None)
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        kwargs.pop("max_length", None)
        return name, path, args, kwargs

    def get_internal_type(self):
        return "TextField"