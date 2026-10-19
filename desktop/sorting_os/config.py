# -*- coding: utf-8 -*-
"""Local configuration for SORTING OS (Prompt 05).

The configuration is a small JSON file in the application data directory.  It
only contains *technical* defaults; every business rule that is still an open
decision stays ``None`` and is reported as such instead of being invented
here.  Runtime settings that belong to the database (e.g. the last used
report filters) live in the ``settings`` table and are managed by
:meth:`sorting_os.db.AppDatabase.set_setting`.
"""
from __future__ import annotations

import copy
import json
import os

#: Technical defaults.  ``None`` means "not decided yet" (open decision).
DEFAULTS = {
    "schema": 1,
    "input_unit": "ریال",
    "display_unit": "ریال",
    "display_unit_options": ["ریال", "تومان", "میلیون تومان"],
    "log_level": "INFO",
    "fiscal_year_start_month": None,   # DEC-008 (open)
    "settlement_rate_percent": None,   # DEC-003 (open)
    "cost_allocation_method": None,    # DEC-006 (open)
    "goods_ownership_model": None,     # DEC-001/DEC-002 (open)
    "receipts_allocation_policy": "receipts-fifo-v1",  # TECH-006 (provisional, DEC-015)
    "features": {
        "bank_import": True,
        "settlement": True,
        "printing": True,
        "period_closing": True,
    },
}


class AppConfig:
    """Read/write access to ``config.json``."""

    def __init__(self, data=None, path=None):
        self.path = path
        self.data = copy.deepcopy(DEFAULTS)
        if data:
            self.data.update(data)

    # -- io ----------------------------------------------------------------- #
    @classmethod
    def load(cls, path, defaults=None):
        instance = cls(path=path)
        if defaults:
            instance.data.update(copy.deepcopy(defaults))
        if path and os.path.isfile(path):
            try:
                with open(path, encoding="utf-8") as handle:
                    stored = json.load(handle)
            except (OSError, ValueError):
                return instance
            if isinstance(stored, dict):
                instance.data.update(stored)
        return instance

    def save(self, path=None):
        target = path or self.path
        if not target:
            raise ValueError("مسیر فایل تنظیمات مشخص نشده است.")
        parent = os.path.dirname(os.path.abspath(target))
        if parent and not os.path.isdir(parent):
            os.makedirs(parent)
        with open(target, "w", encoding="utf-8") as handle:
            json.dump(self.data, handle, ensure_ascii=False, indent=2, sort_keys=True)
        return target

    # -- accessors ---------------------------------------------------------- #
    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value
        return value

    def feature_enabled(self, name):
        return bool(self.data.get("features", {}).get(name, False))

    def open_decisions(self):
        """Keys whose value is still an open business decision."""
        return sorted(key for key, value in self.data.items() if value is None)

    def as_dict(self):
        return copy.deepcopy(self.data)
