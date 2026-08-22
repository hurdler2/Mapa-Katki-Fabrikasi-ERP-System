"""SCADA entegratörüne verilecek user + token'ı hazırlar.

Kullanım:
    python manage.py scada_setup
    python manage.py scada_setup --rotate     # token yeniden üret
"""
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand
from rest_framework.authtoken.models import Token


SCADA_USERNAME = "scada_bridge"
SCADA_GROUP = "SCADA_BRIDGE"

REQUIRED_PERMS = [
    ("production", "productionbatch", "add"),
    ("production", "productionbatch", "view"),
    ("production", "productionorder", "add"),
    ("production", "productionorder", "view"),
    ("production", "materialconsumption", "add"),
    ("production", "materialconsumption", "view"),
    ("quality", "qctestresult", "add"),
    ("quality", "qctestresult", "view"),
    ("quality", "qcspec", "view"),
    ("formulation", "recipe", "view"),
    ("masterdata", "rawmaterial", "view"),
    ("masterdata", "product", "view"),
    ("masterdata", "container", "view"),
]


class Command(BaseCommand):
    help = "SCADA entegrasyonu için bridge user + token oluştur/rotate et."

    def add_arguments(self, parser):
        parser.add_argument(
            "--rotate",
            action="store_true",
            help="Var olan token'ı sil ve yenisini üret.",
        )

    def handle(self, *args, **options):
        User = get_user_model()

        # 1) SCADA bridge user
        user, created = User.objects.get_or_create(
            username=SCADA_USERNAME,
            defaults={
                "first_name": "SCADA",
                "last_name": "Bridge",
                "is_active": True,
                "is_staff": False,
            },
        )
        if created:
            user.set_unusable_password()
            user.save()
            self.stdout.write(self.style.SUCCESS(f"OK yeni user olusturuldu: {SCADA_USERNAME}"))
        else:
            self.stdout.write(f"user zaten var: {SCADA_USERNAME}")

        # 2) SCADA grubu ve izinler
        group, _ = Group.objects.get_or_create(name=SCADA_GROUP)
        perms = []
        for app, model, action in REQUIRED_PERMS:
            perm = Permission.objects.filter(
                content_type__app_label=app,
                content_type__model=model,
                codename=f"{action}_{model}",
            ).first()
            if perm:
                perms.append(perm)
        group.permissions.set(perms)
        user.groups.add(group)
        self.stdout.write(f"{len(perms)} izin gruba baglandi")

        # 3) Token
        if options["rotate"]:
            Token.objects.filter(user=user).delete()
            self.stdout.write(self.style.WARNING("eski token silindi"))

        token, tcreated = Token.objects.get_or_create(user=user)

        # 4) Sonuc bilgisi
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=" * 68))
        self.stdout.write(self.style.SUCCESS("SCADA BRIDGE BILGILERI"))
        self.stdout.write(self.style.SUCCESS("=" * 68))
        self.stdout.write(f"Username:      {user.username}")
        self.stdout.write(f"Token:         {token.key}")
        self.stdout.write("")
        self.stdout.write("Node-RED / SCADA icin HTTP header:")
        self.stdout.write(f"  Authorization: Token {token.key}")
        self.stdout.write("")
        self.stdout.write("Test komutu (curl):")
        self.stdout.write(f'  curl -H "Authorization: Token {token.key}" \\')
        self.stdout.write("       http://ERP_HOST:8000/api/v1/production/scada/status/")
        self.stdout.write("")
        self.stdout.write(self.style.WARNING(
            "GUVENLIK: Bu token'i SADECE SCADA sunucusunda saklayin."
        ))
        self.stdout.write(self.style.WARNING(
            "6 ayda bir 'scada_setup --rotate' ile yenileyin."
        ))
        self.stdout.write(self.style.SUCCESS("=" * 68))
