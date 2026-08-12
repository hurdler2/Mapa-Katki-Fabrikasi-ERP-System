from django.contrib import admin
from django.utils.html import format_html
from simple_history.admin import SimpleHistoryAdmin

from .models import (
    EnvironmentalAspect,
    EnvironmentalMeasurement,
    ExposureMeasurement,
    Incident,
    JSAStep,
    JobSafetyAnalysis,
    LegalRequirement,
    PPEIssuance,
    PPEItem,
    WorkPermit,
)


@admin.register(Incident)
class IncidentAdmin(SimpleHistoryAdmin):
    list_display = ("incident_number", "type", "severity_c", "occurred_at",
                    "location", "reported_by", "status", "days_lost")
    list_filter = ("type", "severity", "status")
    search_fields = ("incident_number", "location", "description")
    filter_horizontal = ("affected_persons",)
    date_hierarchy = "occurred_at"

    fieldsets = (
        (None, {"fields": ("incident_number", "type", "severity", "occurred_at",
                           "location", "reported_by", "investigator", "status", "closed_at")}),
        ("Açıklama", {"fields": ("description", "immediate_actions")}),
        ("Personel etkisi", {"fields": ("affected_persons", "body_parts", "days_lost")}),
        ("Çevresel etki", {"classes": ("collapse",),
                            "fields": ("environmental_medium", "spilled_material",
                                       "spilled_quantity_kg")}),
        ("Kök neden & bağlantılar", {"fields": ("root_cause_analysis", "ncr", "capa")}),
    )

    @admin.display(description="Ağırlık")
    def severity_c(self, obj):
        c = {"FIRST_AID": "#0369a1", "MEDICAL": "#0891b2", "MINOR": "#6b7280",
             "SIGNIFICANT": "#ed6c02", "LOST_TIME": "#ed6c02",
             "MAJOR": "#c62828", "SERIOUS": "#c62828", "FATAL": "#991b1b"}.get(
            obj.severity, "#000")
        return format_html('<span style="color:{};font-weight:600">{}</span>',
                           c, obj.get_severity_display())


@admin.register(PPEItem)
class PPEItemAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "category", "standard",
                    "replacement_days", "stock_quantity", "is_active")
    list_filter = ("category", "is_active")
    search_fields = ("code", "name", "standard")


@admin.register(PPEIssuance)
class PPEIssuanceAdmin(admin.ModelAdmin):
    list_display = ("user", "item", "quantity", "issued_at", "replace_by",
                    "returned_at", "status")
    list_filter = ("status", "item__category")
    search_fields = ("user__username", "item__code")
    date_hierarchy = "issued_at"


@admin.register(ExposureMeasurement)
class ExposureMeasurementAdmin(admin.ModelAdmin):
    list_display = ("measurement_number", "chemical_profile", "person", "area",
                    "route", "measured_value", "unit", "above_limit_c", "measured_at")
    list_filter = ("route", "method")
    search_fields = ("measurement_number", "person__username", "area")
    date_hierarchy = "measured_at"

    @admin.display(description="Limit üzeri mi?")
    def above_limit_c(self, obj):
        v = obj.above_limit
        if v is None:
            return "—"
        color = "#c62828" if v else "#2e7d32"
        text = "EVET" if v else "hayır"
        return format_html('<span style="color:{};font-weight:600">{}</span>', color, text)


@admin.register(EnvironmentalAspect)
class EnvironmentalAspectAdmin(admin.ModelAdmin):
    list_display = ("code", "activity", "category", "operating_condition",
                    "score", "is_significant", "owner")
    list_filter = ("category", "operating_condition", "is_significant")
    search_fields = ("code", "activity", "aspect")

    @admin.display(description="Önem skoru")
    def score(self, obj):
        s = obj.significance_score
        color = "#c62828" if s >= 15 else "#ed6c02" if s >= 8 else "#2e7d32"
        return format_html('<span style="color:{};font-weight:600">{}</span>', color, s)


@admin.register(EnvironmentalMeasurement)
class EnvironmentalMeasurementAdmin(admin.ModelAdmin):
    list_display = ("aspect", "period_start", "period_end", "quantity", "unit",
                    "limit_value", "above_limit_c")
    list_filter = ("aspect__category",)
    date_hierarchy = "period_end"

    @admin.display(description="Limit üzeri")
    def above_limit_c(self, obj):
        v = obj.above_limit
        if v is None:
            return "—"
        color = "#c62828" if v else "#2e7d32"
        return format_html('<span style="color:{}">{}</span>', color, "EVET" if v else "hayır")


@admin.register(LegalRequirement)
class LegalRequirementAdmin(admin.ModelAdmin):
    list_display = ("code", "reference", "title", "domain", "compliance_status",
                    "last_evaluated_on", "next_review_date")
    list_filter = ("domain", "compliance_status")
    search_fields = ("code", "reference", "title")


class JSAStepInline(admin.TabularInline):
    model = JSAStep
    extra = 1
    fields = ("sequence", "step_description", "hazards", "controls", "residual_risk")


@admin.register(JobSafetyAnalysis)
class JobSafetyAnalysisAdmin(SimpleHistoryAdmin):
    list_display = ("jsa_number", "task_name", "location", "status",
                    "approved_at", "review_date")
    list_filter = ("status",)
    search_fields = ("jsa_number", "task_name", "location")
    filter_horizontal = ("required_ppe",)
    inlines = [JSAStepInline]


@admin.register(WorkPermit)
class WorkPermitAdmin(SimpleHistoryAdmin):
    list_display = ("permit_number", "type", "location", "valid_from",
                    "valid_until", "permit_holder", "status_c", "safety_officer")
    list_filter = ("status", "type")
    search_fields = ("permit_number", "location", "work_description")
    filter_horizontal = ("required_ppe",)
    date_hierarchy = "valid_from"

    @admin.display(description="Durum")
    def status_c(self, obj):
        c = {"DRAFT": "#6b7280", "REQUESTED": "#0369a1", "ISSUED": "#2e7d32",
             "SUSPENDED": "#ed6c02", "CLOSED": "#374151",
             "EXPIRED": "#c62828", "CANCELLED": "#991b1b"}.get(obj.status, "#000")
        return format_html('<span style="color:{};font-weight:600">{}</span>',
                           c, obj.get_status_display())
