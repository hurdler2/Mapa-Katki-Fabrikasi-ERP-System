from django.apps import AppConfig


class RulesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "rules"
    verbose_name = "MCOS Non-Negotiable Rules Enforcer"

    def ready(self) -> None:
        # Signal bağlantıları — import edildiğinde @receiver dekoratörleri devreye girer.
        from . import signals  # noqa: F401
