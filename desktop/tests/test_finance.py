# -*- coding: utf-8 -*-
"""Financial core: invoices, posting, reversal, subledger and settlement."""
from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sorting_os.core import ConflictError, ValidationError  # noqa: E402
from support import ACTOR, ServiceTestCase  # noqa: E402


class InvoiceTests(ServiceTestCase):
    def setUp(self):
        super().setUp()
        self.party_id = self.make_party("خریدار نمونه", roles=["customer"])

    def test_total_is_computed_from_lines(self):
        invoice_id = self.documents.create_invoice(
            self.party_id, kind="sales", document_date="2026-02-01",
            lines=[{"description": "پرتقال درجه یک", "weight_kg": 100,
                    "billing_weight_kg": 100, "unit_price": "10000 تومان"},
                   {"description": "پرتقال درجه دو", "weight_kg": 50,
                    "billing_weight_kg": 50, "unit_price": "8000 تومان"}],
            actor=ACTOR)
        invoice = self.documents.get_invoice(invoice_id)
        # 100kg * 100000 rial + 50kg * 80000 rial
        self.assertEqual(invoice["amount_rial"], 14_000_000)
        self.assertEqual(invoice["currency_unit"], "IRR")
        self.assertEqual(self.documents.invoice_total_rial(invoice_id), 14_000_000)

    def test_discount_is_subtracted_and_cannot_exceed_the_line(self):
        invoice_id = self.documents.create_invoice(
            self.party_id, document_date="2026-02-01",
            lines=[{"weight_kg": 10, "unit_price": 1000, "discount_rial": 500}], actor=ACTOR)
        invoice = self.documents.get_invoice(invoice_id)
        self.assertEqual(invoice["amount_rial"], 9_500)
        with self.assertRaises(ValidationError):
            self.documents.create_invoice(
                self.party_id, document_date="2026-02-01",
                lines=[{"weight_kg": 1, "unit_price": 100, "discount_rial": 500}], actor=ACTOR)

    def test_invoice_without_lines_is_rejected(self):
        with self.assertRaises(ValidationError):
            self.documents.create_invoice(self.party_id, document_date="2026-02-01",
                                          lines=[], actor=ACTOR)

    def test_cancel_and_confirm_transitions(self):
        invoice_id = self.documents.create_invoice(
            self.party_id, document_date="2026-02-01",
            lines=[{"weight_kg": 1, "unit_price": 1000}], actor=ACTOR)
        self.documents.confirm_invoice(invoice_id, actor=ACTOR)
        self.assertEqual(self.documents.get_invoice(invoice_id)["status"], "قطعی")
        other = self.documents.create_invoice(
            self.party_id, document_date="2026-02-01",
            lines=[{"weight_kg": 1, "unit_price": 1000}], actor=ACTOR)
        self.documents.cancel_invoice(other, actor=ACTOR)
        self.assertEqual(self.documents.get_invoice(other)["status"], "لغوشده")


class PostingTests(ServiceTestCase):
    def setUp(self):
        super().setUp()
        self.party_id = self.make_party("مشتری", roles=["customer"])
        self.invoice_id = self.documents.create_invoice(
            self.party_id, document_date="2026-02-01",
            lines=[{"weight_kg": 100, "unit_price": 1000}], actor=ACTOR)
        self.documents.confirm_invoice(self.invoice_id, actor=ACTOR)

    def test_posting_is_balanced_and_idempotent(self):
        first = self.ledger.post_invoice(self.invoice_id, actor=ACTOR)
        second = self.ledger.post_invoice(self.invoice_id, actor=ACTOR)
        self.assertTrue(first["created"])
        self.assertFalse(second["created"])
        self.assertEqual(first["entry_id"], second["entry_id"])
        with self.db.reader() as con:
            entries = con.execute("SELECT COUNT(*) FROM journal_entries").fetchone()[0]
            lines = con.execute(
                "SELECT COUNT(*) FROM journal_lines WHERE entry_id=?", (first["entry_id"],)
            ).fetchone()[0]
        self.assertEqual(entries, 1)
        self.assertEqual(lines, 2)

    def test_draft_invoice_cannot_be_posted(self):
        draft_id = self.documents.create_invoice(
            self.party_id, document_date="2026-02-01",
            lines=[{"weight_kg": 1, "unit_price": 10}], actor=ACTOR)
        with self.assertRaises(ConflictError):
            self.ledger.post_invoice(draft_id, actor=ACTOR)

    def test_reversal_creates_a_counter_entry(self):
        posted = self.ledger.post_invoice(self.invoice_id, actor=ACTOR)
        result = self.ledger.reverse_source("invoice", self.invoice_id, "2026-02-05",
                                            "ثبت اشتباه", actor=ACTOR)
        self.assertNotEqual(result["reversal_entry_id"], posted["entry_id"])
        trial = self.ledger.book.trial_balance()
        self.assertEqual(trial["totals"]["closing_debit_rial"], 0)
        self.assertEqual(trial["totals"]["closing_credit_rial"], 0)

    def test_party_subledger_is_rebuilt_from_the_ledger(self):
        self.ledger.post_invoice(self.invoice_id, actor=ACTOR)
        statement = self.ledger.party_subledger(self.party_id)
        # the analytical party is attached to the receivable line only
        self.assertEqual(statement["debit_rial"], 100_000)
        self.assertEqual(statement["credit_rial"], 0)
        self.assertEqual(statement["balance_rial"], 100_000)

    def test_receivable_is_visible_on_the_party_statement(self):
        self.ledger.post_invoice(self.invoice_id, actor=ACTOR)
        balances = self.reports.party_receivables()
        entry = [b for b in balances if b["party_id"] == self.party_id][0]
        self.assertEqual(entry["balance_rial"], 100_000)

    def test_expense_is_recognised_once(self):
        expense_id = self.documents.create_expense("حمل", 50_000, expense_date="2026-02-02",
                                                   actor=ACTOR)
        first = self.ledger.post_expense(expense_id, actor=ACTOR)
        second = self.ledger.post_expense(expense_id, actor=ACTOR)
        self.assertTrue(first["created"])
        self.assertFalse(second["created"])

    def test_expense_allocations_cannot_exceed_the_expense(self):
        expense_id = self.documents.create_expense("حمل", 100_000, actor=ACTOR)
        self.documents.allocate_expense(expense_id, "shipment", 1, 60_000, actor=ACTOR)
        with self.assertRaises(ValidationError):
            self.documents.allocate_expense(expense_id, "shipment", 2, 60_000, actor=ACTOR)

    def test_reconcile_postings_relinks_orphans(self):
        self.ledger.post_invoice(self.invoice_id, actor=ACTOR)
        with self.db.transaction() as con:
            con.execute("UPDATE invoices SET posted_entry_id=NULL WHERE id=?", (self.invoice_id,))
        result = self.ledger.reconcile_postings(actor=ACTOR)
        self.assertEqual(result["repaired"], 1)
        self.assertIsNotNone(self.documents.get_invoice(self.invoice_id)["posted_entry_id"])


