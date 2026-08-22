"""Sprint 1: Bilan massique §22 + besoins théoriques + facteur d'échelle."""
from __future__ import annotations

from decimal import Decimal

import pytest
from django.db import IntegrityError

from formulation.models import RecipeLine
from production.models import ProductionOrder


pytestmark = pytest.mark.django_db


def test_scale_factor_property(order, recipe):
    """target_qty=500, base=1000 → scale_factor 0.5."""
    assert order.scale_factor == Decimal("0.5000")


def test_scale_factor_double(order, recipe):
    order.target_qty = Decimal("2000")
    order.save()
    assert order.scale_factor == Decimal("2.0000")


def test_bilan_massique_no_complement(recipe):
    """Complément yoksa fixed_sum + complement_qty = target_qty
    olmalı ve complement 0 döner."""
    bilan = recipe.bilan_massique(Decimal("1000"))
    assert bilan["has_complement"] is False
    assert bilan["complement_qty"] == Decimal("0")
    # Recipe: W=600, G=15, SP=350, HD=35 → toplam 1000
    assert bilan["fixed_sum"] == Decimal("1000.0000")


def test_bilan_massique_with_complement(recipe, raws):
    """W (su) complément yapılırsa: fixed = 15+350+35=400,
    complément = 1000-400 = 600."""
    w_line = recipe.lines.get(raw_material=raws["W"])
    w_line.is_complement = True
    w_line.save()

    bilan = recipe.bilan_massique(Decimal("1000"))
    assert bilan["has_complement"] is True
    assert bilan["fixed_sum"] == Decimal("400.0000")
    assert bilan["complement_qty"] == Decimal("600.0000")
    assert bilan["complement_material"].code == "W"


def test_bilan_massique_scaled_with_complement(recipe, raws):
    """Scale 2.0: fixed = 800, complément = 2000 - 800 = 1200."""
    w_line = recipe.lines.get(raw_material=raws["W"])
    w_line.is_complement = True
    w_line.save()

    bilan = recipe.bilan_massique(Decimal("2000"))
    assert bilan["fixed_sum"] == Decimal("800.0000")
    assert bilan["complement_qty"] == Decimal("1200.0000")


def test_scaled_lines_complement_marker(recipe, raws):
    """scaled_lines dönüşünde is_complement bayrağı olmalı."""
    w_line = recipe.lines.get(raw_material=raws["W"])
    w_line.is_complement = True
    w_line.save()

    lines = recipe.scaled_lines(Decimal("500"))
    complements = [l for l in lines if l["is_complement"]]
    assert len(complements) == 1
    assert complements[0]["raw_material"].code == "W"


def test_only_one_complement_per_recipe(recipe, raws):
    """Aynı reçetede iki farklı complement satırı olamaz (constraint)."""
    w_line = recipe.lines.get(raw_material=raws["W"])
    w_line.is_complement = True
    w_line.save()

    sp_line = recipe.lines.get(raw_material=raws["SP"])
    sp_line.is_complement = True
    with pytest.raises(IntegrityError):
        sp_line.save()


def test_theoretical_needs_returns_all_lines(order, released_lots):
    """Emirde her hammadde için bir satır dönmeli, sufficient True."""
    rows = order.theoretical_needs()
    assert len(rows) == 4
    codes = {r["raw_material"].code for r in rows}
    assert codes == {"W", "G", "SP", "HD"}
    # released_lots bol stok verir → tümü yeterli
    assert all(r["sufficient"] for r in rows)


def test_theoretical_needs_flags_shortfall(order, released_lots):
    """Bir hammadde stoğunu düşürüp shortfall test et."""
    from inventory.models import RawMaterialLot
    sp_lot = released_lots["SP"]
    # SP ihtiyacı 175 (target 500, factor 0.5, base 350). Stoku 10 yap → shortfall 165.
    sp_lot.remaining_qty = Decimal("10")
    sp_lot.save()

    rows = order.theoretical_needs()
    sp_row = next(r for r in rows if r["raw_material"].code == "SP")
    assert sp_row["needed"] == Decimal("175.0000")
    assert sp_row["available"] == Decimal("10")
    assert sp_row["sufficient"] is False
    assert sp_row["shortfall"] == Decimal("165.0000")
