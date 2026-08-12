"""BusinessLine — SARL MAPA ALGÉRIE'nin 4 iş kolu.

MCOS NAV-001 §3'ten:
- MCS   MAPA Concrete Solutions      (kimyasal katkı, KRMIX)
- MPT   MAPA Precast Technologies    (prefabrik beton)
- MFT   MAPA Formwork Technologies   (çelik / tünel / özel sac kalıp)
- MLTS  MAPA Laboratory & Technical Services (ticari test lab)

**Kritik:** KRMIX bir ürün/ürün ailesidir; iş kolu değildir. MCS altında yönetilir.

CDD-002 §4.1: Her BL için bağımsız güvence hatları korunur:
- QC / Release yetkileri üretim baskısından bağımsız
- MLTS ticari lab tarafsızlığı ve gizliliği ayrı yetki matrisi
- Ortak yönetişim, ayrı sertifikasyon ve akreditasyon
"""
from __future__ import annotations

from django.db import models
from simple_history.models import HistoricalRecords

from common.models import TimeStamped


class BusinessLine(TimeStamped):
    """SARL MAPA ALGÉRIE iş kolu tanımı."""

    class Code(models.TextChoices):
        MCS = "MCS", "MAPA Concrete Solutions"
        MPT = "MPT", "MAPA Precast Technologies"
        MFT = "MFT", "MAPA Formwork Technologies"
        MLTS = "MLTS", "MAPA Laboratory & Technical Services"

    code = models.CharField("Kod", max_length=8, unique=True, choices=Code.choices)
    name = models.CharField("Ad", max_length=120)
    operational_scope = models.TextField(
        "Operasyonel kapsam",
        help_text="NAV-001 §3 tanımına uygun kapsam metni.",
    )
    typical_entry = models.CharField(
        "Tipik giriş noktası", max_length=200, blank=True,
        help_text="Örn. Production/batch event, Precast order/pour, "
                  "Formwork job/fabrication, Contract/sample/method",
    )

    # CDD-002 §4.1 bağımsız güvence
    qc_independence = models.TextField(
        "QC bağımsızlık kuralı", blank=True,
        help_text="Üretimden bağımsız QC/Release yetkisi tanımı.",
    )
    release_authority = models.TextField(
        "Serbest bırakma yetkisi", blank=True,
        help_text="Bu BL'de kim ne şartla release edebilir?",
    )
    external_certifications = models.TextField(
        "Dış sertifikasyon/akreditasyon", blank=True,
        help_text="Örn. ISO 9001, ISO 14001, ISO 17025 (MLTS için).",
    )

    is_active = models.BooleanField("Aktif", default=True)

    history = HistoricalRecords()

    class Meta:
        verbose_name = "İş Kolu"
        verbose_name_plural = "İş Kolları"
        ordering = ["code"]

    def __str__(self) -> str:
        return f"{self.code} · {self.name}"


class RoleBusinessLineScope(TimeStamped):
    """Bir Django Group (rol) hangi iş kollarında yetkilidir?

    Boş (hiç kayıt yok) → superuser gibi tüm BL'lere erişir.
    Kayıt var → sadece listelenen BL'lerde çalışır.
    """

    group = models.ForeignKey(
        "auth.Group", on_delete=models.CASCADE,
        related_name="business_line_scopes",
        verbose_name="Rol (Group)",
    )
    business_line = models.ForeignKey(
        BusinessLine, on_delete=models.CASCADE,
        related_name="role_scopes",
        verbose_name="İş Kolu",
    )

    class Meta:
        verbose_name = "Rol × İş Kolu Yetki"
        verbose_name_plural = "Rol × İş Kolu Yetkileri"
        unique_together = (("group", "business_line"),)

    def __str__(self) -> str:
        return f"{self.group.name} ↔ {self.business_line.code}"
