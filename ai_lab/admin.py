from django.contrib import admin

from .models import ArchibaldInstructionState, ArchibaldPersonaConfig, LabEntry


@admin.register(LabEntry)
class LabEntryAdmin(admin.ModelAdmin):
    list_display = ("id", "owner", "title", "area", "status", "updated_at")
    list_filter = ("area", "status")
    search_fields = ("title", "prompt", "notes", "result")


@admin.register(ArchibaldPersonaConfig)
class ArchibaldPersonaConfigAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "owner",
        "preset",
        "verbosity",
        "challenge_level",
        "action_mode",
        "updated_at",
    )
    list_filter = ("preset", "verbosity", "challenge_level", "action_mode")
    search_fields = ("owner__username", "custom_instructions")


@admin.register(ArchibaldInstructionState)
class ArchibaldInstructionStateAdmin(admin.ModelAdmin):
    list_display = ("id", "owner", "name", "updated_at")
    search_fields = ("owner__username", "name", "instructions_text")
