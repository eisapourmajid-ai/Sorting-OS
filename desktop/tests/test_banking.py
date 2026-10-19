# -*- coding: utf-8 -*-
"""Banking: statement import, reconciliation, cheques and payments."""
from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sorting_os.core import ConflictError, ValidationError  # noqa: E402
from support import ACTOR, ServiceTestCase  # noqa: E402


class StatementImportTests(ServiceTestCase):
    def setUp(self):
        super().setUp()
        self.bank_id = self.banking.create_bank_account("BANK-1", "بانک ملت", "بانک ملت",
                                                        "****1234", actor=ACTOR)
        self.rows = [
            {"date": "2026-02-01", "description": "واریز مشتری", "amount": "12500000",
             "direction": "in", "reference": "INV-1"},
            {"date": "2026-02-02", "description": "پرداخت کارگری", "amount": "5000000",
             "direction": "out"},
        ]

    def test_unit_must_be_explicit(self):
        with self.assertRaises(ValidationError):
            self.banking.import_statement(self.bank_id, self.rows, unit="auto", actor=ACTOR)

    def test_import_creates_a_preview_with_row_errors(self):
        rows = self.rows + [{"date": "not-a-date", "amount": "10", "direction": "in"}]
        result = self.banking.import_statement(self.bank_id, rows, unit="ریال", actor=ACTOR)
        self.assertFalse(result["duplicate"])
        self.assertEqual(result["status"], "preview")
        self.assertEqual(len(result["rows"]), 2)
        self.assertEqual(len(result["errors"]), 1)
        self.assertEqual(result["errors"][0]["row"], 3)

    def test_same_file_twice_does_not_duplicate(self):
        first = self.banking.import_statement(self.bank_id, self.rows, unit="ریال", actor=ACTOR)
        second = self.banking.import_statement(self.bank_id, self.rows, unit="ریال", actor=ACTOR)
        self.assertFalse(first["duplicate"])
        self.assertTrue(second["duplicate"])
        self.assertEqual(second["statement_id"], first["statement_id"])
        with self.db.reader() as con:
            count = con.execute("SELECT COUNT(*) FROM bank_transactions").fetchone()[0]
        self.assertEqual(count, 2)

    def test_toman_input_is_converted_to_rial(self):
        result = self.banking.import_statement(
            self.bank_id, [{"date": "2026-02-01", "amount": "1250", "direction": "in"}],
            unit="تومان", actor=ACTOR)
        self.assertEqual(result["rows"][0]["amount_rial"], 12_500)

    def test_commit_marks_the_statement(self):
        result = self.banking.import_statement(self.bank_id, self.rows, unit="ریال", actor=ACTOR)
        self.banking.commit_statement(result["statement_id"], actor=ACTOR)
        statements = self.banking.list_statements()
        self.assertEqual(statements[0]["status"], "committed")


class ReconciliationTests(ServiceTestCase):
    def setUp(self):
        super().setUp()
        self.party_id = self.make_party("مشتری", roles=["customer"])
        self.bank_id = self.banking.create_bank_account("BANK-1", "بانک", actor=ACTOR)

    def test_suggestions_are_created_and_accepted_by_a_human(self):
        payment_id = self.banking.create_payment(
            self.party_id, "in", 12_500_000, payment_date="2026-02-01", actor=ACTOR)
        result = self.banking.import_statement(
            self.bank_id, [{"date": "2026-02-01", "amount": "12500000", "direction": "in"}],
            unit="ریال", actor=ACTOR)
        transaction = self.banking.list_transactions(result["statement_id"])[0]
        suggestions = self.banking.suggest_matches(transaction["id"])
        self.assertTrue(suggestions)
        self.assertEqual(suggestions[0]["target_id"], payment_id)
        with self.db.reader() as con:
            match = con.execute("SELECT * FROM bank_matches WHERE transaction_id=?",
                                (transaction["id"],)).fetchone()
        self.assertEqual(match["status"], "suggested")
        self.banking.accept_match(match["id"], actor=ACTOR)
        updated = self.banking.list_transactions(result["statement_id"])[0]
        self.assertEqual(updated["status"], "matched")
        self.assertEqual(updated["matched_id"], payment_id)


class ChequeAndPaymentTests(ServiceTestCase):
    def setUp(self):
        super().setUp()
        self.party_id = self.make_party("طرف چک", roles=["customer"])

    def test_cheque_lifecycle(self):
        cheque_id = self.banking.create_cheque("received", self.party_id, 5_000_000,
                                               issue_date="2026-02-01", due_date="2026-02-10",
                                               actor=ACTOR)
        self.banking.cheque_event(cheque_id, "in_process", actor=ACTOR, note="ارسال به بانک")
        self.assertEqual(self.banking.list_cheques()[0]["status"], "in_process")
        result = self.banking.clear_cheque(cheque_id, clear_date="2026-02-10", actor=ACTOR)
        self.assertTrue(result["created"])
        self.assertEqual(self.banking.list_cheques()[0]["status"], "cleared")
        with self.assertRaises(ConflictError):
            self.banking.clear_cheque(cheque_id, clear_date="2026-02-11", actor=ACTOR)

    def test_clearing_a_cheque_posts_a_balanced_entry(self):
        cheque_id = self.banking.create_cheque("received", self.party_id, 5_000_000, actor=ACTOR)
        self.banking.clear_cheque(cheque_id, clear_date="2026-02-10", actor=ACTOR)
        trial = self.ledger.book.trial_balance()
        self.assertTrue(trial["is_balanced"])
        self.assertEqual(trial["totals"]["debit_rial"], 5_000_000)

    def test_payment_posting_is_idempotent(self):
        payment_id = self.banking.create_payment(self.party_id, "in", 1_000_000,
                                                 payment_date="2026-02-01", actor=ACTOR)
        first = self.ledger.post_payment(payment_id, actor=ACTOR)
        second = self.ledger.post_payment(payment_id, actor=ACTOR)
        self.assertTrue(first["created"])
        self.assertFalse(second["created"])

    def test_payment_requires_a_positive_amount(self):
        with self.assertRaises(ValidationError):
            self.banking.create_payment(self.party_id, "in", 0, actor=ACTOR)
        with self.assertRaises(ValidationError):
            self.banking.create_payment(self.party_id, "sideways", 1000, actor=ACTOR)

    def test_cheques_due_uses_the_due_date(self):
        self.banking.create_cheque("received", self.party_id, 1_000_000,
                                   issue_date="2026-02-01", due_date="2026-02-05", actor=ACTOR)
        due = self.banking.cheques_due(within_days=7, as_of="2026-02-02")
        self.assertEqual(len(due), 1)


if __name__ == "__main__":
    unittest.main()
