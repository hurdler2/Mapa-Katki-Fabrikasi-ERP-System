"""GHS piktogramları, tipik H/P ifadeleri ve depolama uyumsuzlukları seed'i."""
from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from chemicals.models import (
    HazardClass,
    HazardStatement,
    Pictogram,
    PrecautionaryStatement,
    StorageIncompatibility,
)


PICTOGRAMS = [(c.value, c.label) for c in Pictogram.Code]


# En sık kullanılan H ifadeleri (kısa liste; tam CLP listesi ~80+)
H_STATEMENTS = [
    ("H200", "Kararsız patlayıcı.", "Explosive, unstable"),
    ("H220", "Aşırı derecede alevlenir gaz.", "Extremely flammable gas"),
    ("H225", "Kolay alevlenir sıvı ve buhar.", "Highly flammable liquid and vapour"),
    ("H226", "Alevlenir sıvı ve buhar.", "Flammable liquid and vapour"),
    ("H272", "Yangını alevlendirebilir; oksitleyici.", "May intensify fire; oxidizer"),
    ("H290", "Metaller için aşındırıcı olabilir.", "May be corrosive to metals"),
    ("H301", "Yutulması halinde toksik.", "Toxic if swallowed"),
    ("H302", "Yutulması halinde zararlı.", "Harmful if swallowed"),
    ("H311", "Cilt ile temas etmesi halinde toksik.", "Toxic in contact with skin"),
    ("H314", "Ciddi cilt yanıklarına ve göz hasarına yol açar.",
        "Causes severe skin burns and eye damage"),
    ("H315", "Cilt tahrişine yol açar.", "Causes skin irritation"),
    ("H317", "Alerjik cilt reaksiyonlarına yol açabilir.",
        "May cause an allergic skin reaction"),
    ("H318", "Ciddi göz hasarına yol açar.", "Causes serious eye damage"),
    ("H319", "Ciddi göz tahrişine yol açar.", "Causes serious eye irritation"),
    ("H332", "Solunması halinde zararlı.", "Harmful if inhaled"),
    ("H335", "Solunum yolu tahrişine yol açabilir.",
        "May cause respiratory irritation"),
    ("H351", "Kansere neden olma şüphesi var.", "Suspected of causing cancer"),
    ("H373", "Uzun süreli veya tekrarlı maruz kalma sonucu organlarda hasara "
             "yol açabilir.",
        "May cause damage to organs through prolonged or repeated exposure"),
    ("H400", "Sucul yaşam için çok toksiktir.", "Very toxic to aquatic life"),
    ("H411", "Sucul yaşam için toksik, uzun süre kalıcı etkili.",
        "Toxic to aquatic life with long lasting effects"),
    ("H412", "Sucul yaşam için zararlı, uzun süre kalıcı etkili.",
        "Harmful to aquatic life with long lasting effects"),
]


P_STATEMENTS = [
    ("P201", "Kullanmadan önce özel talimatları edinin.", "PREVENTION"),
    ("P210", "Isıdan, sıcak yüzeylerden, kıvılcımlardan uzak tutun. Sigara içilmez.",
        "PREVENTION"),
    ("P233", "Kabı sıkıca kapatılmış halde tutun.", "PREVENTION"),
    ("P234", "Yalnızca orijinal kapta saklayın.", "STORAGE"),
    ("P260", "Toz/duman/gaz/sis/buhar/spreyi solumayın.", "PREVENTION"),
    ("P264", "Elleçlemeden sonra ellerinizi iyice yıkayın.", "PREVENTION"),
    ("P271", "Yalnızca iyi havalandırılmış alanda kullanın.", "PREVENTION"),
    ("P273", "Çevreye salıvermekten kaçının.", "PREVENTION"),
    ("P280", "Koruyucu eldiven/koruyucu kıyafet/göz koruyucu/yüz koruyucu kullanın.",
        "PREVENTION"),
    ("P301+P310", "YUTULDUĞUNDA: Derhal ULUSAL ZEHİR DANIŞMA MERKEZİNİ veya "
                  "doktoru arayın.", "RESPONSE"),
    ("P302+P352", "CİLT ÜZERİNDE: Bol su ile yıkayın.", "RESPONSE"),
    ("P303+P361+P353", "CİLT (veya saç) ÜZERİNE: Tüm kirlenmiş kıyafetleri "
                       "derhal çıkarın. Cildi suyla durulayın.", "RESPONSE"),
    ("P304+P340", "SOLUNMASI HALİNDE: Kişiyi temiz havaya çıkarın ve rahat "
                  "nefes alması için uygun bir pozisyonda tutun.", "RESPONSE"),
    ("P305+P351+P338", "GÖZ İLE TEMAS HALİNDE: Su ile birkaç dakika dikkatli "
                       "biçimde durulayın. Kontak lensleri çıkarın ve "
                       "durulamaya devam edin.", "RESPONSE"),
    ("P310", "Derhal ULUSAL ZEHİR DANIŞMA MERKEZİNİ veya doktoru arayın.",
        "RESPONSE"),
    ("P403+P233", "İyi havalandırılmış yerde depolayın. Kabı sıkıca kapatılmış "
                  "halde tutun.", "STORAGE"),
    ("P405", "Kilit altında saklayın.", "STORAGE"),
    ("P501", "İçeriğini/kabını yerel/bölgesel/ulusal/uluslararası düzenlemeye "
             "uygun olarak bertaraf edin.", "DISPOSAL"),
]


# Klasik uyumsuzluk çiftleri (chemical storage segregation)
INCOMPATIBILITIES = [
    (HazardClass.ACID, HazardClass.BASE,
        "Nötralizasyon reaksiyonu, ısı ve gaz üretimi."),
    (HazardClass.ACID, HazardClass.OXIDIZER,
        "Oksitleyici asitle patlayıcı reaksiyon."),
    (HazardClass.FLAMMABLE, HazardClass.OXIDIZER,
        "Yangın/patlama riski."),
    (HazardClass.FLAMMABLE, HazardClass.EXPLOSIVE,
        "Alevlenici + patlayıcı ayrılmalı."),
    (HazardClass.TOXIC, HazardClass.ACID,
        "Toksik gaz açığa çıkması (örn. sülfürler + asit)."),
    (HazardClass.OXIDIZER, HazardClass.EXPLOSIVE,
        "Patlayıcı reaksiyon."),
]


class Command(BaseCommand):
    help = "GHS piktogramları, H/P ifadeleri ve depolama uyumsuzlukları seed'i."

    @transaction.atomic
    def handle(self, *args, **options) -> None:
        for code, label in PICTOGRAMS:
            Pictogram.objects.update_or_create(
                code=code, defaults={"name": label},
            )
        for code, tr, en in H_STATEMENTS:
            HazardStatement.objects.update_or_create(
                code=code, defaults={"statement": tr, "statement_en": en},
            )
        for code, tr, cat in P_STATEMENTS:
            PrecautionaryStatement.objects.update_or_create(
                code=code, defaults={"statement": tr, "category": cat},
            )
        for a, b, reason in INCOMPATIBILITIES:
            StorageIncompatibility.objects.update_or_create(
                class_a=a, class_b=b, defaults={"reason": reason},
            )
        self.stdout.write(self.style.SUCCESS(
            f"GHS seed: {Pictogram.objects.count()} pictograms, "
            f"{HazardStatement.objects.count()} H, "
            f"{PrecautionaryStatement.objects.count()} P, "
            f"{StorageIncompatibility.objects.count()} incompatibility pairs."
        ))
