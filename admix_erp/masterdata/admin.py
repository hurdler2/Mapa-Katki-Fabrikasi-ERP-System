from django.contrib import admin

from .models import (
    CompanyProfile, Container, Customer, Product, RawMaterial,
    Supplier, UnitOfMeasure,
)


@admin.register(CompanyProfile)
class CompanyProfileAdmin(admin.ModelAdmin):
    """Şirket profili — singleton (tek satır) admin ekranı."""

    fieldsets = (
        ("Kurumsal Kimlik", {
            "fields": ("legal_name", "short_name", "tagline", "logo"),
        }),
        ("İletişim", {
            "fields": ("address", "phone", "email", "website"),
        }),
        ("Cezayir Vergi Kimliği", {
            "fields": ("tax_no", "tax_activity_no", "trade_register_no",
                       "article_of_import_no"),
        }),
        ("Banka", {
            "fields": ("bank_name", "bank_rib", "bank_iban"),
        }),
        ("Fatura Metinleri", {
            "fields": ("invoice_header_note", "invoice_footer_note"),
        }),
    )

    def has_add_permission(self, request):
        # Singleton — tek satır zorlaması
        return not CompanyProfile.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(UnitOfMeasure)
class UnitOfMeasureAdmin(admin.ModelAdmin):
    list_display = ("code", "name")
    search_fields = ("code", "name")


@admin.register(RawMaterial)
class RawMaterialAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "material_type", "unit", "density", "is_active")
    list_filter = ("material_type", "is_active")
    search_fields = ("code", "name")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "unit", "is_active")
    list_filter = ("is_active",)
    search_fields = ("code", "name")


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "contact", "is_active")
    list_filter = ("is_active",)
    search_fields = ("code", "name", "tax_no")


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "contact", "default_discount_pct", "is_active")
    list_filter = ("is_active",)
    search_fields = ("code", "name", "tax_no")
    list_editable = ("default_discount_pct",)
    fieldsets = (
        (None, {"fields": ("code", "name", "is_active")}),
        ("İletişim", {"fields": ("contact", "email", "address", "phone")}),
        ("Vergi & Ticari", {"fields": ("tax_no", "default_discount_pct")}),
    )

    def get_fieldsets(self, request, obj=None):
        # phone alanı Customer'da yok — bunun gibi eksik alanlar için güvenlik
        model_fields = {f.name for f in self.model._meta.get_fields()}
        cleaned = []
        for title, opts in super().get_fieldsets(request, obj):
            new_fields = tuple(f for f in opts["fields"] if f in model_fields)
            if new_fields:
                cleaned.append((title, {"fields": new_fields}))
        return cleaned


@admin.register(Container)
class ContainerAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "container_type", "capacity", "unit", "is_active")
    list_filter = ("container_type", "is_active")
    search_fields = ("code", "name")
