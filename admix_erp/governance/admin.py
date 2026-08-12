from django.contrib import admin
from django.utils.html import format_html
from simple_history.admin import SimpleHistoryAdmin

from .models import (
    AuditFinding,
    InternalAudit,
    InternalAuditPlan,
    ManagementReview,
    ManagementReviewAction,
    RiskItem,
)


@admin.register(RiskItem)
class RiskItemAdmin(SimpleHistoryAdmin):
    list_display = ("code", "title", "type", "category", "score", "residual",
                    "status", "owner", "review_date")
    list_filter = ("type", "category", "status")
    search_fields = ("code", "title", "description")

    @admin.display(description="İçsel skor")
    def score(self, obj: RiskItem) -> str:
        s = obj.inherent_score
        color = "#c62828" if s >= 15 else "#ed6c02" if s >= 8 else "#2e7d32"
        return format_html('<span style="color:{};font-weight:600">{}</span>', color, s)

    @admin.display(description="Kalıntı")
    def residual(self, obj: RiskItem):
        return obj.residual_score or "—"


@admin.register(InternalAuditPlan)
class InternalAuditPlanAdmin(admin.ModelAdmin):
    list_display = ("year", "approved_by", "approved_at")


class AuditFindingInline(admin.TabularInline):
    model = AuditFinding
    extra = 0
    fields = ("reference", "level", "description", "evidence", "ncr", "capa")
    autocomplete_fields = ("ncr", "capa")


@admin.register(InternalAudit)
class InternalAuditAdmin(SimpleHistoryAdmin):
    list_display = ("audit_number", "scope", "scheduled_date", "executed_date",
                    "lead_auditor", "status")
    list_filter = ("status", "plan")
    search_fields = ("audit_number", "scope")
    filter_horizontal = ("auditors",)
    inlines = [AuditFindingInline]


@admin.register(AuditFinding)
class AuditFindingAdmin(admin.ModelAdmin):
    list_display = ("audit", "level", "reference", "ncr", "capa")
    list_filter = ("level",)
    search_fields = ("audit__audit_number", "reference", "description")


class ManagementReviewActionInline(admin.TabularInline):
    model = ManagementReviewAction
    extra = 0
    fields = ("description", "assignee", "due_date", "status", "completed_at")


@admin.register(ManagementReview)
class ManagementReviewAdmin(SimpleHistoryAdmin):
    list_display = ("review_number", "meeting_date", "chairperson", "status")
    list_filter = ("status",)
    search_fields = ("review_number",)
    filter_horizontal = ("attendees",)
    inlines = [ManagementReviewActionInline]
    fieldsets = (
        (None, {"fields": ("review_number", "meeting_date", "chairperson", "attendees", "status")}),
        ("Girdiler (§9.3.2)", {"fields": (
            "input_previous_actions", "input_context_changes", "input_qms_performance",
            "input_customer_feedback", "input_process_performance", "input_ncr_capa",
            "input_audit_results", "input_supplier_performance", "input_resource_adequacy",
            "input_risks_opportunities", "input_improvement",
        )}),
        ("Çıktılar (§9.3.3)", {"fields": (
            "output_decisions", "output_resources", "output_improvement_actions",
        )}),
    )


# NCR/CAPA autocomplete için qms admin'lerinin search_fields'ları hazır olmalı
