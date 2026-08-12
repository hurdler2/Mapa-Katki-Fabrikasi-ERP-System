"""Records app — Django admin (Case / RecordInstance / Evidence / Decision)."""
from __future__ import annotations

from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from .models import (
    Case,
    Decision,
    DecisionSignature,
    Evidence,
    RecordInstance,
)


@admin.register(Case)
class CaseAdmin(SimpleHistoryAdmin):
    list_display = ("case_id", "family", "title", "severity", "status",
                    "business_line", "gate", "detected_at")
    list_filter = ("family", "status", "severity", "business_line", "gate")
    search_fields = ("case_id", "title", "description")
    readonly_fields = ("created_at", "updated_at",
                       "contained_at", "scope_frozen_at", "classified_at",
                       "recovery_at", "reconciled_at", "capa_opened_at")


@admin.register(RecordInstance)
class RecordInstanceAdmin(SimpleHistoryAdmin):
    list_display = ("record_id", "controlled_code", "case", "status",
                    "preparer", "reviewer", "approver", "approved_at")
    list_filter = ("status", "controlled_code__function", "controlled_code__type")
    search_fields = ("record_id", "case__case_id",
                     "controlled_code__full_code")
    autocomplete_fields = ("controlled_code", "case",
                            "preparer", "reviewer", "approver")


@admin.register(Evidence)
class EvidenceAdmin(admin.ModelAdmin):
    list_display = ("evidence_id", "case", "record_instance", "kind",
                    "is_contemporaneous", "is_original", "collected_at")
    list_filter = ("kind", "is_contemporaneous", "is_original")
    search_fields = ("evidence_id", "title", "sha256")


class DecisionSignatureInline(admin.TabularInline):
    model = DecisionSignature
    extra = 0
    readonly_fields = ("signed_at",)


@admin.register(Decision)
class DecisionAdmin(SimpleHistoryAdmin):
    list_display = ("decision_id", "case", "level", "status",
                    "decision_maker", "decision_date")
    list_filter = ("level", "status", "veto_holder_role")
    search_fields = ("decision_id", "case__case_id", "rationale")
    inlines = [DecisionSignatureInline]


@admin.register(DecisionSignature)
class DecisionSignatureAdmin(admin.ModelAdmin):
    list_display = ("decision", "signer", "meaning", "signed_at", "ip_address")
    list_filter = ("meaning",)
    search_fields = ("decision__decision_id", "signer__username", "reason")
    readonly_fields = ("signed_at",)
