from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.utils.html import format_html
from simple_history.admin import SimpleHistoryAdmin

from .models import (
    AVCPSystem,
    CertificateOfConformity,
    ChemicalProfile,
    FPCTestPlan,
    HazardStatement,
    NotifiedBody,
    Pictogram,
    PrecautionaryStatement,
    RetentionSample,
    SafetyDataSheet,
    ShelfLifeAlert,
    StorageIncompatibility,
    StorageZone,
)
from .services import approve_sds, render_sds_pdf


@admin.register(Pictogram)
class PictogramAdmin(admin.ModelAdmin):
    list_display = ("code", "name")
    search_fields = ("code", "name")


@admin.register(HazardStatement)
class HazardStatementAdmin(admin.ModelAdmin):
    list_display = ("code", "statement", "hazard_class")
    search_fields = ("code", "statement", "hazard_class")


@admin.register(PrecautionaryStatement)
class PrecautionaryStatementAdmin(admin.ModelAdmin):
    list_display = ("code", "statement", "category")
    list_filter = ("category",)
    search_fields = ("code", "statement")


@admin.register(ChemicalProfile)
class ChemicalProfileAdmin(SimpleHistoryAdmin):
    list_display = ("target", "hazard_class_c", "signal_word", "cas_no", "un_number", "adr_class")
    list_filter = ("hazard_class", "signal_word")
    search_fields = ("cas_no", "ec_no", "un_number",
                     "raw_material__code", "product__code")
    filter_horizontal = ("pictograms", "hazard_statements", "precautionary_statements")

    @admin.display(description="Hedef")
    def target(self, obj):
        return obj.raw_material or obj.product

    @admin.display(description="Tehlike sınıfı")
    def hazard_class_c(self, obj):
        colors = {
            "NON_HAZARDOUS": "#6b7280", "FLAMMABLE": "#dc2626",
            "OXIDIZER": "#ea580c", "ACID": "#f59e0b", "BASE": "#0891b2",
            "TOXIC": "#7c2d12", "CORROSIVE": "#c026d3",
            "ENV_HAZARD": "#059669", "COMPRESSED_GAS": "#0369a1",
            "EXPLOSIVE": "#991b1b",
        }
        c = colors.get(obj.hazard_class, "#000")
        return format_html('<span style="color:{};font-weight:600">{}</span>',
                           c, obj.get_hazard_class_display())


@admin.register(SafetyDataSheet)
class SafetyDataSheetAdmin(SimpleHistoryAdmin):
    list_display = ("sds_number", "profile", "version", "language",
                    "status", "revision_date", "next_review_date")
    list_filter = ("status", "language")
    search_fields = ("sds_number", "profile__raw_material__code",
                     "profile__product__code")
    actions = ["approve_sds_action", "download_pdf_action"]
    date_hierarchy = "revision_date"

    fieldsets = (
        (None, {"fields": (
            "sds_number", "profile", "version", "language",
            "issue_date", "revision_date", "next_review_date",
            "prepared_by", "approved_by", "approved_at", "status", "file",
        )}),
        ("Bölüm 1-4", {"classes": ("collapse",), "fields": (
            "section_1_identification", "section_2_hazards",
            "section_3_composition", "section_4_first_aid",
        )}),
        ("Bölüm 5-8", {"classes": ("collapse",), "fields": (
            "section_5_fire", "section_6_accidental",
            "section_7_handling", "section_8_exposure",
        )}),
        ("Bölüm 9-12", {"classes": ("collapse",), "fields": (
            "section_9_physical", "section_10_stability",
            "section_11_toxicological", "section_12_ecological",
        )}),
        ("Bölüm 13-16", {"classes": ("collapse",), "fields": (
            "section_13_disposal", "section_14_transport",
            "section_15_regulatory", "section_16_other",
        )}),
    )

    @admin.action(description="SDS onayla (APPROVED)")
    def approve_sds_action(self, request, queryset):
        for sds in queryset:
            try:
                approve_sds(sds, approver=request.user)
                self.message_user(request, f"{sds.sds_number} onaylandı.", messages.SUCCESS)
            except ValidationError as e:
                self.message_user(request, f"{sds.sds_number}: {e.messages[0]}", messages.ERROR)

    @admin.action(description="SDS PDF indir (ilk seçili)")
    def download_pdf_action(self, request, queryset):
        sds = queryset.first()
        if not sds:
            return
        pdf = render_sds_pdf(sds)
        response = HttpResponse(pdf, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{sds.sds_number}.pdf"'
        return response


@admin.register(StorageZone)
class StorageZoneAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "allowed_hazard_classes",
                    "max_capacity_kg", "temperature_min", "temperature_max", "is_active")
    list_filter = ("is_active",)
    search_fields = ("code", "name", "location")


@admin.register(StorageIncompatibility)
class StorageIncompatibilityAdmin(admin.ModelAdmin):
    list_display = ("class_a", "class_b", "reason")
    list_filter = ("class_a", "class_b")


@admin.register(NotifiedBody)
class NotifiedBodyAdmin(admin.ModelAdmin):
    list_display = ("number", "name", "country")
    search_fields = ("number", "name")


@admin.register(FPCTestPlan)
class FPCTestPlanAdmin(admin.ModelAdmin):
    list_display = ("product", "avcp_system", "notified_body",
                    "effective_from", "frequency_per_batch")
    list_filter = ("avcp_system", "product")
    search_fields = ("product__code",)


@admin.register(CertificateOfConformity)
class CertificateOfConformityAdmin(SimpleHistoryAdmin):
    list_display = ("coc_number", "product", "standard", "admixture_type",
                    "issue_date", "valid_until", "status", "issuing_body")
    list_filter = ("status", "standard")
    search_fields = ("coc_number", "product__code", "dop_number")
    date_hierarchy = "issue_date"


@admin.register(RetentionSample)
class RetentionSampleAdmin(admin.ModelAdmin):
    list_display = ("sample_number", "batch", "quantity", "unit_label",
                    "storage_location", "sampled_at", "keep_until", "status")
    list_filter = ("status",)
    search_fields = ("sample_number", "batch__batch_number", "storage_location")
    date_hierarchy = "sampled_at"


@admin.register(ShelfLifeAlert)
class ShelfLifeAlertAdmin(admin.ModelAdmin):
    list_display = ("lot", "days_to_expiry", "severity_c", "status", "detected_on")
    list_filter = ("severity", "status")
    search_fields = ("lot__lot_number",)
    date_hierarchy = "detected_on"

    @admin.display(description="Ağırlık")
    def severity_c(self, obj):
        colors = {
            "EXPIRED": "#991b1b", "CRITICAL": "#c62828",
            "WARNING": "#ed6c02", "INFO": "#0369a1",
        }
        c = colors.get(obj.severity, "#000")
        return format_html('<span style="color:{};font-weight:600">{}</span>',
                           c, obj.get_severity_display())
