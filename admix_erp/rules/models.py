"""MCOS Faz H — Non-Negotiable Rules Enforcer.

CDD-001 §16'da tanımlı 12 mutlak kural. Her ihlal denemesi log edilir;
blocked=True ise kayıt asla oluşmaz/güncellenmez (ValidationError yükseltilir).

Kurallar:
    R01 · Onaysız reçete/HM/tedarikçi ile üretim yok
    R02 · HOLD/REJECT malzeme kullanılamaz veya sevk edilemez
    R03 · Geçerli numune + review olmadan release yok
    R04 · Kritik ölçüm geçerli kalibrasyon olmadan kabul edilmez
    R05 · Kayıt geriye dönük oluşturulmaz (backdating yasak)
    R06 · MOC olmadan aktif reçete/proses değişmez
    R07 · QA hold/red/release ticari baskıyla bypass edilmez
    R08 · Emniyetsiz iş (izinsiz) bypass edilemez
    R09 · Kritik görev yetkisiz kişi tarafından yürütülemez
    R10 · NCR/CAPA sadece aksiyon yapıldığı için kapatılmaz (etkinlik zorunlu)
    R11 · Master data (ControlledCode) sahibi ve yürürlük tarihi olmadan yayımlanmaz
    R12 · Ciddi risk (SEV1/SEV2) otomatik eskale edilir (GM notify)
"""
from __future__ import annotations

from django.contrib.auth.models import User
from django.db import models

from common.models import TimeStamped


# 12 kural sabiti — insan-okur label ile eşleşir.
RULE_TITLES: dict[int, str] = {
    1:  "Onaysız reçete/hammadde/tedarikçi ile üretim yok",
    2:  "HOLD/REJECT malzeme kullanılamaz veya sevk edilemez",
    3:  "Geçerli numune + review olmadan parti serbest bırakılmaz",
    4:  "Kritik ölçüm geçerli kalibrasyon olmadan kabul edilmez",
    5:  "Kayıt geriye dönük oluşturulmaz (backdating yasak)",
    6:  "MOC olmadan aktif reçete/proses değişmez",
    7:  "QA hold/red/release ticari baskıyla bypass edilmez",
    8:  "Emniyetsiz iş (izinsiz) bypass edilemez",
    9:  "Kritik görev yetkisiz kişi tarafından yürütülemez",
    10: "NCR/CAPA sadece aksiyon yapıldı diye kapanmaz (etkinlik zorunlu)",
    11: "ControlledCode sahibi olmadan yayımlanmaz",
    12: "Ciddi risk (SEV1/SEV2) eskale edilir",
}


class RuleViolation(TimeStamped):
    """Bir kural ihlali denemesi — log + notify + (blocked=True ise) durdur."""

    class Action(models.TextChoices):
        SAVE = "save", "Kaydetme"
        DELETE = "delete", "Silme"
        RELEASE = "release", "Serbest bırakma"
        CLOSE = "close", "Kapatma"
        CONSUME = "consume", "Tüketim"
        SHIP = "ship", "Sevkiyat"
        OTHER = "other", "Diğer"

    rule_no = models.PositiveSmallIntegerField(
        "Kural no", choices=[(k, f"R{k:02d}") for k in RULE_TITLES],
    )
    rule_title = models.CharField("Kural başlığı", max_length=200)

    user = models.ForeignKey(
        User, on_delete=models.PROTECT, null=True, blank=True,
        related_name="rule_violations",
        verbose_name="Kullanıcı (bilinen)",
    )
    target_model = models.CharField(
        "Hedef model", max_length=100,
        help_text="Örn. production.ProductionBatch",
    )
    target_pk = models.CharField(
        "Hedef PK", max_length=100, blank=True,
        help_text="Kaydedilmemiş nesne için boş olabilir.",
    )
    target_repr = models.CharField(
        "Hedef görüntü", max_length=200, blank=True,
    )
    attempted_action = models.CharField(
        "Denenen aksiyon", max_length=16,
        choices=Action.choices, default=Action.SAVE,
    )
    reason = models.TextField(
        "İhlal nedeni",
        help_text="Kural tetiklenme detayı — hangi alan, hangi değer.",
    )
    context = models.JSONField(
        "Ek bağlam", default=dict, blank=True,
        help_text="Önceki/denenen değerler, ilişki referansları.",
    )

    blocked = models.BooleanField(
        "Bloklandı mı?", default=True,
        help_text="True = kayıt engellendi (ValidationError). False = uyarı log'u.",
    )
    resolved = models.BooleanField("Çözüldü", default=False)
    resolution_note = models.TextField("Çözüm notu", blank=True)

    class Meta:
        verbose_name = "Kural İhlali"
        verbose_name_plural = "Kural İhlalleri"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["rule_no", "-created_at"]),
            models.Index(fields=["blocked", "resolved"]),
            models.Index(fields=["target_model"]),
        ]

    def __str__(self) -> str:
        return f"R{self.rule_no:02d} · {self.target_model} · {self.attempted_action}"
