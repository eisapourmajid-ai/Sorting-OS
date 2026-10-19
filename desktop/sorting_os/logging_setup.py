# -*- coding: utf-8 -*-
"""Local logging for SORTING OS (Prompt 05).

Logging is entirely local: a rotating file inside the application data
directory plus an optional console stream.  No network handler exists, and no
telemetry is ever emitted (offline-first requirement).
"""
from __future__ import annotations

import logging
import logging.handlers
import os

LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(log_file=None, level="INFO", console=True, max_bytes=1_000_000,
                  backups=3):
    """Configure the root logger and return it.

    Calling the function twice does not duplicate handlers.
    """
    root = logging.getLogger("sorting_os")
    root.setLevel(getattr(logging, str(level).upper(), logging.INFO))
    for handler in list(root.handlers):
        root.removeHandler(handler)
        try:
            handler.close()
        except Exception:  # pragma: no cover - defensive
            pass

    formatter = logging.Formatter(LOG_FORMAT, DATE_FORMAT)
    if log_file:
        parent = os.path.dirname(os.path.abspath(log_file))
        if parent and not os.path.isdir(parent):
            os.makedirs(parent)
        file_handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=max_bytes, backupCount=backups, encoding="utf-8")
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)
    if console:
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        root.addHandler(stream_handler)
    root.propagate = False
    return root


def get_logger(name="sorting_os"):
    return logging.getLogger("sorting_os." + name if name != "sorting_os" else name)
