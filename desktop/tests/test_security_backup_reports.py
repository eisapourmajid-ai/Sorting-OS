# -*- coding: utf-8 -*-
"""Security, backup/restore, reporting and domain invariants."""
from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sorting_os.core import ConflictError, PermissionDenied, ValidationError  # noqa: E402
from support import ACTOR, ServiceTestCase  # noqa: E402


class AuthTests(ServiceTestCase):
    def test_user_creation_and_authentication(self):
        user_id = self.auth.create_user("operator", "secret123", role_code="operator",
                                         actor=ACTOR)
        actor = self.auth.authenticate("operator", "secret123")
        self.assertIsNotNone(actor)
        self.assertIn("operations.write", actor.permissions)
        self.assertIsNone(self.auth.authenticate("operator", "wrong-password"))

    def test_weak_password_is_rejected(self):
        with self.assertRaises(ValidationError):
            self.auth.create_user("weak", "123", actor=ACTOR)

    def test_duplicate_username_is_rejected(self):
        self.auth.create_user("dup", "secret123", actor=ACTOR)
        with self.assertRaises(ConflictError):
            self.auth.create_user("dup", "secret123", actor=ACTOR)

    def test_permissions_are_enforced(self):
        self.auth.create_user("viewer", "secret123", role_code="viewer", actor=ACTOR)
        actor = self.auth.authenticate("viewer", "secret123")
        self.assertTrue(actor.can("report.view"))
        self.assertFalse(actor.can("ledger.post"))
        with self.assertRaises(PermissionDenied):
            actor.require("ledger.post")

    def test_audit_chain_detects_tampering(self):
        self.auth.append_audit(ACTOR, "create", "party", 1, "row one")
        self.auth.append_audit(ACTOR, "update", "party", 1, "row two")
        report = self.auth.verify_audit_chain()
        self.assertTrue(report["valid"])
        with self.db.transaction() as con:
            con.execute("UPDATE audit_log SET details='دستکاری' WHERE id=1")
        report = self.auth.verify_audit_chain()
        self.assertFalse(report["valid"])
        self.assertEqual(report["broken_at"], 1)

    def test_existing_audit_rows_can_be_chained(self):
        self.db.audit(ACTOR, "create", "party", 1, "قدیمی")
        result = self.auth.chain_existing_audit(actor=ACTOR)
        self.assertGreaterEqual(result["chained"], 1)
        self.assertTrue(self.auth.verify_audit_chain()["valid"])


class BackupTests(ServiceTestCase):
    def test_backup_is_created_and_verified(self):
        party_id = self.make_party()
        target = os.path.join(self.db_path + "-backups")
        report = self.backups.create(target, actor=ACTOR)
        self.assertTrue(os.path.isfile(report["path"]))
        verification = self.backups.verify(report["path"])
        self.assertTrue(verification["is_valid"])
        self.assertEqual(verification["counts"]["parties"], 1)

    def test_restore_brings_back_the_data(self):
        party_id = self.make_party("قبل از بازیابی")
        target = os.path.join(self.db_path + "-backups")
        report = self.backups.create(target, actor=ACTOR)
        self.parties.create("بعد از بکاپ", actor=ACTOR)
        self.assertEqual(len(self.parties.list_all()), 2)
        self.backups.restore(report["path"], actor=ACTOR)
        self.assertEqual(len(self.parties.list_all()), 1)
        self.assertEqual(self.parties.list_all()[0]["display_name"], "قبل از بازیابی")

    def test_corrupted_backup_is_rejected(self):
        target = os.path.join(self.db_path + "-backups")
        report = self.backups.create(target, actor=ACTOR)
        with open(report["path"], "r+b") as handle:
            handle.seek(0)
            handle.write(b"not a database")
        with self.assertRaises(ConflictError):
            self.backups.restore(report["path"], actor=ACTOR)


