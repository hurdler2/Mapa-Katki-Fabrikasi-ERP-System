"""IAM modelleri: kullanıcı profili + e-imza kayıtları.

ISO 9001 §5.3 (roles), §7.2 (competence). Django Group'ları rol olarak kullanılır;
UserProfile bunları ek meta veriyle (departman, sicil no, yetkinlik) zenginleştirir.
21 CFR Part 11'den esinlenen e-imza modeli: kullanıcı kritik kayıtlar (parti serbest,
COA, doküman onayı) üzerinde parola ile yeniden kimlik doğrulaması yaparak imza atar.
"""
from __future__ import annotations

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models

from common.models import TimeStamped


# Cezayir fabrikası organizasyon yapısına uygun rol tanımları.
# Django Group.name olarak kullanılır.
# MCOS Faz B — her rol CDD-002'nin 12 fonksiyon kodundan biriyle etiketlenir.
class Role:
    # Üst yönetim
    GENERAL_MANAGER = "GENERAL_MANAGER"          # Genel Müdür — hepsini görür, kritik onaylar
    TECHNICAL_MANAGER = "TECHNICAL_MANAGER"      # Teknik Müdür — üretim/kalite/bakım/EHS

    # Orta yönetim
    OPERATIONS_MANAGER = "OPERATIONS_MANAGER"    # Operasyon Müdürü — üretim + depo + planlama
    IMS_QA_MANAGER = "IMS_QA_MANAGER"            # Entegre Yönetim Sistemi & QA Müdürü — QMS/CAPA/doküman/denetim
    ACCOUNTING_MANAGER = "ACCOUNTING_MANAGER"    # Muhasebe (finans/mali)

    # Uzman / operasyonel
    LAB_QC = "LAB_QC"                            # Laboratuvar & Kalite Kontrol
    OPERATIONS_SUPERVISOR = "OPERATIONS_SUPERVISOR"  # Operasyon Supervizörü (vardiya lideri)
    WAREHOUSE = "WAREHOUSE"                      # Depo
    PURCHASING = "PURCHASING"                    # Satın Alma

    # Faz B — MCOS'a özgü yeni roller
    RDT_ENGINEER = "RDT_ENGINEER"                # R&D / Product / Formwork Engineer
    MLTS_ANALYST = "MLTS_ANALYST"                # Commercial Laboratory analyst (MLTS BL)
    HSE_OFFICER = "HSE_OFFICER"                  # HSE — stop-work + veto yetkisi
    INTERNAL_AUDITOR = "INTERNAL_AUDITOR"        # Bağımsız iç tetkik
    MAINTENANCE_TECH = "MAINTENANCE_TECH"        # Bakım Teknisyeni
    COMMERCIAL_ENG = "COMMERCIAL_ENG"            # Ticari & Teknik Servis Mühendisi

    # BT (arka plan — kullanıcıya görünmez normal iş akışlarında)
    IT_ADMIN = "IT_ADMIN"

    ALL = (
        GENERAL_MANAGER, TECHNICAL_MANAGER,
        OPERATIONS_MANAGER, IMS_QA_MANAGER, ACCOUNTING_MANAGER,
        LAB_QC, OPERATIONS_SUPERVISOR, WAREHOUSE, PURCHASING,
        RDT_ENGINEER, MLTS_ANALYST, HSE_OFFICER, INTERNAL_AUDITOR,
        MAINTENANCE_TECH, COMMERCIAL_ENG,
        IT_ADMIN,
    )

    # Türkçe etiket (UI'da gösterim için)
    LABELS = {
        GENERAL_MANAGER: "Genel Müdür",
        TECHNICAL_MANAGER: "Teknik Müdür",
        OPERATIONS_MANAGER: "Operasyon Müdürü",
        IMS_QA_MANAGER: "IMS & QA Müdürü",
        ACCOUNTING_MANAGER: "Muhasebe",
        LAB_QC: "Laboratuvar & QC",
        OPERATIONS_SUPERVISOR: "Operasyon Süpervizörü",
        WAREHOUSE: "Depo",
        PURCHASING: "Satın Alma",
        RDT_ENGINEER: "R&D / Ürün Mühendisi",
        MLTS_ANALYST: "MLTS Laboratuvar Analisti",
        HSE_OFFICER: "İSG & Çevre Sorumlusu",
        INTERNAL_AUDITOR: "İç Tetkikçi",
        MAINTENANCE_TECH: "Bakım Teknisyeni",
        COMMERCIAL_ENG: "Ticari & Teknik Servis Mühendisi",
        IT_ADMIN: "BT Yönetici",
    }

    # MCOS CDD-002 §Ek A — her rol bir fonksiyon koduna eşleşir.
    # NAV-002 §3 — bazı roller VETO gücüne sahip (QA/QC + HSE + LEG özel).
    # Karar seviyesi (D1-D4) rolün rutin yetkisidir; daha yüksek karar için delegasyon.
    MCOS_FUNCTION = {
        GENERAL_MANAGER: "COR",
        TECHNICAL_MANAGER: "RDT",       # + OPS koordinasyonu
        OPERATIONS_MANAGER: "OPS",
        IMS_QA_MANAGER: "QMS",
        ACCOUNTING_MANAGER: "ADM",      # Finance / HR / Admin / IT paylaşımı
        LAB_QC: "QCL",
        OPERATIONS_SUPERVISOR: "PRD",
        WAREHOUSE: "WHL",
        PURCHASING: "SCM",
        RDT_ENGINEER: "RDT",
        MLTS_ANALYST: "QCL",
        HSE_OFFICER: "HSE",
        INTERNAL_AUDITOR: "QMS",        # QA/IMS altında bağımsız denetim
        MAINTENANCE_TECH: "MNT",
        COMMERCIAL_ENG: "COM",
        IT_ADMIN: "ADM",
    }

    # NAV-002 §3 — Veto sahibi roller (HOLD/REJECT verebilirler).
    # Bir Decision.veto_holder_role bu setten değilse veto geçersizdir.
    VETO_HOLDERS = frozenset({
        IMS_QA_MANAGER,        # QA/QC veto
        LAB_QC,                # QC veto (parti serbest bırakma)
        HSE_OFFICER,           # HSE stop-work
        INTERNAL_AUDITOR,      # bağımsız denetim veto
    })

    # NAV-002 §3 — her rolün rutin karar seviyesi.
    # Üst seviyeye çıkılırsa Decision.delegated_authority doldurulmalı.
    DEFAULT_DECISION_LEVEL = {
        GENERAL_MANAGER: "D4",         # strategic / crisis
        TECHNICAL_MANAGER: "D3",       # major (üretim/kalite kapsam)
        OPERATIONS_MANAGER: "D3",
        IMS_QA_MANAGER: "D3",
        ACCOUNTING_MANAGER: "D2",
        LAB_QC: "D2",                  # functional (parti/lot)
        OPERATIONS_SUPERVISOR: "D2",   # vardiya
        WAREHOUSE: "D1",
        PURCHASING: "D2",
        RDT_ENGINEER: "D2",
        MLTS_ANALYST: "D2",
        HSE_OFFICER: "D3",             # stop-work major yetki
        INTERNAL_AUDITOR: "D3",
        MAINTENANCE_TECH: "D1",
        COMMERCIAL_ENG: "D2",
        IT_ADMIN: "D2",                # sistem D2; kritik değişiklikler D3 delegasyon
    }

    @classmethod
    def is_veto_holder(cls, role: str) -> bool:
        return role in cls.VETO_HOLDERS

    @classmethod
    def user_can_decide_at(cls, user, level: str) -> bool:
        """Bir kullanıcı verilen D-seviyesinde karar verebilir mi?

        Süper kullanıcı her seviyede. Aksi halde grup üyeliği içinden
        DEFAULT_DECISION_LEVEL en yüksek olanı bulunur.
        """
        if user.is_superuser:
            return True
        levels_order = {"D1": 1, "D2": 2, "D3": 3, "D4": 4}
        need = levels_order.get(level, 0)
        best = 0
        for g in user.groups.values_list("name", flat=True):
            lvl = cls.DEFAULT_DECISION_LEVEL.get(g)
            if lvl:
                best = max(best, levels_order.get(lvl, 0))
        return best >= need


