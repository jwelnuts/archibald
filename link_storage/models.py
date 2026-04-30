from django.db import models

from common.models import OwnedModel, TimeStampedModel


class Link(OwnedModel, TimeStampedModel):
    """
    Specializzazione di MemoryStockItem per i link/bookmark.
    Un Link può essere creato standalone oppure associato a un MemoryStockItem
    (es. quando arriva da email processing).
    """
    
    # Collegamento opzionale al MemoryStockItem "padre"
    # Se presente, il Link è una specializzazione di quel MemoryStockItem
    memory_item = models.OneToOneField(
        "memory_stock.MemoryStockItem",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="link_specialization"
    )
    
    url = models.CharField(max_length=160)
    CATEGORY_CHOICES = [
        ("TECNOLOGIA", "Tecnologia"),
        ("SALUTE", "Salute"),
        ("SPORT", "Sport"),
        ("INTRATTENIMENTO", "Intrattenimento"),
        ("LAVORO", "Lavoro"),
        ("STUDIO", "Studio"),
        ("ALTRI", "Altri"),
    ]
    category = models.CharField(max_length=15, choices=CATEGORY_CHOICES, blank=True)
    importance = models.IntegerField(default=1)  # 1-5 scala
    note = models.TextField(blank=True)
    
    # Metadati estratti automaticamente
    title_extracted = models.CharField(max_length=255, blank=True)
    description_extracted = models.TextField(blank=True)
    favicon_url = models.URLField(blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["owner", "created_at"]),
            models.Index(fields=["owner", "category"]),
            models.Index(fields=["owner", "importance"]),
        ]

    def __str__(self):
        return str(self.url)
