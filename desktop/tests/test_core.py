# -*- coding: utf-8 -*-
"""Core primitives: money policy and the offline Jalali calendar."""
from __future__ import annotations

import os
import sys
import unittest
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sorting_os import core  # noqa: E402


class MoneyPolicyTests(unittest.TestCase):
    def test_toman_to_rial_is_exact(self):
        self.assertEqual(core.to_rial("1250", "تومان"), 12500)
        self.assertEqual(core.to_rial("1250", "ریال"), 1250)
        self.assertEqual(core.to_rial("12.5", "تومان"), 125)
        self.assertEqual(core.to_rial(100, "ریال"), 100)

    def test_persian_and_arabic_digits_are_accepted(self):
        self.assertEqual(core.to_rial("۱٬۲۳۴", "تومان"), 12340)
        self.assertEqual(core.to_rial("١٢٣٤", "ریال"), 1234)
        self.assertEqual(core.to_rial("1,250", "ریال"), 1250)

    def test_invalid_amounts_are_rejected(self):
        for value, unit in (("0.1", "ریال"), ("-1", "تومان"), ("abc", "ریال"), ("", "ریال"),
                            ("NaN", "ریال")):
            with self.assertRaises(core.ValidationError):
                core.to_rial(value, unit)

    def test_no_float_in_money_arithmetic(self):
        total = sum(core.to_rial("0.1", "تومان") for _ in range(10))
        self.assertIsInstance(total, int)
        self.assertEqual(total, 10)

    def test_format_money_keeps_precision_and_unit(self):
        self.assertEqual(core.format_money(105, "تومان"), "10.5 تومان")
        self.assertEqual(core.format_money(1250, "ریال"), "1,250 ریال")
        self.assertEqual(core.format_money(100000, "میلیون تومان"), "0.01 میلیون تومان")
        self.assertEqual(core.format_money(105, "تومان", local_digits=True), "۱۰.۵ تومان")

    def test_format_money_rejects_fractional_rial(self):
        with self.assertRaises(core.ValidationError):
            core.format_money(100.5, "ریال")

    def test_million_toman_display_equals_rial_amount(self):
        rial = core.to_rial("1250", "تومان")
        self.assertEqual(core.format_money(rial, "میلیون تومان"), "0.00125 میلیون تومان")
        self.assertEqual(core.format_money(rial, "تومان"), "1,250 تومان")
        self.assertEqual(core.format_money(rial, "ریال"), "12,500 ریال")


class JalaliCalendarTests(unittest.TestCase):
    ANCHORS = [
        ("2026-10-19", (1405, 7, 27)),
        ("2026-03-21", (1405, 1, 1)),
        ("2025-03-21", (1404, 1, 1)),
        ("2024-03-20", (1403, 1, 1)),
        ("2020-03-20", (1399, 1, 1)),
        ("1979-02-11", (1357, 11, 22)),
        ("2000-01-01", (1378, 10, 11)),
        ("2012-03-20", (1391, 1, 1)),
        ("2022-03-21", (1401, 1, 1)),
    ]

    def test_known_anchor_dates(self):
        for iso, expected in self.ANCHORS:
            self.assertEqual(core.to_jalali(iso), expected, iso)

    def test_round_trip_over_two_centuries(self):
        current = date(1921, 4, 1)
        end = date(2121, 12, 31)
        while current < end:
            iso = current.isoformat()
            self.assertEqual(core.from_jalali(*core.to_jalali(iso)), iso)
            current += timedelta(days=1)

    def test_leap_years_follow_the_33_year_cycle(self):
        self.assertTrue(core.jalali_leap(1403))
        self.assertFalse(core.jalali_leap(1404))
        self.assertTrue(core.jalali_leap(1408))
        self.assertTrue(core.jalali_leap(1436))
        self.assertFalse(core.jalali_leap(1400))

    def test_format_and_parse(self):
        self.assertEqual(core.format_jalali("2026-10-19"), "1405/07/27")
        self.assertEqual(core.format_jalali_long("2026-10-19"), "27 مهر 1405")
        self.assertEqual(core.parse_jalali("1405/07/27"), "2026-10-19")
        self.assertEqual(core.parse_jalali("1405-7-27"), "2026-10-19")

    def test_invalid_jalali_dates_are_rejected(self):
        with self.assertRaises(core.ValidationError):
            core.parse_jalali("1404/12/30")  # 1404 is not a leap year
        with self.assertRaises(core.ValidationError):
            core.parse_jalali("1405/13/01")

    def test_jalali_month_and_year_ranges(self):
        self.assertEqual(core.jalali_month_range(1405, 7), ("2026-09-23", "2026-10-22"))
        self.assertEqual(core.jalali_year_range(1405), ("2026-03-21", "2027-03-20"))

    def test_iso_date_validation(self):
        self.assertEqual(core.normalize_iso_date("2026-01-05"), "2026-01-05")
        with self.assertRaises(core.ValidationError):
            core.normalize_iso_date("05/01/2026")
        with self.assertRaises(core.ValidationError):
            core.normalize_iso_date("2026-02-30")


if __name__ == "__main__":
    unittest.main()
