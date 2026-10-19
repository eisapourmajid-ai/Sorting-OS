# -*- coding: utf-8 -*-
"""SORTING OS application package.

Layering (ADR-001):
    sorting_os.core      – money / calendar / id / error primitives (no I/O)
    sorting_os.db        – SQLite connection, versioned migrations, transactions
    sorting_os.services  – domain services (no UI, no tkinter imports)
    sorting_os.reporting – report builders on top of services
    sorting_os.ui        – Tkinter shell (imports services only)

Every service module is importable without tkinter so the whole domain can be
tested head-less. Python 3.8+, standard library only.
"""
from __future__ import annotations

__version__ = "0.2.0"
__all__ = ["__version__"]
