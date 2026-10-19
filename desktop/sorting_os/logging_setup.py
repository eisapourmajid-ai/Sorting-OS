# -*- coding: utf-8 -*-
"""Local logging for SORTING OS (Prompt 05 / Prompt 27).

Logging is entirely local: a rotating file inside the application data
directory plus an optional console stream.  No network handler exists, and no
telemetry is ever emitted (offline-first requirement).

The rotating handler is implemented here on purpose: ``logging.handlers``
imports ``socket`` (for its ``SocketHandler``), which would make even a
purely local application look network capable.  With the local implementation
the whole application starts without any networking module being loaded — a
property that is verified by ``desktop/tests/test_offline.py``.
"""
from __future__ import annotations

import logging
import os

LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


class RotatingFileHandler(logging.FileHandler):
    """A small size-based rotating file handler (no networking imports)."""

    def __init__(self, filename, max_bytes=1_000_000, backup_count=3, encoding="utf-8"):
        super().__init__(filename, mode="a", encoding=encoding, delay=True)
        self.max_bytes = max_bytes
        self.backup_count = backup_count

    def should_rollover(self, record):
        try:
            if self.stream is None:
                self.stream = self._open()
            if self.stream.tell() + len(record.getMessage()) > self.max_bytes:
                return True
        except OSError:  # pragma: no cover - defensive
            return False
        return False

    def do_rollover(self):
        if self.stream:
            self.stream.close()
            self.stream = None
        for index in range(self.backup_count - 1, 0, -1):
            source = "%s.%d" % (self.baseFilename, index)
            target = "%s.%d" % (self.baseFilename, index + 1)
            if os.path.exists(source):
                os.replace(source, target)
        if os.path.exists(self.baseFilename):
            os.replace(self.baseFilename, self.baseFilename + ".1")

    def emit(self, record):
        try:
            if self.should_rollover(record):
                self.do_rollover()
            super().emit(record)
        except Exception:  # pragma: no cover - defensive
            self.handleError(record)


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
        file_handler = RotatingFileHandler(log_file, max_bytes=max_bytes,
                                          backup_count=backups)
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
