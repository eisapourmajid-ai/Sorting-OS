# -*- coding: utf-8 -*-
"""Shared test helpers: a throw-away database with all services wired up."""
from __future__ import annotations

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sorting_os.db import AppDatabase  # noqa: E402
from sorting_os.services import (  # noqa: E402
    AuthService,
    BackupService,
    BankingService,
    CatalogService,
    DocumentService,
    ExchangeService,
    LedgerService,
    OperationsService,
    PartyService,
    PeriodService,
    PrintService,
    ReportService,
    SettlementService,
)

ACTOR = "tester"


class ServiceTestCase(unittest.TestCase):
    """Base class creating an isolated SQLite database per test."""

    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tempdir.name, "sorting_os.sqlite3")
        self.db = AppDatabase(self.db_path)
        self.parties = PartyService(self.db)
        self.catalog = CatalogService(self.db)
        self.operations = OperationsService(self.db)
        self.documents = DocumentService(self.db)
        self.ledger = LedgerService(self.db)
        self.settlements = SettlementService(self.db)
        self.banking = BankingService(self.db)
        self.auth = AuthService(self.db)
        self.exchange = ExchangeService(self.db)
        self.reports = ReportService(self.db)
        self.printing = PrintService(self.db)
        self.backups = BackupService(self.db)
        self.periods = PeriodService(self.db)

    def tearDown(self):
        self.tempdir.cleanup()

    # -- fixtures ----------------------------------------------------------- #
    def make_party(self, name="باغدار نمونه", **kwargs):
        kwargs.setdefault("actor", ACTOR)
        return self.parties.create(name, **kwargs)

    def make_shipment(self, owner_id=None, weight=1000.0, **kwargs):
        owner_id = owner_id or self.make_party()
        kwargs.setdefault("actor", ACTOR)
        return self.operations.create_shipment(owner_id, "پرتقال", weight, **kwargs)
