# -*- coding: utf-8 -*-
"""UI layer of SORTING OS (Prompt 24).

The package is split so that the parts that can be verified without a display
server stay importable and testable:

* :mod:`sorting_os.ui.formatting` — bidi isolation and money/date formatting;
* :mod:`sorting_os.ui.theme` — design tokens and the theme service;
* :mod:`sorting_os.ui.app` — the Tkinter shell (imports ``tkinter`` lazily, so
  the module can be imported — but not rendered — on a head-less machine).
"""
from __future__ import annotations
