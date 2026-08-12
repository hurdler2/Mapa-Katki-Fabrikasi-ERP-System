"""Cezayir SCF (PCN 2010) hesap planı, TVA oranları, yevmiye kodları seed'i.

Referans: Ministerial Order No. 26 of 29 July 2008 (SCF).
"""
from __future__ import annotations

from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from accounting.models import Account, JournalCode, TVARate


# SCF ana hesap planı (yaygın kullanılan hesaplar)
ACCOUNTS = [
    # (code, name, type, is_leaf)
    # SINIF 1 — Sermaye
    ("10", "Capital", "EQUITY", False),
    ("101", "Capital souscrit / apporté", "EQUITY", True),
    ("106", "Réserves", "EQUITY", False),
    ("1061", "Réserve légale", "EQUITY", True),
    ("11", "Report à nouveau", "EQUITY", True),
    ("12", "Résultat de l'exercice", "EQUITY", True),
    ("13", "Subventions d'investissement", "EQUITY", True),
    ("16", "Emprunts et dettes assimilées", "LIABILITY", False),
    ("164", "Emprunts auprès des établissements de crédit", "LIABILITY", True),

    # SINIF 2 — Duran varlıklar
    ("21", "Immobilisations corporelles", "ASSET", False),
    ("211", "Terrains", "ASSET", True),
    ("213", "Constructions", "ASSET", True),
    ("2154", "Matériel industriel", "ASSET", True),
    ("2157", "Matériel de laboratoire", "ASSET", True),
    ("2182", "Matériel de transport", "ASSET", True),
    ("2183", "Matériel informatique", "ASSET", True),
    ("2184", "Mobilier de bureau", "ASSET", True),
    ("28", "Amortissements des immobilisations", "ASSET", False),
    ("2813", "Amortissement constructions", "ASSET", True),
    ("28154", "Amortissement matériel industriel", "ASSET", True),
    ("28157", "Amortissement matériel de laboratoire", "ASSET", True),
    ("28182", "Amortissement matériel de transport", "ASSET", True),
    ("28183", "Amortissement matériel informatique", "ASSET", True),
    ("28184", "Amortissement mobilier", "ASSET", True),

    # SINIF 3 — Stoklar
    ("31", "Matières premières", "ASSET", True),
    ("32", "Autres approvisionnements", "ASSET", True),
    ("33", "En-cours de production", "ASSET", True),
    ("35", "Stocks de produits finis", "ASSET", True),
    ("37", "Stocks de marchandises", "ASSET", True),

    # SINIF 4 — Cariler
    ("40", "Fournisseurs et comptes rattachés", "LIABILITY", False),
    ("401", "Fournisseurs", "LIABILITY", True),
    ("4091", "Fournisseurs - avances versées", "ASSET", True),
    ("41", "Clients et comptes rattachés", "ASSET", False),
    ("411", "Clients", "ASSET", True),
    ("4191", "Clients - avances reçues", "LIABILITY", True),
    ("42", "Personnel et comptes rattachés", "LIABILITY", False),
    ("421", "Personnel - rémunérations dues", "LIABILITY", True),
    ("43", "Organismes sociaux (CNAS/CASNOS)", "LIABILITY", False),
    ("431", "Sécurité sociale", "LIABILITY", True),
    ("44", "État et collectivités publiques", "LIABILITY", False),
    ("441", "État - subventions à recevoir", "ASSET", True),
    ("444", "IBS - impôt sur les bénéfices", "LIABILITY", True),
    ("445", "TVA à décaisser / à récupérer", "LIABILITY", False),
    ("4456", "TVA déductible", "ASSET", False),
    ("44566", "TVA déductible sur biens/services", "ASSET", True),
    ("44567", "Crédit de TVA à reporter", "ASSET", True),
    ("4457", "TVA collectée", "LIABILITY", True),
    ("4458", "TVA à décaisser (net)", "LIABILITY", True),

    # SINIF 5 — Finansal
    ("51", "Banques et établissements financiers", "ASSET", False),
    ("512", "Banques - compte courant DZD", "ASSET", True),
    ("53", "Caisse", "ASSET", True),
    ("58", "Virements internes", "ASSET", True),

    # SINIF 6 — Giderler
    ("60", "Achats consommés", "EXPENSE", False),
    ("601", "Achats de matières premières", "EXPENSE", True),
    ("602", "Achats d'autres approvisionnements", "EXPENSE", True),
    ("607", "Achats de marchandises", "EXPENSE", True),
    ("61", "Services extérieurs", "EXPENSE", False),
    ("6111", "Sous-traitance générale", "EXPENSE", True),
    ("6132", "Locations", "EXPENSE", True),
    ("6152", "Entretien et réparations", "EXPENSE", True),
    ("6161", "Assurances", "EXPENSE", True),
    ("62", "Autres services extérieurs", "EXPENSE", False),
    ("6226", "Honoraires (audit/consulting)", "EXPENSE", True),
    ("6241", "Transports sur ventes", "EXPENSE", True),
    ("6261", "Frais postaux et télécommunications", "EXPENSE", True),
    ("63", "Impôts, taxes et versements assimilés", "EXPENSE", False),
    ("64", "Charges de personnel", "EXPENSE", False),
    ("641", "Rémunérations du personnel", "EXPENSE", True),
    ("645", "Charges de sécurité sociale", "EXPENSE", True),
    ("65", "Autres charges de gestion courante", "EXPENSE", True),
    ("66", "Charges financières", "EXPENSE", False),
    ("661", "Charges d'intérêts", "EXPENSE", True),
    ("68", "Dotations aux amortissements et provisions", "EXPENSE", False),
    ("681", "Dotations aux amortissements", "EXPENSE", True),

    # SINIF 7 — Gelirler
    ("70", "Ventes de produits finis / marchandises", "REVENUE", False),
    ("701", "Ventes de produits finis", "REVENUE", True),
    ("707", "Ventes de marchandises", "REVENUE", True),
    ("74", "Subventions d'exploitation", "REVENUE", True),
    ("75", "Autres produits de gestion courante", "REVENUE", True),
    ("76", "Produits financiers", "REVENUE", False),
    ("761", "Produits des participations", "REVENUE", True),
]


