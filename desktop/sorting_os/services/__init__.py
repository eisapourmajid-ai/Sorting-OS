# -*- coding: utf-8 -*-
"""Domain services of SORTING OS.

Every service is a thin, testable layer over :class:`sorting_os.db.AppDatabase`.
No service imports tkinter, and no service writes to the filesystem except the
backup service (which is explicitly requested by the operator).

The exports are resolved lazily (PEP 562) so that a partially migrated checkout
can still import the services it already contains.
"""
from __future__ import annotations

import importlib

_EXPORTS = {
    "Actor": ("auth", "Actor"),
    "AuthService": ("auth", "AuthService"),
    "BackupService": ("backup", "BackupService"),
    "BankingService": ("banking", "BankingService"),
    "CatalogService": ("catalog", "CatalogService"),
    "DocumentService": ("documents", "DocumentService"),
    "ExchangeService": ("exchange", "ExchangeService"),
    "LedgerService": ("ledger", "LedgerService"),
    "OperationsService": ("operations", "OperationsService"),
    "PartyService": ("parties", "PartyService"),
    "PeriodService": ("periods", "PeriodService"),
    "PrintService": ("printing", "PrintService"),
    "ReportService": ("reporting", "ReportService"),
    "SettlementService": ("settlement", "SettlementService"),
}

__all__ = sorted(_EXPORTS)


def __getattr__(name):
    try:
        module_name, attribute = _EXPORTS[name]
    except KeyError:
        raise AttributeError("module %r has no attribute %r" % (__name__, name))
    module = importlib.import_module("." + module_name, __name__)
    value = getattr(module, attribute)
    globals()[name] = value
    return value


def __dir__():
    return sorted(set(list(globals().keys()) + __all__))
