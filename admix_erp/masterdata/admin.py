from django.contrib import admin

from .models import Container, Customer, Product, RawMaterial, Supplier, UnitOfMeasure


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
    list_display = ("code", "name", "contact", "is_active")
    list_filter = ("is_active",)
    search_fields = ("code", "name", "tax_no")


@admin.register(Container)
class ContainerAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "container_type", "capacity", "unit", "is_active")
    list_filter = ("container_type", "is_active")
    search_fields = ("code", "name")
