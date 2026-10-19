# -*- coding: utf-8 -*-
"""Design tokens and theme service (Prompt 24).

The theme is fully local: no font, icon or colour is fetched from the
internet.  The selected theme is stored in the local ``settings`` table, so it
survives a restart and is independent from business data.

The exact brand colours, the Persian font and the icon set are listed as open
design decisions in ``reference-inputs/UI_LAYOUT_THEME_HEADER_SPEC.md``; the
values below are neutral technical defaults, not a brand decision.
"""
from __future__ import annotations

THEME_KEY = "ui.theme_mode"
THEME_OPTIONS = ("light", "dark")

LIGHT = {
    "name": "light",
    "background": "#f5f6f8",
    "surface": "#ffffff",
    "surface_alt": "#eef1f5",
    "text": "#1f2933",
    "text_muted": "#5b6770",
    "border": "#d3d9e0",
    "primary": "#1f6feb",
    "primary_text": "#ffffff",
    "success": "#1f7a44",
    "warning": "#9a6700",
    "danger": "#b3261e",
    "header_background": "#ffffff",
    "row_alternate": "#f8f9fb",
}

DARK = {
    "name": "dark",
    "background": "#14171c",
    "surface": "#1d2127",
    "surface_alt": "#262b33",
    "text": "#e6e9ee",
    "text_muted": "#9aa4b2",
    "border": "#333a44",
    "primary": "#4c8dff",
    "primary_text": "#0b0d10",
    "success": "#3fb950",
    "warning": "#d29922",
    "danger": "#f85149",
    "header_background": "#1d2127",
    "row_alternate": "#22262d",
}

THEMES = {"light": LIGHT, "dark": DARK}

#: Spacing scale (px) and radii used by the shell.
SPACING = {"xs": 4, "sm": 8, "md": 12, "lg": 16, "xl": 24}


class ThemeService:
    """Load/store the theme preference and expose the token table."""

    def __init__(self, db=None, actor="کاربر محلی"):
        self.db = db
        self.actor = actor
        self.mode = "light"

    # -- preference --------------------------------------------------------- #
    def load(self):
        if self.db is not None:
            stored = self.db.get_setting(THEME_KEY, "light")
            if stored in THEME_OPTIONS:
                self.mode = stored
        return self.mode

    def save(self, mode):
        if mode not in THEME_OPTIONS:
            raise ValueError("تم نامعتبر است: %s" % mode)
        self.mode = mode
        if self.db is not None:
            self.db.set_setting(THEME_KEY, mode, actor=self.actor)
        return self.mode

    def toggle(self):
        return self.save("dark" if self.mode == "light" else "light")

    # -- tokens ------------------------------------------------------------- #
    def tokens(self):
        return dict(THEMES[self.mode])

    def token(self, name, default=None):
        return THEMES[self.mode].get(name, default)

    def spacing(self, name="md"):
        return SPACING.get(name, SPACING["md"])
