"""Cezayir Fransız stili sayı biçimlendirme filtreleri.

Kullanım:
    {% load formats %}
    {{ inv.total_ttc|dzd }}          → 1.234.567,89 DZD
    {{ inv.total_ttc|dzd0 }}         → 1.234.568 DZD
    {{ value|fr_number }}            → 1.234.567,89
    {{ value|fr_number:0 }}          → 1.234.568
    {{ value|fr_short }}             → 1,23M / 1,2K
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation

from django import template

register = template.Library()


def _to_decimal(value) -> Decimal | None:
    if value is None or value == "":
        return None
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _fr_format(value: Decimal, decimals: int = 2) -> str:
    """1234567.89 → '1.234.567,89' (nokta binlik, virgül ondalık)."""
    quant = Decimal(10) ** -decimals if decimals else Decimal(1)
    if decimals:
        v = value.quantize(quant)
    else:
        v = value.quantize(Decimal(1))
    # Yerleşik: "{:,.2f}" ise '1,234,567.89' verir → değiştir
    s = f"{v:,.{decimals}f}"
    # ',' → geçici marker, '.' → ',', marker → '.'
    return s.replace(",", "§").replace(".", ",").replace("§", ".")


@register.filter(name="fr_number")
def fr_number(value, decimals=2):
    """Fransız stili sayı: 1.234.567,89"""
    d = _to_decimal(value)
    if d is None:
        return "—"
    try:
        decimals = int(decimals)
    except (TypeError, ValueError):
        decimals = 2
    return _fr_format(d, decimals)


@register.filter(name="dzd")
def dzd(value):
    """1.234.567,89 DZD (iki ondalık)"""
    d = _to_decimal(value)
    if d is None:
        return "—"
    return f"{_fr_format(d, 2)} DZD"


@register.filter(name="dzd0")
def dzd0(value):
    """1.234.568 DZD (tamsayı)"""
    d = _to_decimal(value)
    if d is None:
        return "—"
    return f"{_fr_format(d, 0)} DZD"


@register.filter(name="fr_short")
def fr_short(value):
    """Kısa format: 1,23M / 12,3K / 234"""
    d = _to_decimal(value)
    if d is None:
        return "—"
    n = float(d)
    absn = abs(n)
    if absn >= 1_000_000_000:
        s = _fr_format(Decimal(n / 1_000_000_000), 2)
        return f"{s}Md"
    if absn >= 1_000_000:
        s = _fr_format(Decimal(n / 1_000_000), 2)
        return f"{s}M"
    if absn >= 1_000:
        s = _fr_format(Decimal(n / 1_000), 1)
        return f"{s}K"
    return _fr_format(Decimal(n), 0)


@register.filter(name="pct")
def pct(value, decimals=1):
    """12.5 → '12,5%'"""
    d = _to_decimal(value)
    if d is None:
        return "—"
    try:
        decimals = int(decimals)
    except (TypeError, ValueError):
        decimals = 1
    return f"{_fr_format(d, decimals)}%"
