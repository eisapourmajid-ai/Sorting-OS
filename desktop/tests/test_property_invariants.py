# -*- coding: utf-8 -*-
"""Property / invariant tests with deterministic pseudo-random data (Prompt 28).

All data is synthetic and generated from a fixed seed, so a failure is always
reproducible.  The properties checked here are the ones the product must never
violate, independent of the data set.
"""
from __future__ import annotations

import os
import random
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sorting_os.core import ValidationError, from_rial, to_jalali, to_rial  # noqa: E402
from support import ACTOR, ServiceTestCase  # noqa: E402

SEED = 20261019


class MoneyPropertyTests(unittest.TestCase):
    """Property: rial → toman → rial never loses a rial."""

    def setUp(self):
        self.random = random.Random(SEED)

    def test_rial_toman_round_trip_is_lossless(self):
        for _ in range(500):
            amount = self.random.randint(1, 10 ** 12)
            toman = from_rial(amount, "تومان")
            back = to_rial(toman, "تومان")
            self.assertEqual(back, amount)

    def test_toman_values_keep_the_decimal_part(self):
        for _ in range(200):
            amount = self.random.randint(1, 10 ** 9)
            value = from_rial(amount, "تومان")
            self.assertEqual(to_rial(value, "تومان"), amount)
            if amount % 10:
                self.assertNotEqual(value, value.to_integral_value())

    def test_sum_of_random_amounts_is_exact(self):
        for _ in range(100):
            parts = [self.random.randint(1, 10 ** 6) for _ in range(self.random.randint(2, 9))]
            self.assertEqual(sum(parts), sum(int(part) for part in parts))

    def test_invalid_amounts_are_always_rejected(self):
        for value in ("-1", "abc", "NaN", "inf", "0.5"):
            with self.assertRaises(ValidationError):
                to_rial(value, "ریال")


class CalendarPropertyTests(unittest.TestCase):
    def test_jalali_round_trip_for_random_days(self):
        rng = random.Random(SEED + 1)
        from datetime import date, timedelta
        start = date(2020, 1, 1)
        for _ in range(400):
            day = start + timedelta(days=rng.randint(0, 4000))
            jalali = to_jalali(day.isoformat())
            from sorting_os.core import from_jalali
            self.assertEqual(from_jalali(*jalali), day.isoformat())


class LedgerPropertyTests(ServiceTestCase):
    """Property: every posted entry balances and the trial balance stays equal."""

    def setUp(self):
        super().setUp()
        self.random = random.Random(SEED + 2)
        self.customer = self.make_party("مشتری تصادفی", roles=["customer"])

    def test_many_random_invoices_keep_the_trial_balance_balanced(self):
        for index in range(25):
            lines = []
            for _ in range(self.random.randint(1, 4)):
                lines.append({"weight_kg": self.random.randint(1, 500),
                              "unit_price": self.random.randint(100, 9000)})
            invoice_id = self.documents.create_invoice(
                self.customer, document_date="2026-02-%02d" % (index % 28 + 1),
                lines=lines, actor=ACTOR)
            self.documents.confirm_invoice(invoice_id, actor=ACTOR)
            self.ledger.post_invoice(invoice_id, actor=ACTOR)

        trial = self.ledger.book.trial_balance()
        self.assertTrue(trial["is_balanced"])
        self.assertEqual(trial["totals"]["debit_rial"], trial["totals"]["credit_rial"])

        # the ledger total must equal the sum of the confirmed invoices
        with self.db.reader() as con:
            total = con.execute(
                "SELECT COALESCE(SUM(amount_rial),0) FROM invoices WHERE status='قطعی'"
            ).fetchone()[0]
        self.assertEqual(trial["totals"]["debit_rial"], int(total))

    def test_reversing_all_entries_returns_the_ledger_to_zero(self):
        invoice_id = self.documents.create_invoice(
            self.customer, document_date="2026-02-01",
            lines=[{"weight_kg": 10, "unit_price": 1000}], actor=ACTOR)
        self.documents.confirm_invoice(invoice_id, actor=ACTOR)
        self.ledger.post_invoice(invoice_id, actor=ACTOR)
        self.ledger.reverse_source("invoice", invoice_id, "2026-02-02", "تست", actor=ACTOR)
        trial = self.ledger.book.trial_balance()
        # every account balance is back to zero (the reversed entry stays in the ledger)
        for account in trial["rows"]:
            self.assertEqual(int(account["closing_debit_rial"]), 0,
                             "مانده حساب پس از برگشت صفر نیست: %s" % account["account_code"])
            self.assertEqual(int(account["closing_credit_rial"]), 0,
                             "مانده حساب پس از برگشت صفر نیست: %s" % account["account_code"])
        self.assertTrue(trial["is_balanced"])

    def test_random_invoice_totals_equal_the_sum_of_their_lines(self):
        for index in range(15):
            lines = [{"weight_kg": self.random.randint(1, 100),
                      "unit_price": self.random.randint(100, 5000)}
                     for _ in range(self.random.randint(1, 5))]
            invoice_id = self.documents.create_invoice(
                self.customer, document_date="2026-03-01", lines=lines, actor=ACTOR)
            invoice = self.documents.get_invoice(invoice_id)
            self.assertEqual(invoice["amount_rial"],
                             sum(line["line_total_rial"] for line in invoice["lines"]))


class SortingPropertyTests(ServiceTestCase):
    def test_random_sorting_operations_always_balance(self):
        rng = random.Random(SEED + 3)
        owner = self.make_party("باغدار")
        for index in range(10):
            total = rng.randint(100, 1000)
            output = rng.randint(1, total)
            waste = total - output
            shipment_id = self.operations.create_shipment(owner, "پرتقال", total, actor=ACTOR)
            operation_id = self.operations.create_sorting_operation(
                shipment_id, total,
                [{"line_type": "output", "weight_kg": output},
                 {"line_type": "waste", "weight_kg": waste}],
                waste_weight_kg=waste, actor=ACTOR)
            detail = self.operations.sorting_operation_detail(operation_id)
            self.assertAlmostEqual(
                sum(line["weight_kg"] for line in detail["lines"]),
                detail["input_weight_kg"], places=6)


if __name__ == "__main__":
    unittest.main()