class Department(TimeStamped):
    """Departman / birim."""

    code = models.CharField("Kod", max_length=20, unique=True)
    name = models.CharField("Ad", max_length=120)
    parent = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="children", verbose_name="Üst departman",
    )
    is_active = models.BooleanField("Aktif", default=True)

    class Meta:
        verbose_name = "Departman"
        verbose_name_plural = "Departmanlar"
        ordering = ["code"]

    def __str__(self) -> str:
        return f"{self.code} · {self.name}"


class UserProfile(TimeStamped):
    """Django User'ı ek meta veriyle zenginleştirir."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="profile", verbose_name="Kullanıcı",
    )
    employee_no = models.CharField("Sicil No", max_length=30, blank=True, unique=True)
    department = models.ForeignKey(
        Department, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="employees", verbose_name="Departman",
    )
    title = models.CharField("Ünvan", max_length=120, blank=True)
    phone = models.CharField("Telefon", max_length=30, blank=True)
    hire_date = models.DateField("İşe giriş", null=True, blank=True)

    class Meta:
        verbose_name = "Kullanıcı Profili"
        verbose_name_plural = "Kullanıcı Profilleri"

    def __str__(self) -> str:
        return f"{self.user.get_username()} ({self.employee_no or '-'})"


class Competency(TimeStamped):
    """Yetkinlik tanımı (eğitim/yetki türleri). ISO 9001 §7.2."""

    code = models.CharField("Kod", max_length=30, unique=True)
    name = models.CharField("Ad", max_length=120)
    description = models.TextField("Açıklama", blank=True)
    valid_days = models.PositiveIntegerField(
        "Geçerlilik (gün)", null=True, blank=True,
        help_text="Süreli yetkinlikler için (örn. iş güvenliği 365 gün)",
    )

    class Meta:
        verbose_name = "Yetkinlik"
        verbose_name_plural = "Yetkinlikler"
        ordering = ["code"]

    def __str__(self) -> str:
        return f"{self.code} · {self.name}"


class UserCompetency(TimeStamped):
    """Kullanıcı → yetkinlik ataması. Geçerlilik takibi."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="competencies", verbose_name="Kullanıcı",
    )
    competency = models.ForeignKey(
        Competency, on_delete=models.PROTECT,
        related_name="assignments", verbose_name="Yetkinlik",
    )
    obtained_on = models.DateField("Alındığı tarih")
    expires_on = models.DateField("Geçerlilik sonu", null=True, blank=True)
    evidence = models.CharField("Kanıt (sertifika no vb.)", max_length=200, blank=True)

    class Meta:
        verbose_name = "Kullanıcı Yetkinliği"
        verbose_name_plural = "Kullanıcı Yetkinlikleri"
        unique_together = (("user", "competency"),)

    def __str__(self) -> str:
        return f"{self.user.get_username()} · {self.competency.code}"


