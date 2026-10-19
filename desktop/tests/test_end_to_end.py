# -*- coding: utf-8 -*-
"""End-to-end acceptance scenarios (Prompt 29).

The scenarios mirror ``docs/financial/ACCOUNTING_ACCEPTANCE_SCENARIOS_FA.md``
(scenarios A–H) and use synthetic data only.  They exercise the complete
chain: operational documents → posting → reports, and they verify that no
legacy row reaches the financial statements.
"""
from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sorting_os.core import from_rial, to_rial  # noqa: E402
from support import ACTOR, ServiceTestCase  # noqa: E402


class ScenarioA_UnitConversionTests(unittest.TestCase):
    def test_thousand_toman_becomes_twelve_thousand_three_hundred_forty_rial(self):
        self.assertEqual(to_rial("1,234 تومان", "تومان"), 12_340)

    def test_thousand_rial_stays_thousand_rial(self):
        self.assertEqual(to_rial("1,234 ریال", "ریال"), 1_234)

    def test_ten_and_a_half_toman_becomes_one_hundred_five_rial(self):
        self.assertEqual(to_rial("10.5 تومان", "تومان"), 105)

    def test_one_hundred_five_rial_displays_as_ten_and_a_half_toman(self):
        self.assertEqual(from_rial(105, "تومان"), 10.5)

    def test_fraction_of_a_rial_is_rejected(self):
        from sorting_os.core import ValidationError
        # 0.5 تومان = 5 ریال (مجاز) ولی 0.5 ریال به کسر ریال منجر می‌شود (رد)
        self.assertEqual(to_rial("0.5 تومان", "تومان"), 5)
        with self.assertRaises(ValidationError):
            to_rial("0.5 ریال", "ریال")


class ScenarioB_OpeningEntryTests(ServiceTestCase):
    def test_opening_entry_balances_and_appears_in_the_balance_sheet(self):
        self.ledger.book.post_entry(
            "2026-01-01", "سند افتتاحیه",
            [{"account_code": "1010", "debit_rial": 1_000_000, "credit_rial": 0},
             {"account_code": "3000", "debit_rial": 0, "credit_rial": 1_000_000}],
            actor=ACTOR)
        trial = self.ledger.book.trial_balance()
        self.assertTrue(trial["is_balanced"])
        sheet = self.ledger.book.balance_sheet("2026-01-31")
        self.assertEqual(int(sheet["assets_total_rial"]), 1_000_000)
        self.assertEqual(int(sheet["equity_total_rial"]), 1_000_000)
        self.assertEqual(int(sheet["difference_rial"]), 0)
        self.assertTrue(sheet["is_balanced"])


class ScenarioC_IncomeStatementTests(ServiceTestCase):
    def test_revenue_minus_expense_equals_net_profit(self):
        # the opening entry of scenario B is assumed to exist in the same book
        self.ledger.book.post_entry(
            "2026-01-01", "سند افتتاحیه",
            [{"account_code": "1010", "debit_rial": 1_000_000, "credit_rial": 0},
             {"account_code": "3000", "debit_rial": 0, "credit_rial": 1_000_000}], actor=ACTOR)
        self.ledger.book.post_entry(
            "2026-01-05", "درآمد خدمات",
            [{"account_code": "1010", "debit_rial": 500_000, "credit_rial": 0},
             {"account_code": "4000", "debit_rial": 0, "credit_rial": 500_000}], actor=ACTOR)
        self.ledger.book.post_entry(
            "2026-01-06", "هزینه عملیاتی",
            [{"account_code": "6000", "debit_rial": 100_000, "credit_rial": 0},
             {"account_code": "1010", "debit_rial": 0, "credit_rial": 100_000}], actor=ACTOR)
        income = self.ledger.book.income_statement("2026-01-01", "2026-01-31")
        self.assertEqual(int(income["revenue_total_rial"]), 500_000)
        self.assertEqual(int(income["expense_total_rial"]), 100_000)
        self.assertEqual(int(income["net_profit_rial"]), 400_000)
        sheet = self.ledger.book.balance_sheet("2026-01-31")
        self.assertEqual(int(sheet["assets_total_rial"]), 1_400_000)


class ScenarioD_UnbalancedEntryTests(ServiceTestCase):
    def test_unbalanced_entry_is_rejected_and_leaves_no_rows(self):
        with self.assertRaises(ValueError):
            self.ledger.book.post_entry(
                "2026-01-07", "سند نامتوازن",
                [{"account_code": "1010", "debit_rial": 100_000, "credit_rial": 0},
                 {"account_code": "4000", "debit_rial": 0, "credit_rial": 99_999}], actor=ACTOR)
        with self.db.reader() as con:
            entries = con.execute("SELECT COUNT(*) FROM journal_entries").fetchone()[0]
            lines = con.execute("SELECT COUNT(*) FROM journal_lines").fetchone()[0]
        self.assertEqual(entries, 0)
        self.assertEqual(lines, 0)


class ScenarioE_DuplicateSourceTests(ServiceTestCase):
    def test_posting_the_same_source_twice_is_rejected(self):
        party_id = self.make_party("مشتری", roles=["customer"])
        invoice_id = self.documents.create_invoice(
            party_id, document_date="2026-01-10",
            lines=[{"weight_kg": 10, "unit_price": 1000}], actor=ACTOR)
        self.documents.confirm_invoice(invoice_id, actor=ACTOR)
        first = self.ledger.post_invoice(invoice_id, actor=ACTOR)
        second = self.ledger.post_invoice(invoice_id, actor=ACTOR)
        self.assertTrue(first["created"])
        self.assertFalse(second["created"])
        with self.db.reader() as con:
            count = con.execute("SELECT COUNT(*) FROM journal_entries").fetchone()[0]
        self.assertEqual(count, 1)


