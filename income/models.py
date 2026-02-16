from django.db import models

from common.models import OwnedModel, TimeStampedModel


class IncomeSource(OwnedModel, TimeStampedModel):
    """
    Fonte di denaro: clienti, rimborsi, borse di studio, ecc.
    """
    name = models.CharField(max_length=160)
    website = models.URLField(blank=True)

    class Meta:
        unique_together = [("owner", "name")]
        indexes = [models.Index(fields=["owner", "name"])]

    def __str__(self):
        return self.name