class ESignature(TimeStamped):
    """Elektronik imza kaydı (21 CFR Part 11 esinli).

    Herhangi bir modelin herhangi bir kaydı için imza. `verify_password` ile
    kullanıcının parolasını yeniden doğrulayarak oluşturulmalıdır — servis
    katmanı bu sorumluluğu üstlenir.
    """

    class Meaning(models.TextChoices):
        APPROVED = "APPROVED", "Onaylandı"
        REVIEWED = "REVIEWED", "İncelendi"
        RELEASED = "RELEASED", "Serbest bırakıldı"
        REJECTED = "REJECTED", "Reddedildi"
        WITNESSED = "WITNESSED", "Şahit olarak imzalandı"
        SIGNED_OFF = "SIGNED_OFF", "İmzalandı"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="e_signatures", verbose_name="İmzalayan",
    )
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveBigIntegerField()
    target = GenericForeignKey("content_type", "object_id")
    meaning = models.CharField("Anlam", max_length=16, choices=Meaning.choices)
    reason = models.CharField(
        "Gerekçe", max_length=255,
        help_text="Değişikliğin/kaydın gerekçesi (21 CFR 11 iz gerekliliği).",
    )
    signed_at = models.DateTimeField("İmza zamanı", auto_now_add=True)
    ip_address = models.GenericIPAddressField("IP", null=True, blank=True)

    class Meta:
        verbose_name = "E-imza"
        verbose_name_plural = "E-imzalar"
        ordering = ["-signed_at"]
        indexes = [
            models.Index(fields=["content_type", "object_id"]),
        ]

    def __str__(self) -> str:
        return f"{self.user.get_username()} · {self.get_meaning_display()} · {self.signed_at:%Y-%m-%d %H:%M}"
