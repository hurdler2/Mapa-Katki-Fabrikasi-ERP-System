from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from .models import (
    ControlledDocument,
    DocumentAcknowledgement,
    DocumentCategory,
    DocumentDistribution,
    DocumentRevision,
)


@admin.register(DocumentCategory)
class DocumentCategoryAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "prefix")
    search_fields = ("code", "name")


class DocumentRevisionInline(admin.TabularInline):
    model = DocumentRevision
    extra = 0
    fields = ("revision", "status", "prepared_by", "reviewed_by", "approved_by",
              "effective_date", "next_review_date")
    readonly_fields = ("reviewed_by", "approved_by")


@admin.register(ControlledDocument)
class ControlledDocumentAdmin(SimpleHistoryAdmin):
    list_display = ("document_number", "title", "category", "status", "process_owner")
    list_filter = ("category", "status")
    search_fields = ("document_number", "title")
    inlines = [DocumentRevisionInline]


class DocumentAcknowledgementInline(admin.TabularInline):
    model = DocumentAcknowledgement
    extra = 0
    fields = ("user", "acknowledged_at", "note")
    readonly_fields = ("acknowledged_at",)


class DocumentDistributionInline(admin.TabularInline):
    model = DocumentDistribution
    extra = 0
    fields = ("department_code", "recipient", "copy_number", "distributed_at", "recalled_at")
    readonly_fields = ("distributed_at",)


@admin.register(DocumentRevision)
class DocumentRevisionAdmin(SimpleHistoryAdmin):
    list_display = ("document", "revision", "status", "effective_date",
                    "next_review_date", "approved_at")
    list_filter = ("status",)
    search_fields = ("document__document_number", "document__title", "revision")
    inlines = [DocumentDistributionInline, DocumentAcknowledgementInline]