TVA_RATES = [
    ("TVA19", "TVA Normale", Decimal("19.00")),
    ("TVA9", "TVA Réduite", Decimal("9.00")),
    ("TVA0", "TVA Exonérée", Decimal("0.00")),
]


JOURNAL_CODES = [
    ("JV", "Journal des ventes", "SALES"),
    ("JA", "Journal des achats", "PURCHASE"),
    ("JB", "Journal de banque", "BANK"),
    ("JC", "Journal de caisse", "CASH"),
    ("JO", "Journal des opérations diverses", "OPERATIONS"),
    ("JOU", "Journal d'ouverture", "OPENING"),
    ("JCL", "Journal de clôture", "CLOSING"),
    ("JP", "Journal de paie", "PAYROLL"),
    ("JD", "Journal des amortissements", "DEPRECIATION"),
]


class Command(BaseCommand):
    help = "Cezayir SCF (PCN 2010) hesap planı, TVA ve yevmiye kodları seed'i."

    @transaction.atomic
    def handle(self, *args, **options) -> None:
        # Hesap planı — iki geçiş: önce oluştur, sonra parent bağla
        code_to_acc: dict[str, Account] = {}
        for code, name, type_, is_leaf in ACCOUNTS:
            acc, _ = Account.objects.update_or_create(
                code=code,
                defaults={
                    "name": name, "account_type": type_,
                    "account_class": code[0], "is_leaf": is_leaf,
                    "is_active": True,
                },
            )
            code_to_acc[code] = acc

        # Parent atama (uzun kod → daha kısa kod ile başlayan)
        for code, acc in code_to_acc.items():
            if len(code) <= 1:
                continue
            # En uzun eşleşen prefix
            for i in range(len(code) - 1, 0, -1):
                cand = code[:i]
                if cand in code_to_acc and cand != code:
                    acc.parent = code_to_acc[cand]
                    acc.save(update_fields=["parent"])
                    break

        # TVA oranları
        collected = code_to_acc.get("4457")
        deductible = code_to_acc.get("44566")
        for code, name, rate in TVA_RATES:
            TVARate.objects.update_or_create(
                code=code,
                defaults={
                    "name": name, "rate_pct": rate,
                    "collected_account": collected, "deductible_account": deductible,
                    "is_active": True,
                },
            )

        # Yevmiye kodları
        for code, name, jtype in JOURNAL_CODES:
            JournalCode.objects.update_or_create(
                code=code,
                defaults={"name": name, "type": jtype, "is_active": True},
            )

        self.stdout.write(self.style.SUCCESS(
            f"SCF seed: {Account.objects.count()} accounts, "
            f"{TVARate.objects.count()} TVA rates, "
            f"{JournalCode.objects.count()} journal codes."
        ))
