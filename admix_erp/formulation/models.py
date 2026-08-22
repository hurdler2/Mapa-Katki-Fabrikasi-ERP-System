"""Reçete (formulation) modelleri."""
from __future__ import annotations

from decimal import Decimal
from typing import Iterable

from django.core.exceptions import ValidationError
from django.db import models, transaction
from simple_history.models import HistoricalRecords

from common.models import TimeStamped
from masterdata.models import Product, RawMaterial, UnitOfMeasure


class Recipe(TimeStamped):
    """Versiyonlu reçete. Bir ürün için aynı anda yalnız 1 aktif."""

    product = models.ForeignKey(
        Product, on_delete=models.PROTECT, related_name="recipes", verbose_name="Ürün"
    )
    business_line = models.ForeignKey(
        "businessline.BusinessLine", on_delete=models.PROTECT,
        null=True, blank=True, related_name="recipes",
        verbose_name="İş Kolu",
    )
    version = models.PositiveIntegerField("Versiyon")
    base_batch_size = models.DecimalField(
        "Referans parti", max_digits=12, decimal_places=4
    )
    unit = models.ForeignKey(
        UnitOfMeasure, on_delete=models.PROTECT, related_name="recipes", verbose_name="Birim"
    )
    is_active = models.BooleanField("Aktif", default=False)
    effective_date = models.DateField("Yürürlük tarihi", null=True, blank=True)
    notes = models.TextField("Notlar", blank=True)

    history = HistoricalRecords()

    class Meta:
        verbose_name = "Reçete"
        verbose_name_plural = "Reçeteler"
        unique_together = (("product", "version"),)
        ordering = ["product", "-version"]

    def __str__(self) -> str:
        return f"{self.product.code} v{self.version}"

    def clean(self) -> None:
        """Aktif reçete tekliği: aynı ürüne başka aktif olamaz."""
        if self.is_active:
            qs = Recipe.objects.filter(product=self.product, is_active=True)
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if qs.exists():
                raise ValidationError(
                    {"is_active": "Bu ürün için zaten aktif bir reçete mevcut."}
                )

    def save(self, *args, **kwargs) -> None:
        """Aktif reçete tekliğini transaction içinde zorla."""
        with transaction.atomic():
            if self.is_active:
                Recipe.objects.filter(product=self.product, is_active=True).exclude(
                    pk=self.pk
                ).update(is_active=False)
            super().save(*args, **kwargs)

    def scaled_lines(self, target_qty: Decimal) -> list[dict]:
        """Reçete satırlarını `target_qty` için ölçekle.

        factor = target_qty / base_batch_size
        Döner: [{raw_material, quantity, sequence, tolerance_pct, is_complement}, ...]

        Eğer bir satır ``is_complement=True`` ise, o satırın miktarı diğer
        (sabit) satırların ölçeklenmiş toplamı ile hedef arasındaki farktır.
        (Bilan massique §22 PLANIFIÉ)
        """
        target_qty = Decimal(target_qty)
        if self.base_batch_size <= 0:
            raise ValueError("base_batch_size sıfır veya negatif olamaz.")
        factor = target_qty / self.base_batch_size
        Q = Decimal("0.0001")

        fixed: list[dict] = []
        complement: dict | None = None
        for line in self.lines.select_related("raw_material").order_by("sequence"):
            row = {
                "raw_material": line.raw_material,
                "quantity": (line.quantity * factor).quantize(Q),
                "sequence": line.sequence,
                "tolerance_pct": line.tolerance_pct,
                "is_complement": line.is_complement,
            }
            if line.is_complement:
                complement = row
            else:
                fixed.append(row)

        if complement is not None:
            fixed_sum = sum((r["quantity"] for r in fixed), Decimal("0"))
            complement["quantity"] = (target_qty - fixed_sum).quantize(Q)

        merged = fixed + ([complement] if complement else [])
        merged.sort(key=lambda r: r["sequence"])
        return merged

    def bilan_massique(self, target_qty: Decimal) -> dict:
        """§22 kütle bilançosu özeti: hedef, sabit toplam, complément."""
        lines = self.scaled_lines(target_qty)
        fixed_sum = sum(
            (l["quantity"] for l in lines if not l["is_complement"]),
            Decimal("0"),
        )
        comp = next((l for l in lines if l["is_complement"]), None)
        return {
            "target_qty": Decimal(target_qty),
            "fixed_sum": fixed_sum,
            "complement_qty": comp["quantity"] if comp else Decimal("0"),
            "complement_material": comp["raw_material"] if comp else None,
            "has_complement": comp is not None,
        }


class RecipeLine(TimeStamped):
    """Reçete satırı: base_batch_size başına hammadde miktarı."""

    recipe = models.ForeignKey(
        Recipe, on_delete=models.CASCADE, related_name="lines", verbose_name="Reçete"
    )
    raw_material = models.ForeignKey(
        RawMaterial, on_delete=models.PROTECT, related_name="recipe_lines", verbose_name="Hammadde"
    )
    quantity = models.DecimalField(
        "Miktar (base_batch_size başına)", max_digits=12, decimal_places=4
    )
    sequence = models.PositiveIntegerField("Sıra", default=1)
    tolerance_pct = models.DecimalField(
        "Tolerans (%)", max_digits=5, decimal_places=2, default=Decimal("1.00")
    )
    is_complement = models.BooleanField(
        "Tamamlayıcı (§22)", default=False,
        help_text="COMPLÉMENT: base_batch_size'a otomatik tamamlar (genelde su).",
    )

    class Meta:
        verbose_name = "Reçete Satırı"
        verbose_name_plural = "Reçete Satırları"
        unique_together = (("recipe", "raw_material"),)
        ordering = ["sequence"]
        constraints = [
            models.UniqueConstraint(
                fields=["recipe"],
                condition=models.Q(is_complement=True),
                name="one_complement_per_recipe",
            ),
        ]

    def __str__(self) -> str:
        marker = " [COMPLÉMENT]" if self.is_complement else ""
        return f"{self.recipe} · {self.raw_material.code} × {self.quantity}{marker}"
