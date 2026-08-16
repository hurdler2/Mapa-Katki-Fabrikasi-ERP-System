"""master_register/services.py — snapshot chain servisi (append-only).

Master Register satırı DEĞİŞTİRİLMEZ. Bir kayıt güncellenmesi gerekince
snapshot alınır:
    1. old.is_snapshot = True (donmuş kopya, chain'e girer)
    2. new = old'un mevcut alanları + değişiklikler, is_snapshot=False,
       snapshot_of=old
    3. Register'da her event_id için tek "aktif" satır (is_snapshot=False)
       partial unique constraint ile garantilenir.
"""
from __future__ import annotations

from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction

from .models import IntegratedEventRegister, SecurityEventRegister


def _copy_fields(obj) -> dict:
    """Manuel alan kopyası — history alanı ve pk hariç."""
    exclude = {"id", "pk", "history", "created_at", "updated_at",
                "is_snapshot", "snapshot_of"}
    data = {}
    for f in obj._meta.get_fields():
        if not hasattr(f, "attname"):
            continue
        name = f.name
        if name in exclude:
            continue
        # FK'ları attname (id) ile kopyala
        if f.is_relation and not f.many_to_many:
            data[f.attname] = getattr(obj, f.attname)
        else:
            data[name] = getattr(obj, name)
    return data


@transaction.atomic
def create_snapshot_integrated(
    current: IntegratedEventRegister, **changes: Any,
) -> IntegratedEventRegister:
    """IntegratedEventRegister için snapshot al ve yeni aktif satır oluştur.

    `changes`: yeni satırda güncellenmesi istenen alanlar.
    """
    if current.is_snapshot:
        raise ValidationError(
            "Snapshot satırdan yeni snapshot alınamaz — aktif satırı bul."
        )

    # 1) Eski satırı snapshot'a çevir
    old_pk = current.pk
    IntegratedEventRegister.objects.filter(pk=old_pk).update(is_snapshot=True)

    # 2) Yeni satır (aktif) oluştur
    data = _copy_fields(current)
    data.update(changes)
    data["is_snapshot"] = False
    data["snapshot_of_id"] = old_pk
    return IntegratedEventRegister.objects.create(**data)


@transaction.atomic
def create_snapshot_security(
    current: SecurityEventRegister, **changes: Any,
) -> SecurityEventRegister:
    if current.is_snapshot:
        raise ValidationError(
            "Snapshot satırdan yeni snapshot alınamaz — aktif satırı bul."
        )
    old_pk = current.pk
    SecurityEventRegister.objects.filter(pk=old_pk).update(is_snapshot=True)
    data = _copy_fields(current)
    data.update(changes)
    data["is_snapshot"] = False
    data["snapshot_of_id"] = old_pk
    return SecurityEventRegister.objects.create(**data)


def active_integrated_by_event_id(event_id: str) -> IntegratedEventRegister | None:
    """Aktif (snapshot değil) satırı döner."""
    return IntegratedEventRegister.objects.filter(
        event_id=event_id, is_snapshot=False).first()


def snapshot_chain_integrated(active: IntegratedEventRegister) -> list[IntegratedEventRegister]:
    """En eski snapshot'tan aktife doğru zinciri döner."""
    chain: list[IntegratedEventRegister] = [active]
    cur = active
    while cur.snapshot_of_id:
        cur = cur.snapshot_of
        chain.append(cur)
    chain.reverse()
    return chain
