# -*- coding: utf-8 -*-
"""UI helpers that can be verified without a display server (Prompt 24)."""
from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sorting_os.ui.formatting import (LRI, PDI, empty_state_text, isolate,  # noqa: E402
                                      isolate_tokens, money_display, status_label,
                                      strip_isolates, weight_display)
from sorting_os.ui.theme import THEMES, ThemeService  # noqa: E402


class BidiTests(unittest.TestCase):
    def test_isolate_wraps_without_changing_the_text(self):
        self.assertEqual(strip_isolates(isolate("INV-12")), "INV-12")

    def test_numbers_are_isolated_inside_persian_text(self):
        text = isolate_tokens("فاکتور 1234 مورخ 1405/01/01")
        self.assertIn(LRI + "1234" + PDI, text)
        self.assertIn(LRI + "1405/01/01" + PDI, text)
        self.assertTrue(text.startswith("فاکتور "))

    def test_persian_digits_are_not_wrapped(self):
        text = isolate_tokens("مبلغ ۱۲۳۴ ریال")
        self.assertNotIn(LRI, text)

    def test_strip_isolates_removes_all_marks(self):
        self.assertEqual(strip_isolates(isolate_tokens("سند 12")), "سند 12")


class DisplayTests(unittest.TestCase):
    def test_money_display_always_shows_the_unit(self):
        self.assertIn("ریال", money_display(12500, "ریال"))
        self.assertIn("تومان", money_display(12500, "تومان"))

    def test_weight_display_uses_kg(self):
        self.assertIn("کیلوگرم", weight_display(12.34))

    def test_status_labels_are_persian(self):
        self.assertEqual(status_label("confirmed"), "قطعی")
        self.assertEqual(status_label("draft"), "پیش‌نویس")

    def test_empty_states_are_distinct(self):
        self.assertNotEqual(empty_state_text("table"), empty_state_text("table", True))
        self.assertIn("فیلتر", empty_state_text("table", True))


class ThemeTests(unittest.TestCase):
    def test_both_themes_define_the_same_tokens(self):
        self.assertEqual(sorted(THEMES["light"]), sorted(THEMES["dark"]))

    def test_theme_is_persisted_locally(self):
        import tempfile

        from sorting_os.db import AppDatabase

        root = tempfile.mkdtemp()
        db = AppDatabase(os.path.join(root, "theme.sqlite3"))
        service = ThemeService(db, actor="tester")
        self.assertEqual(service.load(), "light")
        service.toggle()
        self.assertEqual(service.mode, "dark")
        self.assertEqual(ThemeService(db).load(), "dark")
        self.assertEqual(db.get_setting("ui.theme_mode"), "dark")

    def test_invalid_theme_is_rejected(self):
        service = ThemeService()
        with self.assertRaises(ValueError):
            service.save("neon")


if __name__ == "__main__":
    unittest.main()
