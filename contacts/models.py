from django.db import models

from common.models import OwnedModel, TimeStampedModel


class Contact(OwnedModel, TimeStampedModel):
    class EntityType(models.TextChoices):
        PERSON = "PERSON", "Persona"
        COMPANY = "COMPANY", "Azienda"
        HYBRID = "HYBRID", "Persona + Attivita"

    display_name = models.CharField(max_length=160)
    entity_type = models.CharField(max_length=10, choices=EntityType.choices, default=EntityType.PERSON)
    person_name = models.CharField(max_length=160, blank=True)
    business_name = models.CharField(max_length=160, blank=True)

    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=40, blank=True)
    website = models.URLField(blank=True)
    city = models.CharField(max_length=120, blank=True)

    role_customer = models.BooleanField(default=False)
    role_supplier = models.BooleanField(default=False)
    role_payee = models.BooleanField(default=False)
    role_income_source = models.BooleanField(default=False)

    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = [("owner", "display_name")]
        indexes = [
            models.Index(fields=["owner", "display_name"]),
            models.Index(fields=["owner", "is_active"]),
            models.Index(fields=["owner", "role_customer"]),
            models.Index(fields=["owner", "role_supplier"]),
            models.Index(fields=["owner", "role_payee"]),
            models.Index(fields=["owner", "role_income_source"]),
        ]

    def __str__(self):
        return self.display_name
