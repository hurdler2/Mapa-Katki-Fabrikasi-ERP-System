"""12 Non-Negotiable kuralı Django signal'lerine bağlar.

pre_save kancaları enforcer.py'deki check_ruleXX fonksiyonlarını çağırır.
İhlal olursa RuleViolationError yükseltilir → transaction rollback edilir,
kayıt oluşmaz. Her ihlal RuleViolation modelinde log'lanır.

Feature flag: settings.MCOS_ENABLE_RULES_ENFORCER=False iken tüm kurallar sessiz.
"""
from __future__ import annotations

from django.db.models.signals import pre_save
from django.dispatch import receiver

from . import enforcer


def _get_old(sender, instance):
    """DB'deki eski instance — save öncesi değişikliği tespit için."""
    if not instance.pk:
        return None
    try:
        return sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        return None


# ---------------------------------------------------------------------------
# R01 + R03 — ProductionBatch
# ---------------------------------------------------------------------------

try:
    from production.models import ProductionBatch

    @receiver(pre_save, sender=ProductionBatch)
    def _rule01_03_batch(sender, instance, **kwargs):
        old = _get_old(sender, instance)
        enforcer.check_rule01_batch_uses_approved_inputs(instance)
        enforcer.check_rule03_release_requires_qc_results(
            instance, old_qc_status=getattr(old, "qc_status", None))
except ImportError:
    pass


# ---------------------------------------------------------------------------
# R02 — MaterialConsumption + ShipmentLine
# ---------------------------------------------------------------------------

try:
    from production.models import MaterialConsumption

    @receiver(pre_save, sender=MaterialConsumption)
    def _rule02_consumption(sender, instance, **kwargs):
        enforcer.check_rule02_consumption_uses_released_lot(instance)
except ImportError:
    pass

try:
    from sales.models import ShipmentLine

    @receiver(pre_save, sender=ShipmentLine)
    def _rule02_shipment(sender, instance, **kwargs):
        enforcer.check_rule02_shipment_line_ships_released_batch(instance)
except ImportError:
    pass


# ---------------------------------------------------------------------------
# R04 — QCTestResult
# ---------------------------------------------------------------------------

try:
    from quality.models import QCTestResult

    @receiver(pre_save, sender=QCTestResult)
    def _rule04_qc(sender, instance, **kwargs):
        enforcer.check_rule04_qc_result_requires_calibrated_equipment(instance)
except ImportError:
    pass


# ---------------------------------------------------------------------------
# R05 — RecordInstance
# ---------------------------------------------------------------------------

try:
    from records.models import RecordInstance

    @receiver(pre_save, sender=RecordInstance)
    def _rule05_record(sender, instance, **kwargs):
        enforcer.check_rule05_record_not_backdated(instance)
except ImportError:
    pass


# ---------------------------------------------------------------------------
# R06 — Recipe
# ---------------------------------------------------------------------------

try:
    from formulation.models import Recipe

    @receiver(pre_save, sender=Recipe)
    def _rule06_recipe(sender, instance, **kwargs):
        old = _get_old(sender, instance)
        enforcer.check_rule06_active_recipe_change_needs_moc(
            instance, old_recipe=old)
except ImportError:
    pass


# ---------------------------------------------------------------------------
# R07 — ApprovalRequest
# ---------------------------------------------------------------------------

try:
    from portal.models import ApprovalRequest

    @receiver(pre_save, sender=ApprovalRequest)
    def _rule07_approval(sender, instance, **kwargs):
        enforcer.check_rule07_approval_veto_respected(instance)
except ImportError:
    pass


# ---------------------------------------------------------------------------
# R08 — Incident
# ---------------------------------------------------------------------------

try:
    from ehs.models import Incident

    @receiver(pre_save, sender=Incident)
    def _rule08_incident(sender, instance, **kwargs):
        enforcer.check_rule08_hse_incident_severity(instance)
except ImportError:
    pass


# ---------------------------------------------------------------------------
# R09 — Decision
# ---------------------------------------------------------------------------

try:
    from records.models import Decision

    @receiver(pre_save, sender=Decision)
    def _rule09_decision(sender, instance, **kwargs):
        enforcer.check_rule09_decision_maker_has_authority(instance)
except ImportError:
    pass


# ---------------------------------------------------------------------------
# R10 — CAPA
# ---------------------------------------------------------------------------

try:
    from qms.models import CAPA

    @receiver(pre_save, sender=CAPA)
    def _rule10_capa(sender, instance, **kwargs):
        enforcer.check_rule10_capa_close_requires_effectiveness(instance)
except ImportError:
    pass


# ---------------------------------------------------------------------------
# R11 — ControlledCode
# ---------------------------------------------------------------------------

try:
    from registry.models import ControlledCode

    @receiver(pre_save, sender=ControlledCode)
    def _rule11_code(sender, instance, **kwargs):
        enforcer.check_rule11_controlled_code_owner_required(instance)
except ImportError:
    pass


# ---------------------------------------------------------------------------
# R12 — Case (log-only, block etmez)
# ---------------------------------------------------------------------------

try:
    from records.models import Case

    @receiver(pre_save, sender=Case)
    def _rule12_case(sender, instance, **kwargs):
        # Sadece yeni oluşturmada eskale et
        if instance.pk:
            return
        enforcer.check_rule12_severe_case_escalated(instance)
except ImportError:
    pass
