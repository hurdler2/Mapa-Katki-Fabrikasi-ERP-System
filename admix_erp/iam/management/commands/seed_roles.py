"""9 organizasyonel rol + BT rolü için Django Group + izin matrisi seed.

Kullanım: python manage.py seed_roles

Model:
- Genel Müdür (GM): her şeyi görür (READ), kritik onayları verir
- Teknik Müdür (TM): üretim/kalite/bakım/EHS — operasyonun teknik omurgası
- Operasyon Müdürü (OM): üretim planlama + depo koordinasyonu
- IMS & QA Müdürü: QMS/NCR/CAPA/doküman/iç denetim/risk/yönetim gözden geçirme
- Muhasebe: SCF muhasebe + fatura + TVA + sabit kıymet
- Lab & QC: kalite testleri + parametreler + COA
- Op. Süpervizörü: üretim partisi başlat/tamamla + dozaj kontrol + vardiya
- Depo: mal kabul + lot + stok hareketleri + IBC
- Satın Alma: PO + tedarikçi + requisition
- BT: kullanıcı yönetimi + sistem (Django Admin erişimi)
"""
from __future__ import annotations

from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from django.db import transaction

from iam.models import Role


FULL = ("view", "add", "change", "delete")
READ_WRITE = ("view", "add", "change")
READ = ("view",)


# app_label başına verilen izin türleri — Cezayir organizasyonuna göre.
ROLE_MATRIX: dict[str, dict[str, tuple[str, ...]]] = {

    # === ÜST YÖNETİM ================================================
    Role.GENERAL_MANAGER: {
        # Her şeyi görür ama kritik onaylar dışında değiştirmez
        "production": READ, "quality": READ, "inventory": READ,
        "purchasing": READ, "sales": READ, "reporting": READ,
        "governance": READ_WRITE,   # Yönetim gözden geçirme + risk kayıt
        "qms": READ, "docs": READ,
        "accounting": READ, "ehs": READ, "cmms": READ,
        "chemicals": READ, "mrp": READ, "hr": READ,
        "masterdata": READ, "formulation": READ,
        "registry": READ,  # MCOS kod register (okuma)
        "records": READ,   # MCOS case/record/decision (okuma)
        "analytics": READ, "notifications": READ_WRITE,
    },

    Role.TECHNICAL_MANAGER: {
        # Üretim + kalite + bakım + kimya + EHS teknik omurgası
        "production": FULL, "formulation": FULL,
        "quality": FULL, "chemicals": FULL,
        "cmms": FULL, "ehs": READ_WRITE,
        "qms": READ_WRITE, "docs": READ_WRITE,
        "inventory": READ, "masterdata": READ_WRITE,
        "mrp": READ_WRITE, "scada": FULL,
        "registry": READ,  # MCOS kod register (okuma)
        "records": READ_WRITE,   # TM olayları takip eder + kayıt oluşturur
        "reporting": READ, "notifications": READ_WRITE,
    },

    # === ORTA YÖNETİM ================================================
    Role.OPERATIONS_MANAGER: {
        # Üretim planlama + depo koordinasyonu
        "production": FULL, "formulation": READ_WRITE,
        "inventory": READ_WRITE, "purchasing": READ,
        "sales": READ, "cmms": READ,
        "mrp": FULL, "scada": READ_WRITE,
        "masterdata": READ_WRITE, "reporting": READ,
        "hr": READ_WRITE, "notifications": READ_WRITE,
    },

    Role.IMS_QA_MANAGER: {
        # Entegre Yönetim Sistemi: QMS + doküman + denetim + risk
        "qms": FULL, "docs": FULL, "governance": FULL,
        "quality": FULL, "chemicals": READ_WRITE,
        "production": READ, "inventory": READ,
        "ehs": READ_WRITE, "cmms": READ,
        "masterdata": READ, "hr": READ,
        "registry": FULL,  # MCOS Faz C — kontrollü kod register sahibi
        "records": FULL,   # MCOS Faz D — case/record/decision sahibi
        "notifications": READ_WRITE,
    },

    Role.ACCOUNTING_MANAGER: {
        "accounting": FULL,
        "purchasing": READ, "sales": READ,
        "masterdata": READ_WRITE,      # cari (müşteri/tedarikçi)
        "reporting": READ,
        "notifications": READ_WRITE,
    },

    # === UZMAN / OPERASYONEL =========================================
    Role.LAB_QC: {
        # Laboratuvar & Kalite Kontrol — testler + spec + parametreler
        "quality": FULL, "chemicals": READ_WRITE,
        "inventory": READ_WRITE,       # Lot QC durumu değiştirir
        "production": READ,
        "qms": READ_WRITE,             # NCR açabilir
        "lims": READ_WRITE,
        "masterdata": READ,
        "notifications": READ_WRITE,
    },

    Role.OPERATIONS_SUPERVISOR: {
        # Vardiya lideri — parti başlat/tamamla, dozaj kontrol, IBC
        "production": FULL, "inventory": READ_WRITE,
        "formulation": READ, "scada": READ_WRITE,
        "cmms": READ, "qms": READ_WRITE,
        "masterdata": READ,
        "notifications": READ_WRITE,
    },

    Role.WAREHOUSE: {
        "inventory": FULL, "purchasing": READ_WRITE,
        "sales": READ, "production": READ,
        "masterdata": READ,
        "chemicals": READ,             # SDS okuma + tehlike depolama
        "notifications": READ_WRITE,
    },

    Role.PURCHASING: {
        "purchasing": FULL, "masterdata": READ_WRITE,
        "inventory": READ, "mrp": READ_WRITE,
        "accounting": READ,            # PO → fatura akışını görsün
        "notifications": READ_WRITE,
    },

    # === BT =========================================================
    Role.IT_ADMIN: {
        "iam": FULL, "auth": FULL,
        "notifications": FULL,
        "records": READ,   # sistem olaylarını görebilir (dahil olduğu case'ler)
    },

    # === Faz B — Yeni MCOS rolleri ==================================
    Role.RDT_ENGINEER: {
        # R&D / Product / Formwork engineering (RDT fonksiyonu)
        "formulation": FULL, "chemicals": FULL,
        "quality": READ_WRITE, "production": READ,
        "masterdata": READ_WRITE, "docs": READ_WRITE,
        "records": READ_WRITE,
        "registry": READ,
        "notifications": READ_WRITE,
    },

    Role.MLTS_ANALYST: {
        # Commercial Laboratory analyst — MLTS BL için 3. taraf test hizmetleri
        "quality": FULL, "lims": FULL,
        "chemicals": READ, "inventory": READ,
        "masterdata": READ,
        "qms": READ_WRITE,       # NCR açabilir
        "records": READ_WRITE,
        "registry": READ,
        "notifications": READ_WRITE,
    },

    Role.HSE_OFFICER: {
        # HSE — stop-work + veto yetkili
        "ehs": FULL, "governance": READ_WRITE,
        "cmms": READ_WRITE,      # bakım kaynaklı olaylar
        "production": READ, "chemicals": READ_WRITE,
        "qms": READ_WRITE,       # HSE kaynaklı NCR
        "records": READ_WRITE,   # incident → case → decision (veto)
        "registry": READ,
        "notifications": READ_WRITE,
    },

    Role.INTERNAL_AUDITOR: {
        # Bağımsız iç tetkik — her şeyi görür, denetlediğini değiştirmez
        "governance": FULL,      # denetim + risk register
        "qms": READ, "docs": READ,
        "production": READ, "quality": READ,
        "inventory": READ, "purchasing": READ, "sales": READ,
        "accounting": READ, "ehs": READ, "cmms": READ,
        "chemicals": READ, "masterdata": READ, "hr": READ,
        "records": READ_WRITE,   # denetim bulguları → case + decision
        "registry": READ,
        "notifications": READ_WRITE,
    },

    Role.MAINTENANCE_TECH: {
        # Bakım Teknisyeni — iş emri operatörü
        "cmms": READ_WRITE,
        "production": READ, "inventory": READ,
        "ehs": READ_WRITE,       # olay bildirimi
        "qms": READ,
        "records": READ_WRITE,
        "notifications": READ_WRITE,
    },

    Role.COMMERCIAL_ENG: {
        # Ticari & Teknik Servis Mühendisi
        "sales": FULL, "masterdata": READ_WRITE,
        "quality": READ,
        "chemicals": READ,       # müşteriye teknik açıklama
        "qms": READ_WRITE,       # şikayet → NCR
        "records": READ_WRITE,   # şikayet case açar
        "notifications": READ_WRITE,
    },
}


