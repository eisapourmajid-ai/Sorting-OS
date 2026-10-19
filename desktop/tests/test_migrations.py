# -*- coding: utf-8 -*-
"""Migration framework: fresh install, legacy upgrade and idempotency."""
from __future__ import annotations

import os
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import Database  # noqa: E402  (legacy MVP schema)
from sorting_os.db import AppDatabase  # noqa: E402
from sorting_os.migrations import LATEST_SCHEMA_VERSION  # noqa: E402


class MigrationTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tempdir.cleanup()

    def test_fresh_database_is_migrated_to_the_latest_version(self):
        path = os.path.join(self.tempdir.name, "fresh.sqlite3")
        db = AppDatabase(path)
        self.assertEqual(db.schema_version(), LATEST_SCHEMA_VERSION)
        self.assertEqual(db.integrity_check(), "ok")
        with db.reader() as con:
            tables = {row[0] for row in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        for expected in ("parties", "shipments", "invoices", "invoice_lines",
                         "journal_entries", "inventory_transactions", "settlements",
                         "bank_transactions", "cheques", "users", "print_templates",
                         "fiscal_periods", "settlement_rates"):
            self.assertIn(expected, tables)

    def test_settlement_rate_columns_exist(self):
        path = os.path.join(self.tempdir.name, "rates.sqlite3")
        db = AppDatabase(path)
        with db.reader() as con:
            settlement_columns = {row[1] for row in con.execute(
                "PRAGMA table_info(settlements)").fetchall()}
        for column in ("invoice_id", "rate_source", "rate_id"):
            self.assertIn(column, settlement_columns)

    def test_migration_is_idempotent(self):
        path = os.path.join(self.tempdir.name, "again.sqlite3")
        db = AppDatabase(path)
        self.assertEqual(db.migrate(), [])
        self.assertEqual(db.schema_version(), LATEST_SCHEMA_VERSION)

    def test_legacy_database_upgrades_without_losing_data(self):
        path = os.path.join(self.tempdir.name, "legacy.sqlite3")
        legacy = Database(path)
        party_id = legacy.save_party(
            {"display_name": "باغدار قدیمی", "national_id": "0012345678"}, actor="تست")
        legacy.create_shipment(party_id, "پرتقال", 500, actor="تست")
        legacy.create_invoice(party_id, "فروش", "2026-01-02", 1000, "قدیمی",
                              status="قطعی", actor="تست")
        self.assertEqual(legacy.counts()["parties"], 1)

        db = AppDatabase(path)
        self.assertEqual(db.schema_version(), LATEST_SCHEMA_VERSION)
        with db.reader() as con:
            self.assertEqual(con.execute("SELECT COUNT(*) FROM parties").fetchone()[0], 1)
            self.assertEqual(con.execute("SELECT COUNT(*) FROM shipments").fetchone()[0], 1)
            invoices = con.execute(
                "SELECT amount, amount_rial, currency_unit FROM invoices").fetchone()
            # the legacy amount keeps its unknown unit and is never posted
            self.assertIsNone(invoices["amount_rial"])
            self.assertIsNone(invoices["currency_unit"])
            # the ledger stays empty: legacy rows are not silently reinterpreted
            self.assertEqual(con.execute("SELECT COUNT(*) FROM journal_entries").fetchone()[0], 0)

    def test_legacy_invoice_cannot_be_posted(self):
        from sorting_os.core import ConflictError
        from sorting_os.services import LedgerService

        path = os.path.join(self.tempdir.name, "legacy_post.sqlite3")
        legacy = Database(path)
        party_id = legacy.save_party({"display_name": "قدیمی"}, actor="تست")
        legacy.create_invoice(party_id, "فروش", "2026-01-02", 1000, "قدیمی",
                              status="قطعی", actor="تست")
        db = AppDatabase(path)
        with db.reader() as con:
            invoice_id = con.execute("SELECT id FROM invoices").fetchone()[0]
        with self.assertRaises(ConflictError):
            LedgerService(db).post_invoice(invoice_id, actor="تست")

    def test_failed_migration_leaves_database_untouched(self):
        path = os.path.join(self.tempdir.name, "broken.sqlite3")
        db = AppDatabase(path)
        with db.transaction() as con:
            # a view with the same name makes the migration fail on purpose
            con.execute("DROP TABLE settings")
            con.execute("CREATE VIEW settings AS SELECT 1 AS dummy")
            con.execute("UPDATE schema_meta SET value='1' WHERE key='schema_version'")
        with self.assertRaises(Exception):
            db.migrate()
        # the failed migration rolled back completely: version 1 is still recorded
        self.assertEqual(db.schema_version(), 1)
        with db.reader() as con:
            self.assertEqual(con.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='settings'"
            ).fetchone()[0], 0)

    def test_foreign_keys_are_enforced(self):
        path = os.path.join(self.tempdir.name, "fk.sqlite3")
        db = AppDatabase(path)
        with self.assertRaises(sqlite3.IntegrityError):
            with db.transaction() as con:
                con.execute(
                    """INSERT INTO shipment_lines(shipment_id, product_id, grade_id, packaging_id,
                            description, quantity, unit, weight_kg, created_at)
                       VALUES(9999, NULL, NULL, NULL, 'x', 0, 'kg', 0, '2026-01-01')""")


if __name__ == "__main__":
    unittest.main()
