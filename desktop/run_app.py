# -*- coding: utf-8 -*-
"""Entry point of the SORTING OS desktop application.

This thin launcher exists so that both the source distribution and the
PyInstaller build (see ``sorting_os.spec``) start the same code path:

    python run_app.py
    python -m sorting_os
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sorting_os.app import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
