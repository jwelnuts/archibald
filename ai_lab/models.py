from django.db import models

from common.models import OwnedModel, TimeStampedModel


class LabEntry(OwnedModel, TimeStampedModel):
    class Area(models.TextChoices):
        FOUNDATIONS = "FOUNDATIONS", "Fondamentali"
        PROMPTING = "PROMPTING", "Prompting"
        EMBEDDINGS = "EMBEDDINGS", "Embeddings"
        RAG = "RAG", "RAG"
        VECTOR_DB = "VECTOR_DB", "Vector DB"
        EXPERIMENT = "EXPERIMENT", "Esperimento libero"

    class Status(models.TextChoices):
        TODO = "TODO", "Da studiare"
        LEARNING = "LEARNING", "In studio"
        TESTING = "TESTING", "In test"
        APPLIED = "APPLIED", "Applicato"

    title = models.CharField(max_length=140)
    area = models.CharField(max_length=20, choices=Area.choices, default=Area.FOUNDATIONS)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.TODO)
    prompt = models.TextField(blank=True)
    result = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    next_step = models.CharField(max_length=220, blank=True)
    resource_url = models.URLField(blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["owner", "area", "status"]),
            models.Index(fields=["owner", "updated_at"]),
        ]

    def __str__(self):
        return self.title


class ArchibaldPersonaConfig(OwnedModel, TimeStampedModel):
    class Preset(models.TextChoices):
        OPERATIVE = "OPERATIVE", "Operativo diretto"
        BALANCED = "BALANCED", "Bilanciato"
        CLASSIC = "CLASSIC", "Magiordomo classico"

    class Verbosity(models.TextChoices):
        SHORT = "SHORT", "Breve"
        MEDIUM = "MEDIUM", "Media"
        LONG = "LONG", "Dettagliata"

    class ChallengeLevel(models.TextChoices):
        LOW = "LOW", "Delicato"
        NORMAL = "NORMAL", "Normale"
        HIGH = "HIGH", "Sfida attiva"

    class ActionMode(models.TextChoices):
        WHEN_USEFUL = "WHEN_USEFUL", "Azioni pratiche quando utili"
        ALWAYS = "ALWAYS", "Chiudi sempre con azioni pratiche"
        NEVER = "NEVER", "Niente lista azioni finali"

    preset = models.CharField(max_length=12, choices=Preset.choices, default=Preset.BALANCED)
    verbosity = models.CharField(max_length=10, choices=Verbosity.choices, default=Verbosity.MEDIUM)
    challenge_level = models.CharField(
        max_length=10,
        choices=ChallengeLevel.choices,
        default=ChallengeLevel.NORMAL,
    )
    action_mode = models.CharField(max_length=12, choices=ActionMode.choices, default=ActionMode.WHEN_USEFUL)
    avoid_pandering = models.BooleanField(default=True)
    include_reasoning = models.BooleanField(default=True)
    psych_validate_emotions = models.BooleanField(
        default=True,
        verbose_name="Validazione emotiva",
        help_text="Riconosce e legittima lo stato emotivo prima della soluzione.",
    )
    psych_assertive_boundaries = models.BooleanField(
        default=True,
        verbose_name="Confini assertivi",
        help_text="Protegge priorita e limiti, evitando dispersione.",
    )
    psych_socratic_questions = models.BooleanField(
        default=False,
        verbose_name="Domande socratiche",
        help_text="Fa domande guida per aumentare consapevolezza e chiarezza.",
    )
    psych_cognitive_reframe = models.BooleanField(
        default=True,
        verbose_name="Riformulazione cognitiva",
        help_text="Trasforma formulazioni bloccanti in letture piu utili.",
    )
    psych_bias_check = models.BooleanField(
        default=True,
        verbose_name="Controllo bias",
        help_text="Evidenzia catastrofismo, tutto-o-nulla e inferenze fragili.",
    )
    psych_self_efficacy = models.BooleanField(
        default=True,
        verbose_name="Rinforzo autoefficacia",
        help_text="Rinforza senso di competenza e capacita di azione dell'utente.",
    )
    psych_micro_actions = models.BooleanField(
        default=True,
        verbose_name="Micro-azioni immediate",
        help_text="Propone passi piccoli e concreti per sbloccarsi subito.",
    )
    psych_accountability_nudge = models.BooleanField(
        default=True,
        verbose_name="Nudge accountability",
        help_text="Introduce responsabilizzazione gentile e follow-up pratico.",
    )
    psych_decision_simplify = models.BooleanField(
        default=True,
        verbose_name="Semplificazione decisionale",
        help_text="Riduce il carico decisionale con opzioni nette e criteri chiari.",
    )
    psych_non_judgmental_tone = models.BooleanField(
        default=True,
        verbose_name="Tono non giudicante",
        help_text="Mantiene linguaggio rispettoso evitando colpevolizzazione.",
    )
    bias_catastrophizing = models.BooleanField(
        default=True,
        verbose_name="Catastrofismo",
        help_text="Individua scenari estremi non supportati dai dati.",
    )
    bias_all_or_nothing = models.BooleanField(
        default=True,
        verbose_name="Pensiero tutto-o-nulla",
        help_text="Riconosce valutazioni in bianco/nero prive di gradazioni.",
    )
    bias_overgeneralization = models.BooleanField(
        default=True,
        verbose_name="Sovrageneralizzazione",
        help_text="Evita conclusioni globali basate su pochi episodi.",
    )
    bias_mind_reading = models.BooleanField(
        default=True,
        verbose_name="Lettura del pensiero",
        help_text="Segnala assunzioni sulle intenzioni altrui senza evidenze.",
    )
    bias_negative_filtering = models.BooleanField(
        default=True,
        verbose_name="Filtro negativo",
        help_text="Contrasta il focus esclusivo sugli aspetti negativi.",
    )
    bias_confirmation_bias = models.BooleanField(
        default=True,
        verbose_name="Bias di conferma",
        help_text="Evidenzia selezione parziale delle prove a favore della tesi iniziale.",
    )
    custom_instructions = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["owner"],
                name="ai_lab_archibald_persona_owner_unique",
            ),
        ]
        indexes = [
            models.Index(fields=["owner", "updated_at"]),
        ]

    def __str__(self):
        return f"ArchibaldPersonaConfig({self.owner_id})"


class ArchibaldInstructionState(OwnedModel, TimeStampedModel):
    name = models.CharField(max_length=120)
    instructions_text = models.TextField(blank=True)

    class Meta:
        unique_together = [("owner", "name")]
        indexes = [
            models.Index(fields=["owner", "name"]),
            models.Index(fields=["owner", "updated_at"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.owner_id})"