class ReportingTests(ServiceTestCase):
    def setUp(self):
        super().setUp()
        self.party_id = self.make_party("مشتری", roles=["customer"])
        self.invoice_id = self.documents.create_invoice(
            self.party_id, document_date="2026-02-01",
            lines=[{"weight_kg": 100, "unit_price": 1000}], actor=ACTOR)
        self.documents.confirm_invoice(self.invoice_id, actor=ACTOR)
        self.ledger.post_invoice(self.invoice_id, actor=ACTOR)

    def test_dashboard_is_built_from_real_data(self):
        dashboard = self.reports.dashboard(as_of="2026-02-01")
        self.assertEqual(dashboard["commercial"]["confirmed_invoices"], 1)
        self.assertEqual(dashboard["commercial"]["confirmed_amount_rial"], 100_000)
        self.assertEqual(dashboard["financial"]["receivables_rial"], 100_000)
        self.assertIn("تومان", dashboard["financial"]["receivables_display"])

    def test_financial_reports_come_from_the_journal(self):
        report = self.reports.financial("2026-02-01", "2026-02-28")
        self.assertTrue(report["trial_balance"]["is_balanced"])
        self.assertTrue(report["balance_sheet"]["is_balanced"])
        self.assertEqual(report["income_statement"]["revenue_total_rial"], 100_000)
        self.assertEqual(report["cash_flow"]["reconciles"], True)
        self.assertTrue(report["notes"])

    def test_operations_report_uses_real_movements(self):
        owner = self.make_party("باغدار")
        shipment_id = self.operations.create_shipment(owner, "پرتقال", 1000,
                                                      received_at="2026-02-02", actor=ACTOR)
        operation_id = self.operations.create_sorting_operation(
            shipment_id, 1000, [{"line_type": "output", "weight_kg": 900},
                                {"line_type": "waste", "weight_kg": 100}],
            waste_weight_kg=100, measured_at="2026-02-03", actor=ACTOR)
        self.operations.confirm_sorting_operation(operation_id, actor=ACTOR)
        report = self.reports.operations_report("2026-02-01", "2026-02-28")
        self.assertEqual(report["received"]["weight_kg"], 1000.0)
        self.assertEqual(report["sorting"]["input_kg"], 1000.0)
        self.assertAlmostEqual(report["sorting"]["output_ratio"], 0.9, places=3)

    def test_receivables_ageing_buckets_invoices(self):
        second = self.documents.create_invoice(
            self.party_id, document_date="2026-01-01", due_date="2026-01-10",
            lines=[{"weight_kg": 1, "unit_price": 5000}], actor=ACTOR)
        self.documents.confirm_invoice(second, actor=ACTOR)
        ageing = self.reports.receivables_aging(as_of="2026-03-01")
        self.assertTrue(ageing["items"])
        # due 2026-01-10 -> 50 days late on 2026-03-01
        self.assertEqual(ageing["buckets"]["31_60"], 5_000)
        late = self.reports.receivables_aging(as_of="2026-06-01")
        self.assertGreater(late["buckets"]["over_90"], 0)


