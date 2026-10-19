# -*- coding: utf-8 -*-
"""Predictable local paths for SORTING OS (Prompt 05).

The data location must never depend on the current working directory or on
where the program happens to be installed.  It is resolved from the operating
system conventions and can be overridden explicitly:

* environment variable ``SORTING_OS_HOME`` (highest priority);
* Windows: ``%LOCALAPPDATA%\\SortingOS``;
* other platforms: ``$XDG_DATA_HOME/sorting-os`` or ``~/.local/share/sorting-os``.

All files created by the application (database, logs, backups, exports) live
below that single root, so that backup/restore and support instructions stay
predictable.
"""
from __future__ import annotations

import os

APP_DIR_NAME = "sorting-os"
WINDOWS_DIR_NAME = "SortingOS"
ENV_HOME = "SORTING_OS_HOME"


class AppPaths:
    """Resolved locations of the local application data."""

    def __init__(self, home):
        self.home = os.path.abspath(home)

    # -- directories -------------------------------------------------------- #
    @property
    def data_dir(self):
        return self.home

    @property
    def db_dir(self):
        return os.path.join(self.home, "db")

    @property
    def backup_dir(self):
        return os.path.join(self.home, "backups")

    @property
    def export_dir(self):
        return os.path.join(self.home, "exports")

    @property
    def import_dir(self):
        return os.path.join(self.home, "imports")

    @property
    def log_dir(self):
        return os.path.join(self.home, "logs")

    @property
    def config_file(self):
        return os.path.join(self.home, "config.json")

    # -- files -------------------------------------------------------------- #
    @property
    def db_file(self):
        return os.path.join(self.db_dir, "sorting_os.sqlite3")

    @property
    def log_file(self):
        return os.path.join(self.log_dir, "sorting_os.log")

    def ensure(self):
        """Create the directory tree (idempotent, offline)."""
        for path in (self.data_dir, self.db_dir, self.backup_dir, self.export_dir,
                     self.import_dir, self.log_dir):
            if not os.path.isdir(path):
                os.makedirs(path)
        return self

    # -- resolution --------------------------------------------------------- #
    @classmethod
    def resolve(cls, home=None, environ=None):
        environ = os.environ if environ is None else environ
        if home:
            return cls(home)
        override = environ.get(ENV_HOME)
        if override:
            return cls(override)
        if os.name == "nt":
            base = environ.get("LOCALAPPDATA") or os.path.expanduser("~")
            return cls(os.path.join(base, WINDOWS_DIR_NAME))
        base = environ.get("XDG_DATA_HOME") or os.path.join(os.path.expanduser("~"),
                                                           ".local", "share")
        return cls(os.path.join(base, APP_DIR_NAME))

    def __repr__(self):  # pragma: no cover - debugging helper
        return "AppPaths(home=%r)" % self.home
