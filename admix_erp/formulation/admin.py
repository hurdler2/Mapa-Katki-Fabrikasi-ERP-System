from django.contrib import admin

from .models import Recipe, RecipeLine


class RecipeLineInline(admin.TabularInline):
    model = RecipeLine
    extra = 1
    fields = ("sequence", "raw_material", "quantity", "tolerance_pct")
    ordering = ("sequence",)


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ("product", "version", "base_batch_size", "unit", "is_active", "effective_date")
    list_filter = ("is_active", "product")
    search_fields = ("product__code", "product__name")
    inlines = [RecipeLineInline]


@admin.register(RecipeLine)
class RecipeLineAdmin(admin.ModelAdmin):
    list_display = ("recipe", "sequence", "raw_material", "quantity", "tolerance_pct")
    list_filter = ("raw_material",)
