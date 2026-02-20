from django import forms

from .models import ArchibaldPersonaConfig, LabEntry


class LabEntryForm(forms.ModelForm):
    class Meta:
        model = LabEntry
        fields = (
            "title",
            "area",
            "status",
            "prompt",
            "result",
            "notes",
            "next_step",
            "resource_url",
        )


class ArchibaldPersonaConfigForm(forms.ModelForm):
    CORE_FIELDS = (
        "preset",
        "verbosity",
        "challenge_level",
        "action_mode",
        "custom_instructions",
    )
    PSYCHOLOGICAL_BOOLEAN_FIELDS = (
        "avoid_pandering",
        "include_reasoning",
        "psych_validate_emotions",
        "psych_assertive_boundaries",
        "psych_socratic_questions",
        "psych_cognitive_reframe",
        "psych_bias_check",
        "psych_self_efficacy",
        "psych_micro_actions",
        "psych_accountability_nudge",
        "psych_decision_simplify",
        "psych_non_judgmental_tone",
    )

    class Meta:
        model = ArchibaldPersonaConfig
        fields = (
            "preset",
            "verbosity",
            "challenge_level",
            "action_mode",
            "custom_instructions",
            "avoid_pandering",
            "include_reasoning",
            "psych_validate_emotions",
            "psych_assertive_boundaries",
            "psych_socratic_questions",
            "psych_cognitive_reframe",
            "psych_bias_check",
            "psych_self_efficacy",
            "psych_micro_actions",
            "psych_accountability_nudge",
            "psych_decision_simplify",
            "psych_non_judgmental_tone",
        )
        widgets = {
            "custom_instructions": forms.Textarea(
                attrs={
                    "rows": 5,
                    "placeholder": "Regole personali extra (es: evita frasi troppo accondiscendenti, vai subito al punto).",
                }
            ),
        }


class ArchibaldSandboxPromptForm(forms.Form):
    prompt = forms.CharField(
        label="Prompt di test",
        widget=forms.Textarea(
            attrs={
                "rows": 5,
                "placeholder": "Scrivi qui un prompt per verificare il nuovo stile di Archibald.",
            }
        ),
    )
