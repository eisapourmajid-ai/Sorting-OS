# -*- coding: utf-8 -*-
"""Performance and reliability budget (Prompt 30).

The budgets below are *development machine* budgets for the head-less test
suite.  They are not a promise about the target PC (Windows 7) — a target
measurement must be taken on the real machine (see
``docs/verification/target-os-verification.md``).
"""
from __future__ import annotations

import os
import sys
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from support import ACTOR, ServiceTestCase  # noqa: E402


class PerformanceTests(ServiceTestCase):
    def setUp(self):
        super().setUp()
        self.customer = self.make_party("مشتری", roles=["customer"])

    def _post_invoices(self, count):
        started = time.perf_counter()
        for index in range(count):
            invoice_id = self.documents.create_invoice(
                self.customer, document_date="2026-02-%02d" % (index % 28 + 1),
                lines=[{"weight_kg": 100 + index, "unit_price": 1000}], actor=ACTOR)
            self.documents.confirm_invoice(invoice_id, actor=ACTOR)
            self.ledger.post_invoice(invoice_id, actor=ACTOR)
        return time.perf_counter() - started

    def test_posting_a_hundred_invoices_stays_within_budget(self):
        elapsed = self._post_invoices(100)
        sys.stderr.write("\n[perf] 100 invoice postings: %.2fs\n" % elapsed)
        self.assertLess(elapsed, 20.0, "بودجهٔ posting رد شد: %.2fs" % elapsed)
        trial = self.ledger.book.trial_balance()
        self.assertTrue(trial["is_balanced"])

    def test_financial_report_is_generated_quickly(self):
        self._post_invoices(50)
        started = time.perf_counter()
        report = self.reports.financial("2026-02-01", "2026-02-28")
        elapsed = time.perf_counter() - started
        sys.stderr.write("\n[perf] financial report: %.2fs\n" % elapsed)
        self.assertLess(elapsed, 5.0, "بودجهٔ گزارش رد شد: %.2fs" % elapsed)
        self.assertTrue(report["trial_balance"]["is_balanced"])

    def test_inventory_movements_stay_within_budget(self):
        started = time.perf_counter()
        for index in range(300):
            self.operations.post_inventory_movement("in", 10, "manual", "S%d" % index,
                                                    "loc-1", "p1", actor=ACTOR)
        elapsed = time.perf_counter() - started
        sys.stderr.write("\n[perf] 300 inventory movements: %.2fs\n" % elapsed)
        self.assertLess(elapsed, 15.0, "بودجهٔ انبار رد شد: %.2fs" % elapsed)
        self.assertEqual(self.operations.inventory_balance()["balance_kg"], 3000.0)

    def test_idempotent_replay_does_not_duplicate_anything(self):
        self._post_invoices(5)
        started = time.perf_counter()
        for _ in range(5):
            for invoice in self.documents.list_invoices():
                self.ledger.post_invoice(invoice["id"], actor=ACTOR)
        elapsed = time.perf_counter() - started
        sys.stderr.write("\n[perf] idempotent replay of 5 postings: %.2fs\n" % elapsed)
        with self.db.reader() as con:
            entries = con.execute("SELECT COUNT(*) FROM journal_entries").fetchone()[0]
        self.assertEqual(entries, 5)

    def test_database_survives_an_aborted_transaction(self):
        self._post_invoices(2)
        before = self.ledger.book.trial_balance()["totals"]["debit_rial"]
        with self.assertRaises(RuntimeError):
            with self.db.transaction() as con:
                cur = con.execute(
                    """INSERT INTO journal_entries(entry_no, entry_date, description, status,
                            actor, created_at) VALUES('JE-ERR','2026-02-01','x','posted','t','t')""")
                con.execute(
                    """INSERT INTO journal_lines(entry_id, line_no, account_code, debit_rial,
                            credit_rial) VALUES(?,1,'1010',100,0)""", (cur.lastrowid,))
                raise RuntimeError("خطای شبیه‌سازی‌شده")
        after = self.ledger.book.trial_balance()["totals"]["debit_rial"]
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
