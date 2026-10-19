# -*- coding: utf-8 -*-
"""تخصیص درصد صافی: پیش‌فرض، حساب طرف و فاکتور (DEC-017).

The settlement percentage is assigned per invoice, per settlement counterparty
(supplier account) and falls back to an editable default.  Rates are versioned:
editing a rate never rewrites a settlement that was already calculated.
"""
from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sorting_os.core import ValidationError  # noqa: E402
from support import ACTOR, ServiceTestCase  # noqa: E402


class RateAssignmentTests(ServiceTestCase):
    def setUp(self):
        super().setUp()
        self.party_id = self.make_party("باغدار", roles=["owner"])
        self.customer_id = self.make_party("مشتری", roles=["customer"])
        self.invoice_id = self.documents.create_invoice(
            self.customer_id, document_date="2026-02-01",
            lines=[{"weight_kg": 100, "unit_price": 1000}], actor=ACTOR)

    def lines(self, weight=1000, price=1000):
        return [{"line_type": "output", "dispatched_weight_kg": weight, "unit_price": price}]

    def calculate(self, **kwargs):
        params = {"party_id": self.party_id, "shipment_id": None,
                  "lines": self.lines(), "calculation_mode": "net_rate_input"}
        params.update(kwargs)
        return self.settlements.calculate(**params)

    # -- assignment --------------------------------------------------------- #
    def test_default_rate_can_be_set_and_read(self):
        result = self.settlements.set_default_rate(90, valid_from="2026-01-01", actor=ACTOR)
        self.assertEqual(result["rate_percent"], 90.0)
        resolved = self.settlements.resolve_rate(party_id=self.party_id,
                                                on_date="2026-02-01")
        self.assertEqual(resolved["rate_percent"], 90.0)
        self.assertEqual(resolved["source"], "default")

    def test_party_rate_overrides_the_default(self):
        self.settlements.set_default_rate(90, valid_from="2026-01-01", actor=ACTOR)
        self.settlements.set_party_rate(self.party_id, 85, valid_from="2026-01-01", actor=ACTOR)
        resolved = self.settlements.resolve_rate(party_id=self.party_id, on_date="2026-02-01")
        self.assertEqual(resolved["rate_percent"], 85.0)
        self.assertEqual(resolved["source"], "party")

    def test_invoice_rate_overrides_the_party_rate(self):
        self.settlements.set_default_rate(90, valid_from="2026-01-01", actor=ACTOR)
        self.settlements.set_party_rate(self.party_id, 85, valid_from="2026-01-01", actor=ACTOR)
        self.settlements.set_invoice_rate(self.invoice_id, 80, valid_from="2026-01-01",
                                          actor=ACTOR)
        resolved = self.settlements.resolve_rate(party_id=self.party_id,
                                                invoice_id=self.invoice_id,
                                                on_date="2026-02-01")
        self.assertEqual(resolved["rate_percent"], 80.0)
        self.assertEqual(resolved["source"], "invoice")

    def test_rates_are_validated(self):
        for value in (-1, 101, "abc", None):
            with self.assertRaises(ValidationError):
                self.settlements.set_default_rate(value, actor=ACTOR)

    def test_rate_for_an_unknown_party_is_rejected(self):
        with self.assertRaises(ValidationError):
            self.settlements.set_party_rate(999999, 90, actor=ACTOR)

    def test_rate_for_an_unknown_invoice_is_rejected(self):
        with self.assertRaises(ValidationError):
            self.settlements.set_invoice_rate(999999, 90, actor=ACTOR)

    # -- calculation -------------------------------------------------------- #
    def test_calculation_without_any_rate_is_refused(self):
        with self.assertRaises(ValidationError):
            self.calculate()

    def test_calculation_uses_the_assigned_rate(self):
        self.settlements.set_default_rate(90, valid_from="2026-01-01", actor=ACTOR)
        result = self.calculate()
        self.assertEqual(result["payload"]["net_rate_percent"], 90.0)
        self.assertEqual(result["payload"]["rate_source"], "default")
        # 1,000 kg × 1,000 rial = 1,000,000 rial gross → 90% = 900,000
        self.assertEqual(result["payload"]["net_amount_rial"], 900_000)

    def test_invoice_rate_is_used_for_its_own_settlement_only(self):
        self.settlements.set_default_rate(90, valid_from="2026-01-01", actor=ACTOR)
        self.settlements.set_invoice_rate(self.invoice_id, 80, valid_from="2026-01-01",
                                          actor=ACTOR)
        with_invoice = self.calculate(invoice_id=self.invoice_id)
        self.assertEqual(with_invoice["payload"]["net_rate_percent"], 80.0)
        self.assertEqual(with_invoice["payload"]["rate_source"], "invoice")
        without_invoice = self.calculate()
        self.assertEqual(without_invoice["payload"]["net_rate_percent"], 90.0)
        self.assertEqual(without_invoice["payload"]["rate_source"], "default")

    def test_manual_rate_wins_over_the_assigned_rate(self):
        self.settlements.set_default_rate(90, valid_from="2026-01-01", actor=ACTOR)
        result = self.calculate(net_rate_percent=75)
        self.assertEqual(result["payload"]["net_rate_percent"], 75.0)
        self.assertEqual(result["payload"]["rate_source"], "manual")

    def test_settlement_stores_the_rate_source(self):
        self.settlements.set_party_rate(self.party_id, 85, valid_from="2026-01-01", actor=ACTOR)
        result = self.calculate()
        stored = self.settlements.get(result["settlement_id"])
        self.assertEqual(stored["rate_source"], "party")
        self.assertIsNotNone(stored["rate_id"])
        self.assertEqual(stored["payload"]["rate_source_label"], "نرخ حساب طرف")

    def test_amount_mode_keeps_the_assigned_rate_visible(self):
        self.settlements.set_default_rate(90, valid_from="2026-01-01", actor=ACTOR)
        result = self.calculate(calculation_mode="net_amount_input",
                                 net_amount_rial=950_000)
        self.assertEqual(result["payload"]["rate_source"], "amount_input")
        self.assertEqual(result["payload"]["assigned_rate_percent"], 90.0)
        self.assertEqual(result["payload"]["net_amount_rial"], 950_000)

    # -- editing ------------------------------------------------------------ #
    def test_editing_a_rate_does_not_change_earlier_settlements(self):
        self.settlements.set_party_rate(self.party_id, 85, valid_from="2026-01-01", actor=ACTOR)
        first = self.calculate()
        self.settlements.set_party_rate(self.party_id, 70, valid_from="2026-02-10", actor=ACTOR)
        second = self.calculate(settlement_date="2026-02-10")

        self.assertEqual(self.settlements.get(first["settlement_id"])["net_rate_percent"], 85.0)
        self.assertEqual(self.settlements.get(second["settlement_id"])["net_rate_percent"], 70.0)
        history = self.settlements.list_rates(scope="party", party_id=self.party_id)
        self.assertEqual(len(history), 2)
        old = [r for r in history if r["id"] == self.settlements.get(first["settlement_id"])["rate_id"]][0]
        self.assertEqual(old["is_active"], 0)
        self.assertEqual(old["valid_to"], "2026-02-09")

    def test_editing_twice_on_the_same_day_is_allowed(self):
        self.settlements.set_party_rate(self.party_id, 85, valid_from="2026-01-01", actor=ACTOR)
        self.settlements.set_party_rate(self.party_id, 70, valid_from="2026-01-01", actor=ACTOR)
        history = self.settlements.list_rates(scope="party", party_id=self.party_id)
        self.assertEqual(len(history), 2)
        resolved = self.settlements.resolve_rate(party_id=self.party_id, on_date="2026-01-01")
        self.assertEqual(resolved["rate_percent"], 70.0)
        self.assertEqual(resolved["source"], "party")

    def test_database_refuses_two_active_versions_of_the_same_target(self):
        import sqlite3

        self.settlements.set_party_rate(self.party_id, 85, valid_from="2026-01-01", actor=ACTOR)
        with self.assertRaises(sqlite3.IntegrityError):
            with self.db.transaction() as con:
                con.execute(
                    """INSERT INTO settlement_rates(scope, party_id, invoice_id, rate_percent,
                            valid_from, valid_to, is_active, created_at)
                       VALUES('party', ?, NULL, 50, '2026-01-01', NULL, 1, '2026-01-01')""",
                    (self.party_id,))

    def test_a_closed_rate_does_not_apply_after_its_end_date(self):
        self.settlements.set_party_rate(self.party_id, 85, valid_from="2026-01-01",
                                       valid_to="2026-01-31", actor=ACTOR)
        resolved = self.settlements.resolve_rate(party_id=self.party_id, on_date="2026-02-05")
        self.assertIsNone(resolved["rate_percent"])

    def test_deactivating_a_rate_falls_back_to_the_default(self):
        self.settlements.set_default_rate(90, valid_from="2026-01-01", actor=ACTOR)
        party_rate = self.settlements.set_party_rate(self.party_id, 85, valid_from="2026-01-01",
                                                    actor=ACTOR)
        self.settlements.deactivate_rate(party_rate["rate_id"], actor=ACTOR)
        resolved = self.settlements.resolve_rate(party_id=self.party_id, on_date="2026-02-01")
        self.assertEqual(resolved["rate_percent"], 90.0)
        self.assertEqual(resolved["source"], "default")

    # -- printing ----------------------------------------------------------- #
    def test_printed_settlement_shows_the_rate_and_its_source(self):
        self.settlements.set_party_rate(self.party_id, 85, valid_from="2026-01-01", actor=ACTOR)
        result = self.calculate()
        payload = self.settlements.print_payload(result["settlement_id"], unit="تومان")
        self.assertIn("85%", payload["rate_display"])
        self.assertNotIn("85.0", payload["rate_display"])
        self.assertIn("نرخ حساب طرف", payload["rate_display"])
        preview = self.printing.render("settlement", payload, unit="تومان")
        self.assertIn("85", preview["text"])
        self.assertIn("تومان", preview["text"])


if __name__ == "__main__":
    unittest.main()
