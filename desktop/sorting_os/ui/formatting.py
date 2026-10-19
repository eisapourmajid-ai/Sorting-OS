# -*- coding: utf-8 -*-
"""RTL formatting helpers (Prompt 24).

Numbers, document numbers and Latin identifiers must keep their own direction
inside Persian (right-to-left) text.  The Unicode isolate characters are used
for that; they are invisible and do not change the stored value.

The helpers here are pure functions without any tkinter dependency so that they
can be unit tested on a head-less machine.
"""
from __future__ import annotations

import re

#: Left-to-right isolate / pop directional isolate
LRI = "⁦"
#: Right-to-left isolate
RLI = "⁧"
#: Pop directional isolate
PDI = "⁩"

_LATIN_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_./:\-]*")


def isolate(text):
    """Wrap ``text`` in a left-to-right isolate (safe inside RTL paragraphs)."""
    if text is None:
        return ""
    return LRI + str(text) + PDI


def isolate_tokens(text):
    """Isolate every Latin/number token inside a Persian string.

    ``"فاکتور 1234 مورخ 1405/01/01"`` becomes a string where ``1234`` and
    ``1405/01/01`` are each wrapped in an LRI…PDI isolate.
    """
    if text is None:
        return ""
    return _LATIN_TOKEN.sub(lambda match: isolate(match.group(0)), str(text))


def strip_isolates(text):
    """Remove the isolate characters (used before storing a value)."""
    if text is None:
        return ""
    return str(text).replace(LRI, "").replace(RLI, "").replace(PDI, "")


def money_display(amount_rial, unit="ریال", thousands=True):
    """Format an integer rial amount with an explicit unit (money policy)."""
    from ..core import format_money

    if unit == "ریال":
        text = format_money(amount_rial, "ریال")
    else:
        text = format_money(amount_rial, unit)
    return "%s %s" % (text, unit)


def weight_display(weight_kg, digits=1):
    """Format a weight with a fixed unit (kg)."""
    if weight_kg is None:
        return "—"
    text = ("%%.%df" % digits) % float(weight_kg)
    return "%s کیلوگرم" % text


def status_label(status):
    """Human readable Persian label for a document status."""
    labels = {
        "draft": "پیش‌نویس",
        "confirmed": "قطعی",
        "cancelled": "لغوشده",
        "posted": "ثبت در دفترکل",
        "closed": "بسته‌شده",
        "open": "باز",
        "suggested": "پیشنهاد",
        "accepted": "تأییدشده",
        "rejected": "ردشده",
        "cleared": "وصول/پرداخت‌شده",
        "in_process": "در جریان",
        "settled": "تسویه‌شده",
    }
    return labels.get(status, status)


def empty_state_text(kind="list", filter_active=False):
    """Distinct empty states (the spec forbids a single generic message)."""
    if filter_active:
        return "هیچ سندی مطابق فیلترهای انتخاب‌شده یافت نشد."
    if kind == "table":
        return "هنوز سندی ثبت نشده است."
    if kind == "report":
        return "داده‌ای برای این بازه زمانی وجود ندارد."
    return "موردی برای نمایش وجود ندارد."
