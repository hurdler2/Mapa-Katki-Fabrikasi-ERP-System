"""Menü kayıt defteri — her item için gerekli permission listesi tanımlı.

Kullanıcı bir item'ın gerektirdiği tüm izinlere sahipse (has_perms) gösterilir.
Aksi halde item hiç render edilmez — böylece kullanıcı yetkisiz sayfaları görmez bile.

Portal base template `menu()` fonksiyonunu context processor gibi kullanır.
"""
from __future__ import annotations

from typing import Iterable

from django.contrib.auth.models import User


# Menu şeması:
# {
#   "section": "Başlık",
#   "items": [
#       {"label", "url", "icon", "perms": ["app.view_model", ...], "roles": ["ROLE"]}
#   ]
# }
#
# Bir item için:
# - perms: Django Permission kodları (hepsi geçmeli)
# - roles: Group adı (herhangi biri geçmeli) — perms boşsa buna bakılır
# İkisi de boşsa item herkese gösterilir.

MENU: list[dict] = [
    {
        "section": "Ana Ekran",
        "items": [
            {"label": "Panom", "url": "portal:home", "icon": "🏠"},
            {"label": "Onay Bekleyenler", "url": "portal:approvals_inbox",
             "icon": "✅", "badge": "approvals_count"},
            {"label": "Bildirimler", "url": "notifications:inbox",
             "icon": "🔔", "badge": "unread_count"},
        ],
    },
    {
        "section": "Üretim",
        "items": [
            {"label": "Üretim Panosu", "url": "portal:production",
             "icon": "🏭",
             "perms": ["production.view_productionbatch"]},
            {"label": "Yeni Parti Başlat", "url": "portal:production_start_batch",
             "icon": "▶️",
             "perms": ["production.add_productionbatch"]},
            {"label": "Reçeteler", "url": "portal:recipes",
             "icon": "📖",
             "perms": ["formulation.view_recipe"]},
        ],
    },
    {
        "section": "Kalite",
        "items": [
            {"label": "Kalite Panosu", "url": "portal:quality",
             "icon": "🔬",
             "perms": ["quality.view_qctestresult"]},
            {"label": "Test Sonuçları", "url": "portal:qc_results",
             "icon": "🧪",
             "perms": ["quality.view_qctestresult"]},
            {"label": "COA'lar", "url": "portal:coa_list",
             "icon": "📜",
             "perms": ["quality.view_certificateofanalysis"]},
        ],
    },
    {
        "section": "MCOS",
        "items": [
            {"label": "Kontrollü Kod Register", "url": "portal:registry_list",
             "icon": "📚",
             "perms": ["registry.view_controlledcode"]},
            {"label": "Case'ler / Vakalar", "url": "portal:case_list",
             "icon": "🗂️",
             "perms": ["records.view_case"]},
        ],
    },
    {
        "section": "Kalite Yönetim Sistemi (IMS)",
        "items": [
            {"label": "Uygunsuzluk (NCR)", "url": "portal:ncr_list",
             "icon": "⚠️",
             "perms": ["qms.view_nonconformance"]},
            {"label": "Düzeltici Faaliyet (CAPA)", "url": "portal:capa_list",
             "icon": "🔧",
             "perms": ["qms.view_capa"]},
            {"label": "Dokümanlar (SOP)", "url": "portal:documents",
             "icon": "📄",
             "perms": ["docs.view_controlleddocument"]},
            {"label": "İç Denetim", "url": "portal:internal_audits",
             "icon": "🔍",
             "perms": ["governance.view_internalaudit"]},
            {"label": "Yönetim Gözden Geçirme", "url": "portal:mgmt_reviews",
             "icon": "🗂️",
             "perms": ["governance.view_managementreview"]},
        ],
    },
    {
        "section": "Stok / Depo",
        "items": [
            {"label": "Depo Panosu", "url": "portal:warehouse",
             "icon": "📦",
             "perms": ["inventory.view_rawmateriallot"]},
            {"label": "Yeni Mal Kabul", "url": "portal:warehouse_receipt_new",
             "icon": "📥",
             "perms": ["purchasing.add_goodsreceipt"]},
            {"label": "Hammadde Lotları", "url": "portal:lots_list",
             "icon": "🧪",
             "perms": ["inventory.view_rawmateriallot"]},
        ],
    },
    {
        "section": "Satın Alma",
        "items": [
            {"label": "Satın Alma Panosu", "url": "portal:purchasing",
             "icon": "🛒",
             "perms": ["purchasing.view_purchaseorder"]},
            {"label": "Tedarikçiler", "url": "portal:suppliers",
             "icon": "🏭",
             "perms": ["masterdata.view_supplier"]},
        ],
    },
    {
        "section": "Muhasebe",
        "items": [
            {"label": "Muhasebe Panosu", "url": "portal:accounting",
             "icon": "💰",
             "perms": ["accounting.view_invoice"]},
            {"label": "Faturalar", "url": "portal:accounting_invoices",
             "icon": "🧾",
             "perms": ["accounting.view_invoice"]},
            {"label": "Yeni Fatura", "url": "portal:accounting_invoice_new",
             "icon": "➕",
             "perms": ["accounting.add_invoice"]},
            {"label": "Mizan (Balance)", "url": "portal:trial_balance",
             "icon": "📈",
             "perms": ["accounting.view_account"]},
        ],
    },
    {
        "section": "Bakım (CMMS)",
        "items": [
            {"label": "Bakım Panosu", "url": "portal:maintenance",
             "icon": "🔧",
             "perms": ["cmms.view_workorder"]},
            {"label": "Ekipmanlar", "url": "portal:equipment_list",
             "icon": "⚙️",
             "perms": ["cmms.view_equipment"]},
        ],
    },
    {
        "section": "İSG & Çevre (EHS)",
        "items": [
            {"label": "EHS Panosu", "url": "portal:ehs",
             "icon": "🦺",
             "perms": ["ehs.view_incident"]},
            {"label": "Olay Bildir", "url": "portal:incident_new",
             "icon": "🚨",
             "perms": ["ehs.add_incident"]},
        ],
    },
    {
        "section": "Yönetim Raporları",
        "items": [
            {"label": "BI Dashboard", "url": "portal:bi_link",
             "icon": "📊",
             "roles": ["GENERAL_MANAGER", "TECHNICAL_MANAGER",
                       "OPERATIONS_MANAGER", "IMS_QA_MANAGER",
                       "ACCOUNTING_MANAGER"]},
            {"label": "ISO Denetim Paketi", "url": "portal:iso_link",
             "icon": "📋",
             "roles": ["GENERAL_MANAGER", "IMS_QA_MANAGER"]},
        ],
    },
    {
        "section": "Sistem",
        "items": [
            {"label": "Kullanıcılar", "url": "portal:user_admin",
             "icon": "👥",
             "roles": ["IT_ADMIN"]},
            {"label": "Django Admin", "url": "admin_link",
             "icon": "⚙️",
             "roles": ["IT_ADMIN"]},
        ],
    },
]


def _user_has_perms(user: User, perms: Iterable[str]) -> bool:
    if user.is_superuser:
        return True
    return all(user.has_perm(p) for p in perms)


def _user_has_role(user: User, roles: Iterable[str]) -> bool:
    if user.is_superuser:
        return True
    user_groups = set(user.groups.values_list("name", flat=True))
    return bool(user_groups & set(roles))


def filter_menu_for(user: User) -> list[dict]:
    """Kullanıcıya görünmesi gereken menü ağacını döner."""
    out = []
    for section in MENU:
        visible_items = []
        for item in section["items"]:
            perms = item.get("perms") or []
            roles = item.get("roles") or []
            if perms and not _user_has_perms(user, perms):
                continue
            if roles and not _user_has_role(user, roles):
                continue
            visible_items.append(item)
        if visible_items:
            out.append({"section": section["section"], "items": visible_items})
    return out