class Command(BaseCommand):
    help = "9 organizasyonel rol + BT için Django Group ve izin matrisi kur."

    @transaction.atomic
    def handle(self, *args, **options) -> None:
        created_new = 0
        removed_stale = 0

        # Eski isimli grupları (varsa) sil — temiz kurulum için
        STALE = [
            "OPERATOR", "SHIFT_SUPERVISOR", "PRODUCTION_PLANNER",
            "QC_ANALYST", "QA_MANAGER", "SALES",
            "MAINTENANCE", "EHS", "MANAGEMENT",
        ]
        for name in STALE:
            if name in Role.ALL:
                continue
            deleted, _ = Group.objects.filter(name=name).delete()
            removed_stale += deleted or 0

        for role in Role.ALL:
            group, was_created = Group.objects.get_or_create(name=role)
            if was_created:
                created_new += 1

            desired: list[Permission] = []
            for app_label, actions in ROLE_MATRIX.get(role, {}).items():
                for ct in ContentType.objects.filter(app_label=app_label):
                    for action in actions:
                        codename = f"{action}_{ct.model}"
                        p = Permission.objects.filter(
                            content_type=ct, codename=codename
                        ).first()
                        if p:
                            desired.append(p)

            # Rolü sıfırdan set et — matrix authoritative
            group.permissions.set(desired)

        self.stdout.write(self.style.SUCCESS(
            f"Roles: {len(Role.ALL)} total, {created_new} new group(s), "
            f"{removed_stale} stale group(s) removed."
        ))
