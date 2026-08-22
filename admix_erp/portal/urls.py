from django.urls import path

from . import views, views_extra

app_name = "portal"

urlpatterns = [
    path("", views.home, name="home"),

    # Onaylar
    path("onaylar/", views_extra.approvals_inbox, name="approvals_inbox"),
    path("onaylar/<int:pk>/", views_extra.approval_decide, name="approval_decide"),

    # MCOS Faz A — BusinessLine selector
    path("bl/switch/", views_extra.switch_business_line, name="switch_bl"),

    # MCOS Faz C — Controlled Code Register
    path("registry/", views_extra.registry_list_view, name="registry_list"),
    path("registry/<int:pk>/", views_extra.registry_detail_view, name="registry_detail"),

    # MCOS Faz D — 5-Katman ID Modeli (Case / Record / Decision)
    path("cases/", views_extra.case_list_view, name="case_list"),
    path("cases/<str:case_id>/", views_extra.case_detail_view, name="case_detail"),
    path("records/<str:record_id>/", views_extra.record_detail_view, name="record_detail"),
    path("decisions/<str:decision_id>/", views_extra.decision_detail_view, name="decision_detail"),

    # MCOS Faz E — 8-Part Gate Model
    path("gates/", views_extra.gate_list_view, name="gate_list"),
    path("gates/<str:gate_id>/", views_extra.gate_detail_view, name="gate_detail"),

    # MCOS Faz G — Master Register (integrated + security)
    path("master/integrated/", views_extra.master_integrated_list_view,
         name="master_integrated_list"),
    path("master/integrated/<str:event_id>/",
         views_extra.master_integrated_detail_view,
         name="master_integrated_detail"),
    path("master/security/", views_extra.master_security_list_view,
         name="master_security_list"),

    # MCOS Faz H — Non-Negotiable Rules Enforcer
    path("kurallar/", views_extra.violation_list_view, name="violation_list"),
    path("kurallar/katalog/", views_extra.rules_catalog_view, name="rules_catalog"),
    path("kurallar/<int:pk>/resolve/", views_extra.violation_resolve_view,
         name="violation_resolve"),

    # Muhasebe
    path("muhasebe/", views.accounting_dashboard, name="accounting"),
    path("muhasebe/faturalar/", views.accounting_invoices, name="accounting_invoices"),
    path("muhasebe/faturalar/yeni/", views.accounting_invoice_new,
         name="accounting_invoice_new"),
    path("muhasebe/faturalar/<int:pk>/", views.accounting_invoice_detail,
         name="accounting_invoice_detail"),
    path("muhasebe/mizan/", views_extra.trial_balance_view, name="trial_balance"),

    # Üretim
    path("uretim/", views.production_dashboard, name="production"),
    path("uretim/parti-baslat/", views.production_start_batch,
         name="production_start_batch"),
    path("uretim/emir/<int:pk>/", views.production_order_detail,
         name="production_order_detail"),
    path("recete/", views_extra.recipes_list, name="recipes"),
    path("recete/yeni/", views.formulation_new, name="formulation_new"),

    # Kalite
    path("kalite/", views.quality_dashboard, name="quality"),
    path("kalite/test-sonuclari/", views_extra.qc_results_list, name="qc_results"),
    path("kalite/coa/", views_extra.coa_list, name="coa_list"),
    # Sprint 9 — SDS / DoP / FPC audit yasal uyum
    path("uyum/sds/", views.sds_list, name="sds_list"),
    path("uyum/sds/<int:pk>/pdf/", views.sds_pdf, name="sds_pdf"),
    path("uyum/dop/", views.dop_list, name="dop_list"),
    path("uyum/dop/<int:pk>/pdf/", views.dop_pdf, name="dop_pdf"),
    path("uyum/fpc-audit/", views.fpc_audit_list, name="fpc_audit_list"),
    path("uyum/reach-svhc/", views.reach_svhc_list, name="reach_svhc_list"),

    # SCADA entegrasyon durumu
    path("scada/", views.scada_dashboard, name="scada_dashboard"),

    # Sprint 8 — Facture de dépense + multi-line ajustement
    path("muhasebe/gider/", views.expense_list, name="expense_list"),
    path("muhasebe/gider/yeni/", views.expense_new, name="expense_new"),
    path("muhasebe/gider/<int:pk>/", views.expense_detail, name="expense_detail"),
    path("stok/ajustement/multi/", views.multi_line_adjustment_new,
         name="multi_line_adjustment_new"),

    # Sprint 5 — Müşteri avansı (§23)
    path("muhasebe/avans/", views.customer_advances_list, name="customer_advances"),
    path("muhasebe/avans/<int:pk>/tahsis/", views.advance_allocate,
         name="advance_allocate"),

    # Sprint 4 — Stok detay + Reporting hub
    path("stok/hammadde/<int:pk>/", views.raw_material_detail, name="raw_material_detail"),
    path("rapor/", views.reporting_hub, name="reporting_hub"),

    # Sprint 6 — Detaylı raporlar
    path("rapor/echeancier-clients/", views.report_aging_clients, name="report_aging_clients"),
    path("rapor/valorisation-stocks/", views.report_stock_valuation, name="report_stock_valuation"),
    path("rapor/rendements-production/", views.report_production_yields, name="report_production_yields"),
    path("rapor/bl-fatura/", views.report_bl_invoice_matching, name="report_bl_invoice"),
    path("muhasebe/cari/<int:customer_pk>/", views.customer_statement, name="customer_statement"),
    path("stok/ajustement/yeni/", views.stock_adjustment_new, name="stock_adjustment_new"),

    # Sales / BL Client
    path("satis/bl/", views.bl_client_list, name="bl_client_list"),
    path("satis/bl/<int:pk>/", views.bl_client_detail, name="bl_client_detail"),
    path("satis/bl/faturaya-donustur/", views.bl_to_invoice_view, name="bl_to_invoice"),

    path("kalite/sartname/", views.quality_specs_list, name="quality_specs"),
    path("kalite/sartname/<int:pk>/", views.quality_spec_detail, name="quality_spec_detail"),
    path("kalite/orneklem-plani/", views.sampling_plans_list, name="sampling_plans"),
    path("kalite/katalog/", views.quality_catalog, name="quality_catalog"),

    # QMS
    path("ims/ncr/", views_extra.ncr_list, name="ncr_list"),
    path("ims/capa/", views_extra.capa_list, name="capa_list"),
    path("ims/dokumanlar/", views_extra.documents_list, name="documents"),
    path("ims/ic-denetim/", views_extra.internal_audits, name="internal_audits"),
    path("ims/yonetim-gozden-gecirme/", views_extra.mgmt_reviews, name="mgmt_reviews"),

    # Depo
    path("stok/", views.warehouse_dashboard, name="warehouse"),
    path("stok/mal-kabul/", views.warehouse_receipt_new,
         name="warehouse_receipt_new"),
    path("stok/lotlar/", views_extra.lots_list, name="lots_list"),

    # Satın alma
    path("satin-alma/", views.purchasing_dashboard, name="purchasing"),
    path("tedarikci/", views_extra.suppliers_list, name="suppliers"),

    # Bakım
    path("bakim/", views.maintenance_dashboard, name="maintenance"),
    path("bakim/ekipmanlar/", views_extra.equipment_list, name="equipment_list"),

    # EHS
    path("ehs/", views.ehs_dashboard, name="ehs"),
    path("ehs/olay-bildir/", views_extra.incident_new, name="incident_new"),

    # Yönetim
    path("yonetim/", views.management_dashboard, name="management"),

    # BT
    path("bt/", views_extra.user_admin, name="user_admin"),

    # Ghost URL'ler (menü'den link vermek için) — gerçekte redirect
    path("bi/", lambda r: __import__("django").shortcuts.redirect("/analytics/bi/"), name="bi_link"),
    path("iso/", lambda r: __import__("django").shortcuts.redirect("/analytics/iso-audit/"), name="iso_link"),
]
