# -*- coding: utf-8 -*-
"""Historical data migration with an explicit unit (Prompt 32)."""
from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sorting_os.core import ValidationError  # noqa: E402
from sorting_os.services.migration import LegacyMigrationService  # noqa: E402
from support import ACTOR, ServiceTestCase  # noqa: E402


class LegacyInvoiceFactory(object):
    """Creates legacy invoices (REAL amount, no unit) in the same database."""

    def __init__(self, db, actor=ACTOR):
        self.db = db
        self.actor = actor

    def add(self, party_id, amount, document_date="2026-01-01", code=None, status="قطعی"):
        with self.db.transaction() as con:
            if code is None:
                code = "LG-%d" % (con.execute("SELECT COUNT(*) FROM invoices").fetchone()[0] + 1)
            cur = con.execute(
                """INSERT INTO invoices(code, party_id, invoice_type, document_date, amount,
                        description, status, created_at, created_by)
                   VALUES(?,?,?,?,?,?,?,?,?)""",
                (code, party_id, "فروش", document_date, float(amount), "داده تاریخی",
                 status, "2026-01-01 00:00:00", self.actor))
            return cur.lastrowid


class MigrationTests(ServiceTestCase):
    def setUp(self):
        super().setUp()
        self.factory = LegacyInvoiceFactory(self.db)
        self.service = LegacyMigrationService(self.db, actor=ACTOR)
        self.party_id = self.make_party("طرف تاریخی", roles=["customer"])

    def test_scan_detects_pending_rows(self):
        self.factory.add(self.party_id, 5_000_000)
        report = self.service.scan()
        self.assertEqual(report["pending_rows"], 1)
        self.assertTrue(report["needs_unit_decision"])
        self.assertEqual(report["open_decision"], "DEC-013")

    def test_unit_must_be_explicit(self):
        self.factory.add(self.party_id, 5_000_000)
        with self.assertRaises(ValidationError):
            self.service.preview(unit="")
        with self.assertRaises(ValidationError):
            self.service.preview(unit="خودکار")

    def test_preview_does_not_write(self):
        self.factory.add(self.party_id, 5_000_000)
        preview = self.service.preview("ریال")
        self.assertEqual(preview["row_count"], 1)
        self.assertEqual(preview["total_rial"], 5_000_000)
        with self.db.reader() as con:
            row = con.execute("SELECT amount_rial FROM invoices").fetchone()
        self.assertIsNone(row["amount_rial"])

    def test_toman_source_is_converted_to_rial(self):
        self.factory.add(self.party_id, 1_250)
        preview = self.service.preview("تومان")
        self.assertEqual(preview["total_rial"], 12_500)

    def test_fractional_rial_rows_are_reported_as_errors(self):
        self.factory.add(self.party_id, 5_000)
        with self.db.transaction() as con:
            con.execute("UPDATE invoices SET amount=12.5")
        preview = self.service.preview("ریال")
        self.assertEqual(preview["row_count"], 0)
        self.assertEqual(preview["error_count"], 1)
        self.assertIn("id", preview["errors"][0])

    def test_migration_writes_exact_rial_and_keeps_the_ledger_clean(self):
        self.factory.add(self.party_id, 5_000_000)
        result = self.service.migrate("ریال", actor=ACTOR)
        self.assertEqual(result["migrated"], 1)
        self.assertEqual(result["total_rial"], 5_000_000)
        self.assertEqual(result["posted"], 0)
        with self.db.reader() as con:
            row = con.execute("SELECT amount_rial, currency_unit FROM invoices").fetchone()
            entries = con.execute("SELECT COUNT(*) FROM journal_entries").fetchone()[0]
        self.assertEqual(row["amount_rial"], 5_000_000)
        self.assertEqual(row["currency_unit"], "ریال")
        self.assertEqual(entries, 0, "مهاجرت نباید خودکار به دفترکل post کند")

    def test_migration_is_idempotent(self):
        self.factory.add(self.party_id, 5_000_000)
        self.service.migrate("ریال", actor=ACTOR)
        again = self.service.migrate("ریال", actor=ACTOR)
        self.assertEqual(again["migrated"], 0)
        with self.db.reader() as con:
            count = con.execute("SELECT COUNT(*) FROM invoices").fetchone()[0]
        self.assertEqual(count, 1)

    def test_posting_requires_an_explicit_confirmation(self):
        self.factory.add(self.party_id, 5_000_000)
        with self.assertRaises(ValidationError):
            self.service.migrate("ریال", actor=ACTOR, post_to_ledger=True)

    def test_optional_posting_is_reconciled(self):
        self.factory.add(self.party_id, 5_000_000)
        result = self.service.migrate("ریال", actor=ACTOR, post_to_ledger=True,
                                      confirm_posting=True)
        self.assertEqual(result["posted"], 1)
        self.assertTrue(result["reconciles"])
        trial = self.ledger.book.trial_balance()
        self.assertTrue(trial["is_balanced"])
        self.assertEqual(trial["totals"]["debit_rial"], 5_000_000)


if __name__ == "__main__":
    unittest.main()
