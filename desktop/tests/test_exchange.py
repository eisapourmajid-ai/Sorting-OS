# -*- coding: utf-8 -*-
"""Import/export engine: preview, mapping, commit, idempotency and exports."""
from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sorting_os.core import ValidationError  # noqa: E402
from support import ACTOR, ServiceTestCase  # noqa: E402


class ImportTests(ServiceTestCase):
    ROWS = [
        {"نام": "باغدار یک", "تلفن": "09120000001", "کد ملی": "0011111111"},
        {"نام": "باغدار دو", "تلفن": "09120000002", "کد ملی": "0022222222"},
        {"نام": "", "تلفن": "09120000003", "کد ملی": "0033333333"},
    ]

    def test_preview_does_not_write_anything(self):
        result = self.exchange.preview("parties", self.ROWS, unit="ریال", actor=ACTOR)
        self.assertEqual(result["status"], "preview")
        self.assertEqual(result["row_count"], 2)
        self.assertEqual(result["error_count"], 1)
        with self.db.reader() as con:
            self.assertEqual(con.execute("SELECT COUNT(*) FROM parties").fetchone()[0], 0)

    def test_missing_required_field_is_a_row_error(self):
        result = self.exchange.preview("parties", self.ROWS, unit="ریال", actor=ACTOR)
        self.assertEqual(result["errors"][0]["row_no"], 3)
        self.assertIn("display_name", result["errors"][0]["error"])

    def test_mapping_maps_source_columns_to_fields(self):
        mapping = {"display_name": "نام", "phone": "تلفن", "national_id": "کد ملی"}
        result = self.exchange.preview("parties", self.ROWS, mapping=mapping, unit="ریال",
                                        actor=ACTOR)
        self.assertEqual(result["row_count"], 2)

    def test_commit_writes_valid_rows_only(self):
        mapping = {"display_name": "نام", "phone": "تلفن", "national_id": "کد ملی"}
        preview = self.exchange.preview("parties", self.ROWS, mapping=mapping, unit="ریال",
                                         actor=ACTOR)
        committed = self.exchange.commit(preview["batch_id"], actor=ACTOR)
        self.assertEqual(committed["committed"], 2)
        with self.db.reader() as con:
            self.assertEqual(con.execute("SELECT COUNT(*) FROM parties").fetchone()[0], 2)

    def test_importing_the_same_file_twice_is_idempotent(self):
        mapping = {"display_name": "نام", "phone": "تلفن", "national_id": "کد ملی"}
        first = self.exchange.preview("parties", self.ROWS, mapping=mapping, unit="ریال",
                                       actor=ACTOR)
        self.exchange.commit(first["batch_id"], actor=ACTOR)
        second = self.exchange.preview("parties", self.ROWS, mapping=mapping, unit="ریال",
                                        actor=ACTOR)
        self.assertTrue(second["duplicate"])
        with self.db.reader() as con:
            self.assertEqual(con.execute("SELECT COUNT(*) FROM parties").fetchone()[0], 2)

    def test_unit_must_be_explicit(self):
        with self.assertRaises(ValidationError):
            self.exchange.preview("parties", self.ROWS, unit="auto", actor=ACTOR)

    def test_duplicate_national_id_fails_only_that_row(self):
        self.parties.create("باغدار یک", national_id="0011111111", actor=ACTOR)
        mapping = {"display_name": "نام", "phone": "تلفن", "national_id": "کد ملی"}
        preview = self.exchange.preview("parties", self.ROWS, mapping=mapping, unit="ریال",
                                         actor=ACTOR)
        committed = self.exchange.commit(preview["batch_id"], actor=ACTOR)
        self.assertEqual(committed["committed"], 1)
        self.assertEqual(len(committed["failed"]), 1)
        with self.db.reader() as con:
            self.assertEqual(con.execute("SELECT COUNT(*) FROM parties").fetchone()[0], 2)

    def test_money_import_uses_the_declared_unit(self):
        party_id = self.make_party()
        rows = [{"party_id": party_id, "document_date": "2026-02-01", "amount": "1250",
                 "invoice_type": "فروش", "kind": "sales"}]
        preview = self.exchange.preview("invoices", rows, unit="تومان", actor=ACTOR)
        self.assertEqual(preview["row_count"], 1)
        self.exchange.commit(preview["batch_id"], actor=ACTOR)
        with self.db.reader() as con:
            invoice = con.execute("SELECT amount_rial FROM invoices").fetchone()
        self.assertEqual(invoice["amount_rial"], 12_500)


class ExportTests(ServiceTestCase):
    def test_export_contains_the_data_and_a_checksum(self):
        self.parties.create("باغدار یک", national_id="0011111111", actor=ACTOR)
        result = self.exchange.export("parties", actor=ACTOR)
        self.assertEqual(result["row_count"], 1)
        self.assertIn("باغدار یک", result["csv"])
        self.assertTrue(result["sha256"])
        with self.db.reader() as con:
            batches = con.execute("SELECT COUNT(*) FROM export_batches").fetchone()[0]
        self.assertEqual(batches, 1)

    def test_export_of_invoices_uses_the_rial_column(self):
        party_id = self.make_party()
        self.documents.create_invoice(party_id, document_date="2026-02-01",
                                      lines=[{"weight_kg": 1, "unit_price": 12_500}],
                                      actor=ACTOR)
        result = self.exchange.export("invoices", actor=ACTOR)
        self.assertIn("12500", result["csv"])

    def test_unknown_entity_is_rejected(self):
        with self.assertRaises(ValidationError):
            self.exchange.export("unicorns", actor=ACTOR)


if __name__ == "__main__":
    unittest.main()