class SettlementTests(ServiceTestCase):
    def setUp(self):
        super().setUp()
        self.party_id = self.make_party("باغدار", roles=["owner"])

    def test_net_rate_mode_computes_the_net_amount(self):
        result = self.settlements.calculate(
            self.party_id, None,
            [{"dispatched_weight_kg": 1000, "unit_price": "10000 تومان", "basis": "dispatched"}],
            calculation_mode="net_rate_input", net_rate_percent=92.5, actor=ACTOR)
        payload = result["payload"]
        self.assertEqual(payload["reference_amount_rial"], 100_000_000)
        self.assertEqual(payload["net_amount_rial"], 92_500_000)
        self.assertEqual(payload["net_settlement_rial"], 92_500_000)

    def test_net_amount_mode_derives_the_rate(self):
        result = self.settlements.calculate(
            self.party_id, None,
            [{"dispatched_weight_kg": 1000, "unit_price": 100_000, "basis": "dispatched"}],
            calculation_mode="net_amount_input", net_amount_rial=92_500_000, actor=ACTOR)
        self.assertAlmostEqual(result["payload"]["net_rate_percent"], 92.5, places=6)

    def test_commission_rule_is_versioned_and_applied(self):
        self.settlements.create_rule("COM-1", "کمیسیون ۵٪", "commission", "percent", "gross",
                                     rate_percent=5, valid_from="2026-01-01", actor=ACTOR)
        result = self.settlements.calculate(
            self.party_id, None,
            [{"dispatched_weight_kg": 1000, "unit_price": 100_000, "basis": "dispatched"}],
            calculation_mode="net_rate_input", net_rate_percent=100, actor=ACTOR)
        self.assertEqual(result["payload"]["commission_rial"], 5_000_000)
        self.assertEqual(result["payload"]["net_settlement_rial"], 95_000_000)

    def test_expired_rule_is_not_applied(self):
        self.settlements.create_rule("COM-OLD", "قدیمی", "commission", "percent", "gross",
                                     rate_percent=5, valid_from="2020-01-01",
                                     valid_to="2020-12-31", actor=ACTOR)
        result = self.settlements.calculate(
            self.party_id, None,
            [{"dispatched_weight_kg": 1000, "unit_price": 100_000, "basis": "dispatched"}],
            calculation_mode="net_rate_input", net_rate_percent=100, actor=ACTOR)
        self.assertEqual(result["payload"]["commission_rial"], 0)

    def test_adjustments_change_the_result_and_are_stored(self):
        result = self.settlements.calculate(
            self.party_id, None,
            [{"dispatched_weight_kg": 1000, "unit_price": 100_000, "basis": "dispatched"}],
            calculation_mode="net_rate_input", net_rate_percent=100,
            adjustments=[{"adjustment_type": "discount", "amount_rial": 1_000_000,
                          "reason": "کسری وزن"}], actor=ACTOR)
        self.assertEqual(result["payload"]["deductions_rial"], 1_000_000)
        self.assertEqual(result["payload"]["net_settlement_rial"], 99_000_000)
        stored = self.settlements.get(result["settlement_id"])
        self.assertEqual(len(stored["adjustments"]), 1)
        self.assertEqual(stored["formula_version"], "settlement-v1")

    def test_settlement_must_be_approved_before_posting(self):
        result = self.settlements.calculate(
            self.party_id, None,
            [{"dispatched_weight_kg": 100, "unit_price": 1000, "basis": "dispatched"}],
            calculation_mode="net_rate_input", net_rate_percent=90, actor=ACTOR)
        with self.assertRaises(ConflictError):
            self.settlements.post_settlement(result["settlement_id"], actor=ACTOR)
        self.settlements.approve(result["settlement_id"], actor=ACTOR)
        posted = self.settlements.post_settlement(result["settlement_id"], actor=ACTOR)
        self.assertTrue(posted["created"])
        self.assertTrue(posted["provisional"])

    def test_declared_weight_requires_a_declared_value(self):
        with self.assertRaises(ValidationError):
            self.settlements.calculate(
                self.party_id, None,
                [{"dispatched_weight_kg": 100, "unit_price": 1000, "basis": "declared"}],
                calculation_mode="net_rate_input", net_rate_percent=90, actor=ACTOR)


if __name__ == "__main__":
    unittest.main()