class ScenarioF_ReversalTests(ServiceTestCase):
    def test_reversal_keeps_the_original_and_cancels_the_effect(self):
        party_id = self.make_party("مشتری", roles=["customer"])
        invoice_id = self.documents.create_invoice(
            party_id, document_date="2026-01-10",
            lines=[{"weight_kg": 10, "unit_price": 1000}], actor=ACTOR)
        self.documents.confirm_invoice(invoice_id, actor=ACTOR)
        posting = self.ledger.post_invoice(invoice_id, actor=ACTOR)
        self.ledger.reverse_source("invoice", invoice_id, "2026-01-11", "اصلاح اشتباه",
                                   actor=ACTOR)
        with self.db.reader() as con:
            entries = con.execute(
                "SELECT id, reverses_entry_id FROM journal_entries ORDER BY id").fetchall()
        self.assertEqual(len(entries), 2)
        self.assertIsNone(entries[0]["reverses_entry_id"])
        self.assertEqual(entries[1]["reverses_entry_id"], posting["entry_id"])
        trial = self.ledger.book.trial_balance()
        for row in trial["rows"]:
            self.assertEqual(int(row["closing_debit_rial"]), 0)
            self.assertEqual(int(row["closing_credit_rial"]), 0)


class ScenarioG_CashFlowTests(ServiceTestCase):
    def test_cash_reconciliation(self):
        self.ledger.book.post_entry(
            "2026-01-01", "تأمین مالی",
            [{"account_code": "1010", "debit_rial": 1_000_000, "credit_rial": 0},
             {"account_code": "3000", "debit_rial": 0, "credit_rial": 1_000_000}], actor=ACTOR)
        self.ledger.book.post_entry(
            "2026-01-02", "هزینه نقدی",
            [{"account_code": "6000", "debit_rial": 200_000, "credit_rial": 0},
             {"account_code": "1010", "debit_rial": 0, "credit_rial": 200_000}], actor=ACTOR)
        cash = self.ledger.book.cash_flow_statement("2026-01-01", "2026-01-31")
        self.assertEqual(int(cash["opening_cash_rial"]), 0)
        self.assertEqual(int(cash["net_change_rial"]), 800_000)
        self.assertEqual(int(cash["closing_cash_rial"]), 800_000)
        self.assertTrue(cash.get("reconciles", True))


class ScenarioH_NoImplicitMigrationTests(ServiceTestCase):
    def test_legacy_invoice_never_reaches_the_ledger(self):
        from database import Database

        legacy = Database(self.db_path)
        party_id = legacy.save_party({"display_name": "طرف قدیمی"}, actor=ACTOR)
        legacy.create_invoice(party_id, "فروش", "2026-01-02", 5_000_000, "legacy",
                              status="قطعی", actor=ACTOR)
        trial = self.ledger.book.trial_balance()
        self.assertEqual(trial["totals"]["debit_rial"], 0)
        income = self.ledger.book.income_statement("2026-01-01", "2026-01-31")
        self.assertEqual(int(income["revenue_total_rial"]), 0)
        # the legacy row is still visible as an operational document
        with self.db.reader() as con:
            rows = con.execute("SELECT amount_rial FROM invoices").fetchall()
        self.assertEqual(len(rows), 1)
        self.assertIsNone(rows[0]["amount_rial"])


class FullFlowTests(ServiceTestCase):
    """A complete operational day: intake → sorting → invoice → payment → report."""

    def test_complete_day(self):
        owner = self.make_party("باغدار", roles=["owner"])
        customer = self.make_party("مشتری", roles=["customer"])

        shipment_id = self.operations.create_shipment(
            owner, "پرتقال", 1000, received_at="2026-02-01", actor=ACTOR)
        self.operations.create_weighing("in", 1050, 50, shipment_ids=[shipment_id],
                                        weighed_at="2026-02-01", actor=ACTOR)
        operation_id = self.operations.create_sorting_operation(
            shipment_id, 1000,
            [{"line_type": "output", "weight_kg": 900, "grade_id": None},
             {"line_type": "waste", "weight_kg": 100}],
            waste_weight_kg=100, measured_at="2026-02-02", actor=ACTOR)
        self.operations.confirm_sorting_operation(operation_id, actor=ACTOR)

        invoice_id = self.documents.create_invoice(
            customer, document_date="2026-02-03",
            lines=[{"weight_kg": 900, "unit_price": 1000}], actor=ACTOR)
        self.documents.confirm_invoice(invoice_id, actor=ACTOR)
        posting = self.ledger.post_invoice(invoice_id, actor=ACTOR)
        self.assertTrue(posting["created"])

        payment_id = self.banking.create_payment(
            customer, "in", 900_000, payment_date="2026-02-04", actor=ACTOR)
        self.ledger.post_payment(payment_id, actor=ACTOR)

        trial = self.ledger.book.trial_balance()
        self.assertTrue(trial["is_balanced"])
        dashboard = self.reports.dashboard(as_of="2026-02-28")
        self.assertEqual(dashboard["commercial"]["confirmed_invoices"], 1)
        self.assertEqual(dashboard["financial"]["receivables_rial"], 0)
        ageing = self.reports.receivables_aging(as_of="2026-02-28")
        self.assertEqual(ageing["total_outstanding_rial"], 0)


if __name__ == "__main__":
    unittest.main()