class InvariantTests(ServiceTestCase):
    """Domain invariants that must hold for every dataset (Prompt 28/30)."""

    def test_every_journal_entry_is_balanced(self):
        party_id = self.make_party()
        invoice_id = self.documents.create_invoice(
            party_id, document_date="2026-02-01",
            lines=[{"weight_kg": 10, "unit_price": 1000}], actor=ACTOR)
        self.documents.confirm_invoice(invoice_id, actor=ACTOR)
        self.ledger.post_invoice(invoice_id, actor=ACTOR)
        with self.db.reader() as con:
            rows = con.execute(
                """SELECT entry_id, SUM(debit_rial) AS d, SUM(credit_rial) AS c
                   FROM journal_lines GROUP BY entry_id""").fetchall()
        self.assertTrue(rows)
        for row in rows:
            self.assertEqual(row["d"], row["c"], "سند نامتوازن: %s" % row["entry_id"])

    def test_totals_of_invoices_match_their_lines(self):
        party_id = self.make_party()
        invoice_id = self.documents.create_invoice(
            party_id, document_date="2026-02-01",
            lines=[{"weight_kg": 10, "unit_price": 1000},
                   {"weight_kg": 5, "unit_price": 2000}], actor=ACTOR)
        invoice = self.documents.get_invoice(invoice_id)
        self.assertEqual(invoice["amount_rial"],
                         sum(line["line_total_rial"] for line in invoice["lines"]))

    def test_inventory_balance_equals_the_sum_of_movements(self):
        for index in range(5):
            self.operations.post_inventory_movement("in", 100 + index, "src", "S%d" % index,
                                                    "l1", "p", actor=ACTOR)
        for index in range(2):
            self.operations.post_inventory_movement("out", 30, "src", "O%d" % index,
                                                    "l1", "p", actor=ACTOR)
        balance = self.operations.inventory_balance()
        self.assertEqual(balance["balance_kg"], sum(range(100, 105)) - 60)

    def test_expense_allocations_never_exceed_the_expense(self):
        expense_id = self.documents.create_expense("حمل", 100_000, actor=ACTOR)
        self.documents.allocate_expense(expense_id, "shipment", 1, 40_000, actor=ACTOR)
        self.documents.allocate_expense(expense_id, "shipment", 2, 60_000, actor=ACTOR)
        with self.assertRaises(ValidationError):
            self.documents.allocate_expense(expense_id, "shipment", 3, 1, actor=ACTOR)
        allocated = sum(a["amount_rial"] for a in self.documents.expense_allocations(expense_id))
        self.assertEqual(allocated, 100_000)

    def test_sorting_mass_balance_is_enforced_for_every_operation(self):
        owner = self.make_party()
        shipment_id = self.operations.create_shipment(owner, "پرتقال", 500, actor=ACTOR)
        operation_id = self.operations.create_sorting_operation(
            shipment_id, 500, [{"line_type": "output", "weight_kg": 450},
                               {"line_type": "waste", "weight_kg": 50}],
            waste_weight_kg=50, actor=ACTOR)
        detail = self.operations.sorting_operation_detail(operation_id)
        total = sum(line["weight_kg"] for line in detail["lines"])
        self.assertAlmostEqual(total, detail["input_weight_kg"], places=3)

    def test_no_legacy_row_reaches_the_financial_reports(self):
        from database import Database

        legacy = Database(self.db_path)
        party_id = legacy.save_party({"display_name": "قدیمی"}, actor=ACTOR)
        legacy.create_invoice(party_id, "فروش", "2026-01-02", 5_000_000, "legacy",
                              status="قطعی", actor=ACTOR)
        trial = self.ledger.book.trial_balance()
        self.assertEqual(trial["totals"]["debit_rial"], 0)


class PeriodTests(ServiceTestCase):
    def test_closing_a_period_posts_a_balanced_entry(self):
        party_id = self.make_party()
        invoice_id = self.documents.create_invoice(
            party_id, document_date="2026-02-01",
            lines=[{"weight_kg": 10, "unit_price": 1000}], actor=ACTOR)
        self.documents.confirm_invoice(invoice_id, actor=ACTOR)
        self.ledger.post_invoice(invoice_id, actor=ACTOR)
        period_id = self.periods.create_period("1405-01", "نیمه اول ۱۴۰۵", "2026-02-01",
                                               "2026-02-28", actor=ACTOR)
        result = self.periods.close(period_id, actor=ACTOR)
        self.assertTrue(result["closed"])
        trial = self.ledger.book.trial_balance()
        self.assertTrue(trial["is_balanced"])
        self.assertEqual(trial["totals"]["closing_debit_rial"], 10_000)

    def test_closed_period_rejects_new_documents(self):
        period_id = self.periods.create_period("1405-01", "دوره", "2026-02-01", "2026-02-28",
                                               actor=ACTOR)
        self.periods.close(period_id, actor=ACTOR)
        with self.assertRaises(ConflictError):
            self.periods.assert_open("2026-02-15")

    def test_backup_is_created_before_closing(self):
        period_id = self.periods.create_period("1405-01", "دوره", "2026-02-01", "2026-02-28",
                                               actor=ACTOR)
        target = os.path.join(self.db_path + "-backups")
        self.periods.close(period_id, actor=ACTOR, backup_dir=target)
        self.assertTrue(os.path.isdir(target))
        self.assertTrue(os.listdir(target))


if __name__ == "__main__":
    unittest.main()
