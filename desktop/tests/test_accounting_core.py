# -*- coding: utf-8 -*-
import os
import tempfile
import unittest
from accounting_core import AccountingBook, parse_amount_to_rial, format_money
from database import Database


class AccountingCoreTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tempdir.name, 'accounting.sqlite3')
        self.book = AccountingBook(self.path)

    def tearDown(self):
        self.tempdir.cleanup()

    def post(self, date, desc, lines, **kwargs):
        return self.book.post_entry(date, desc, lines, actor='test', **kwargs)

    def test_rial_toman_conversion_exact_and_persian_digits(self):
        self.assertEqual(parse_amount_to_rial('۱٬۲۳۴', 'تومان'), 12340)
        self.assertEqual(parse_amount_to_rial('12.5', 'تومان'), 125)
        self.assertEqual(parse_amount_to_rial('1,250', 'ریال'), 1250)
        self.assertEqual(format_money(105, 'تومان'), '10.5 تومان')
        self.assertEqual(format_money(100000, 'میلیون تومان'), '0.01 میلیون تومان')

    def test_invalid_fractional_rial_and_negative_rejected(self):
        with self.assertRaises(ValueError):
            parse_amount_to_rial('0.1', 'ریال')
        with self.assertRaises(ValueError):
            parse_amount_to_rial('-1', 'تومان')

    def test_internal_rial_amounts_never_silently_truncate(self):
        with self.assertRaises(ValueError):
            self.post('2026-01-01', 'اعشار نامعتبر', [
                {'account_code': '1000', 'debit_rial': 100.5, 'credit_rial': 0},
                {'account_code': '3000', 'debit_rial': 0, 'credit_rial': 100.5},
            ])
        with self.assertRaises(ValueError):
            format_money(100.5, 'ریال')
        with self.book.connect() as con:
            self.assertEqual(con.execute('select count(*) from journal_entries').fetchone()[0], 0)

    def test_unbalanced_journal_rejected(self):
        with self.assertRaises(ValueError):
            self.post('2026-01-01', 'سند نامتوازن', [
                {'account_code': '1000', 'debit_rial': 100, 'credit_rial': 0},
                {'account_code': '3000', 'debit_rial': 0, 'credit_rial': 90},
            ])
        with self.book.connect() as con:
            self.assertEqual(con.execute('select count(*) from journal_entries').fetchone()[0], 0)

    def test_post_and_trial_balance(self):
        self.post('2026-01-01', 'واریز سرمایه', [
            {'account_code': '1010', 'debit_rial': 100000, 'credit_rial': 0},
            {'account_code': '3000', 'debit_rial': 0, 'credit_rial': 100000},
        ])
        tb = self.book.trial_balance()
        self.assertTrue(tb['is_balanced'])
        self.assertEqual(tb['totals']['debit_rial'], 100000)
        self.assertEqual(tb['totals']['credit_rial'], 100000)
        self.assertEqual(tb['totals']['closing_debit_rial'], 100000)
        self.assertEqual(tb['totals']['closing_credit_rial'], 100000)

    def test_balance_sheet_and_income_statement(self):
        self.post('2026-01-01', 'سرمایه اولیه', [
            {'account_code': '1010', 'debit_rial': 1000000, 'credit_rial': 0},
            {'account_code': '3000', 'debit_rial': 0, 'credit_rial': 1000000},
        ])
        self.post('2026-01-02', 'ارائه خدمات', [
            {'account_code': '1010', 'debit_rial': 500000, 'credit_rial': 0},
            {'account_code': '4000', 'debit_rial': 0, 'credit_rial': 500000},
        ])
        self.post('2026-01-03', 'پرداخت هزینه', [
            {'account_code': '6000', 'debit_rial': 100000, 'credit_rial': 0},
            {'account_code': '1010', 'debit_rial': 0, 'credit_rial': 100000},
        ])
        inc = self.book.income_statement('2026-01-01', '2026-01-31')
        self.assertEqual(inc['revenue_total_rial'], 500000)
        self.assertEqual(inc['expense_total_rial'], 100000)
        self.assertEqual(inc['net_profit_rial'], 400000)
        bs = self.book.balance_sheet('2026-01-31')
        self.assertTrue(bs['is_balanced'])
        self.assertEqual(bs['assets_total_rial'], 1400000)
        self.assertEqual(bs['liabilities_equity_total_rial'], 1400000)

    def test_duplicate_source_posting_is_rejected(self):
        lines = [
            {'account_code': '1010', 'debit_rial': 500, 'credit_rial': 0},
            {'account_code': '3000', 'debit_rial': 0, 'credit_rial': 500},
        ]
        self.post('2026-01-01', 'منبع یکتا', lines, source_type='test', source_id='123')
        with self.assertRaises(ValueError):
            self.post('2026-01-01', 'تکرار منبع', lines, source_type='test', source_id='123')
        with self.book.connect() as con:
            self.assertEqual(con.execute('select count(*) from journal_entries').fetchone()[0], 1)

    def test_reversal_creates_counter_entry_not_deletion(self):
        original = self.post('2026-01-01', 'سرمایه', [
            {'account_code': '1010', 'debit_rial': 700, 'credit_rial': 0},
            {'account_code': '3000', 'debit_rial': 0, 'credit_rial': 700},
        ])
        reversed_id = self.book.reverse_entry(original, '2026-01-02', 'ثبت اشتباه', actor='test')
        self.assertNotEqual(original, reversed_id)
        with self.book.connect() as con:
            self.assertEqual(con.execute('select count(*) from journal_entries').fetchone()[0], 2)
            self.assertEqual(con.execute('select count(*) from journal_lines').fetchone()[0], 4)
        tb = self.book.trial_balance()
        self.assertEqual(tb['totals']['closing_debit_rial'], 0)
        self.assertEqual(tb['totals']['closing_credit_rial'], 0)

    def test_cash_flow_reconciles(self):
        self.post('2026-01-01', 'سرمایه', [
            {'account_code': '1010', 'debit_rial': 1000, 'credit_rial': 0},
            {'account_code': '3000', 'debit_rial': 0, 'credit_rial': 1000},
        ])
        self.post('2026-01-02', 'هزینه نقدی', [
            {'account_code': '6000', 'debit_rial': 200, 'credit_rial': 0},
            {'account_code': '1010', 'debit_rial': 0, 'credit_rial': 200},
        ])
        cf = self.book.cash_flow_statement('2026-01-01', '2026-01-31')
        self.assertTrue(cf['reconciles'])
        self.assertEqual(cf['opening_cash_rial'], 0)
        self.assertEqual(cf['closing_cash_rial'], 800)
        self.assertEqual(cf['net_change_rial'], 800)

    def test_legacy_invoice_does_not_auto_post_into_financial_reports(self):
        operational = Database(self.path)
        party_id = operational.save_party({'display_name': 'مشتری آزمون', 'roles': 'خریدار'}, actor='test')
        operational.create_invoice(party_id, 'فروش', '2026-01-02', 1000, 'فاکتور قدیمی', status='قطعی', actor='test')
        # Initializing the ledger on the same SQLite file must not reinterpret legacy amount REAL.
        self.book = AccountingBook(self.path)
        self.assertEqual(self.book.list_entries(), [])
        tb = self.book.trial_balance()
        self.assertEqual(tb['totals']['debit_rial'], 0)
        self.assertEqual(tb['totals']['credit_rial'], 0)
        with self.book.connect() as con:
            self.assertEqual(con.execute('select count(*) from invoices').fetchone()[0], 1)
            self.assertEqual(con.execute('select count(*) from journal_entries').fetchone()[0], 0)

    def test_ledger_reversal_date_filter(self):
        self.post('2026-01-01', 'سرمایه', [
            {'account_code': '1010', 'debit_rial': 100, 'credit_rial': 0},
            {'account_code': '3000', 'debit_rial': 0, 'credit_rial': 100},
        ])
        self.assertEqual(len(self.book.account_ledger('1010', '2026-01-01', '2026-01-01')['lines']), 1)
        self.assertEqual(len(self.book.account_ledger('1010', '2026-01-02', '2026-01-03')['lines']), 0)


if __name__ == '__main__':
    unittest.main()
