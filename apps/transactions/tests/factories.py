"""
Mise HERo Finance - Test Factories
===================================
Factory Boy factories for generating test data.
"""

import random
from datetime import date, timedelta
from decimal import Decimal

import factory
from factory.django import DjangoModelFactory

from apps.core.models import User
from apps.transactions.models import (CategoryRule, ImportBatch, Product,
                                      ProductSubgroup, Project, Transaction)


class UserFactory(DjangoModelFactory):
    """Factory for creating test users."""

    class Meta:
        model = User

    email = factory.Sequence(lambda n: f"user{n}@example.com")
    first_name = factory.Faker("first_name", locale="cs_CZ")
    last_name = factory.Faker("last_name", locale="cs_CZ")
    role = "viewer"
    is_active = True

    @factory.post_generation
    def password(obj, create, extracted, **kwargs):
        if extracted:
            obj.set_password(extracted)
        else:
            obj.set_password("testpassword123")
        if create:
            obj.save()


class AdminUserFactory(UserFactory):
    """Factory for creating admin users."""

    role = "admin"
    is_staff = True


class ProjectFactory(DjangoModelFactory):
    """Factory for creating test projects."""

    class Meta:
        model = Project

    id = factory.Sequence(lambda n: f"project-{n}")
    name = factory.Sequence(lambda n: f"Project {n}")
    description = factory.Faker("sentence")
    is_active = True


class ProductFactory(DjangoModelFactory):
    """Factory for creating test products."""

    class Meta:
        model = Product

    id = factory.Sequence(lambda n: f"product-{n}")
    name = factory.Sequence(lambda n: f"Product {n}")
    category = factory.Iterator(["SKOLY", "FIRMY"])
    description = factory.Faker("sentence")
    is_active = True


class ProductSubgroupFactory(DjangoModelFactory):
    """Factory for creating test product subgroups."""

    class Meta:
        model = ProductSubgroup

    id = factory.Sequence(lambda n: f"subgroup-{n}")
    product = factory.SubFactory(ProductFactory)
    name = factory.Sequence(lambda n: f"Subgroup {n}")
    description = factory.Faker("sentence")
    is_active = True


class TransactionFactory(DjangoModelFactory):
    """Factory for creating test transactions."""

    class Meta:
        model = Transaction

    # Bank columns
    datum = factory.LazyFunction(
        lambda: date.today() - timedelta(days=random.randint(0, 365))
    )
    ucet = factory.Iterator(["123456789/0100", "987654321/0300", "555555555/0600"])
    typ = factory.Iterator(["Příchozí platba", "Odchozí platba", "Trvalý příkaz"])
    poznamka_zprava = factory.Faker("sentence", locale="cs_CZ")
    variabilni_symbol = factory.Sequence(lambda n: str(n).zfill(10))
    castka = factory.LazyFunction(lambda: Decimal(str(random.randint(-50000, 50000))))

    datum_zauctovani = factory.LazyAttribute(lambda o: o.datum + timedelta(days=1))
    cislo_protiuctu = factory.Sequence(lambda n: f"{n:09d}/0100")
    nazev_protiuctu = factory.Faker("company", locale="cs_CZ")
    typ_transakce = factory.Iterator(["Převod", "Platba kartou", "SEPA"])
    mena = "CZK"

    id_transakce = factory.Sequence(lambda n: f"TXN{n:012d}")

    # App columns with defaults
    status = "importovano"
    prijem_vydaj = factory.LazyAttribute(lambda o: "P" if o.castka > 0 else "V")
    vlastni_nevlastni = "V"
    dane = False
    druh = ""
    detail = ""
    kmen = ""
    mh_pct = Decimal("0")
    sk_pct = Decimal("0")
    xp_pct = Decimal("0")
    fr_pct = Decimal("0")


class CategorizedTransactionFactory(TransactionFactory):
    """Factory for creating fully categorized transactions."""

    status = "zpracovano"
    druh = factory.Iterator(["Fixní", "Variabilní", "Mzdy", "Projekt EU", "Grant CZ"])
    detail = factory.Faker("sentence", locale="cs_CZ")
    kmen = factory.Iterator(["MH", "SK", "XP", "FR"])

    # Properly distributed KMEN percentages
    @factory.lazy_attribute
    def mh_pct(self):
        return Decimal("100") if self.kmen == "MH" else Decimal("0")

    @factory.lazy_attribute
    def sk_pct(self):
        return Decimal("100") if self.kmen == "SK" else Decimal("0")

    @factory.lazy_attribute
    def xp_pct(self):
        return Decimal("100") if self.kmen == "XP" else Decimal("0")

    @factory.lazy_attribute
    def fr_pct(self):
        return Decimal("100") if self.kmen == "FR" else Decimal("0")


class SplitTransactionFactory(TransactionFactory):
    """Factory for creating transactions with KMEN split."""

    status = "zpracovano"
    druh = "Variabilní"
    kmen = ""  # No primary KMEN when split
    mh_pct = Decimal("25")
    sk_pct = Decimal("25")
    xp_pct = Decimal("25")
    fr_pct = Decimal("25")


class CategoryRuleFactory(DjangoModelFactory):
    """Factory for creating category rules."""

    class Meta:
        model = CategoryRule

    name = factory.Sequence(lambda n: f"Rule {n}")
    description = factory.Faker("sentence")
    match_type = factory.Iterator(["protiucet", "merchant", "keyword"])
    match_mode = "contains"
    match_value = factory.Faker("word")
    case_sensitive = False
    priority = factory.Sequence(lambda n: n * 10)
    is_active = True


class ImportBatchFactory(DjangoModelFactory):
    """Factory for creating import batches."""

    class Meta:
        model = ImportBatch

    filename = factory.Sequence(lambda n: f"import_{n}.csv")
    status = "completed"
    total_rows = factory.LazyFunction(lambda: random.randint(10, 500))
    imported_count = factory.LazyAttribute(
        lambda o: o.total_rows - random.randint(0, 10)
    )
    skipped_count = factory.LazyAttribute(lambda o: o.total_rows - o.imported_count)
    error_count = 0
    error_details = []
