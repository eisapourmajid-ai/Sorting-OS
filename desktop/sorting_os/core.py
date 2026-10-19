# -*- coding: utf-8 -*-
"""Core primitives for SORTING OS: money policy, Jalali calendar, codes, errors.

This module is the single source of truth for the two policies the whole
application depends on:

* **Money** - every internal amount is an ``int`` number of Iranian Rials.
  1 Toman = 10 Rials.  ``float``/``REAL`` is never used for money.
  (See ``docs/financial/MONEY_UNIT_POLICY_FA.md``.)
* **Calendar** - storage is always ISO Gregorian ``YYYY-MM-DD``; the Jalali
  (Shamsi) calendar is an offline, pure-integer conversion used for input and
  display only.  (See ``docs/financial/ACCOUNTING_CORE_SPEC_FA.md`` section 7.)

No I/O, no database, no tkinter: everything here is unit-testable.
"""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation

RIAL_PER_TOMAN = 10
PERSIAN_DIGITS = "۰۱۲۳۴۵۶۷۸۹"
ARABIC_DIGITS = "٠١٢٣٤٥٦٧٨٩"
ASCII_DIGITS = "0123456789"

#: Unit of the integer amount stored in the database.
BASE_MONEY_UNIT = "IRR"


class DomainError(ValueError):
    """Business/domain rule violation. Always safe to show to the operator."""


class ValidationError(DomainError):
    """Input failed a domain validation rule."""


class ConflictError(DomainError):
    """The request conflicts with the current persisted state (duplicates, ...)."""


class PermissionDenied(DomainError):
    """The current actor is not allowed to perform the operation."""


# --------------------------------------------------------------------------- #
# Numbers and money
# --------------------------------------------------------------------------- #
def normalize_digits(value):
    """Convert Persian/Arabic digits and separators to stable ASCII text."""
    if value is None:
        return ""
    text = str(value).strip()
    table = str.maketrans(PERSIAN_DIGITS + ARABIC_DIGITS, ASCII_DIGITS * 2)
    text = text.translate(table)
    for ch in ("٬", "،", ",", "_", " "):
        text = text.replace(ch, "")
    return text


def to_rial_strict(value, field="مبلغ ریالی", allow_negative=False):
    """Parse an already-rial integer amount (no unit conversion).

    Used for internal ledger values where the unit is fixed.  Fractional
    values are rejected instead of being silently truncated.
    """
    if isinstance(value, bool):
        raise ValidationError("%s باید عدد صحیح ریال باشد." % field)
    if isinstance(value, int):
        amount = Decimal(value)
    elif isinstance(value, Decimal):
        amount = value
    else:
        text = normalize_digits(value)
        if not text:
            raise ValidationError("%s خالی است." % field)
        try:
            amount = Decimal(text)
        except (InvalidOperation, ValueError):
            raise ValidationError("%s معتبر نیست." % field)
    if not amount.is_finite():
        raise ValidationError("%s باید عددی متناهی باشد." % field)
    if amount != amount.to_integral_value():
        raise ValidationError("%s باید عدد صحیح ریال باشد؛ گردکردن خودکار ممنوع است." % field)
    if not allow_negative and amount < 0:
        raise ValidationError("%s نمی‌تواند منفی باشد." % field)
    return int(amount)


#: Unit words that may travel inside the value itself, e.g. ``1250 تومان``.
UNIT_TOKENS = (
    ("میلیون تومان", "million_toman"),
    ("میلیون‌تومان", "million_toman"),
    ("تومان", "toman"),
    ("toman", "toman"),
    ("tomans", "toman"),
    ("ریال", "rial"),
    ("ريال", "rial"),
    ("rial", "rial"),
    ("rials", "rial"),
)

UNIT_MULTIPLIERS = {
    "rial": Decimal(1),
    "toman": Decimal(RIAL_PER_TOMAN),
    "million_toman": Decimal(RIAL_PER_TOMAN) * Decimal(1000000),
}


def detect_unit(text):
    """Return the unit word carried by a value such as ``1250 تومان``."""
    if text is None:
        return None
    lowered = str(text).strip().lower()
    for token, name in UNIT_TOKENS:
        if token in lowered:
            return name
    return None


def to_rial(value, unit="ریال", field="مبلغ"):
    """Convert an amount in ``unit`` to integer Rials without float math.

    Accepts ``int``, ``str`` or ``Decimal``.  A unit written inside the value
    (``"1250 تومان"``) wins over the default parameter; a value that carries a
    unit conflicting with an explicitly different parameter is rejected so the
    operator has to resolve the ambiguity.
    """
    if isinstance(value, bool):
        raise ValidationError("%s باید عدد باشد." % field)
    embedded = detect_unit(value) if not isinstance(value, (int, Decimal)) else None
    if isinstance(value, int):
        amount = Decimal(value)
    elif isinstance(value, Decimal):
        amount = value
    else:
        text = normalize_digits(value)
        for token, _name in UNIT_TOKENS:
            text = text.replace(token, "").replace(token.upper(), "")
        if not text:
            raise ValidationError("%s خالی است." % field)
        try:
            amount = Decimal(text)
        except (InvalidOperation, ValueError):
            raise ValidationError("قالب %s معتبر نیست." % field)
    if not amount.is_finite():
        raise ValidationError("%s باید عددی متناهی باشد." % field)
    if amount < 0:
        raise ValidationError("%s نمی‌تواند منفی باشد." % field)
    u = _normalize_unit(unit)
    if embedded:
        default = _normalize_unit("ریال")
        if u not in (default, "rial", "rials") and u != embedded:
            raise ValidationError(
                "واحد داخل مقدار با واحد ورودی متفاوت است؛ یکی را اصلاح کنید.")
        target = embedded
    elif u in ("تومان", "toman", "tomans"):
        target = "toman"
    elif u in ("ریال", "rial", "rials"):
        target = "rial"
    elif u in ("میلیون تومان", "million toman", "million tomans"):
        target = "million_toman"
    else:
        raise ValidationError("واحد %s باید ریال یا تومان باشد." % field)
    amount *= UNIT_MULTIPLIERS[target]
    if amount != amount.to_integral_value():
        raise ValidationError("%s باید به ریال صحیح تبدیل شود؛ مقدار اعشاری پذیرفته نیست." % field)
    return int(amount)


def _normalize_unit(unit):
    """Normalise a unit label without destroying the space (e.g. میلیون تومان)."""
    return " ".join(str(unit or "").split()).lower()


def from_rial(amount_rial, unit="تومان"):
    """Return a ``Decimal`` amount expressed in ``unit`` (exact, no rounding)."""
    n = to_rial_strict(amount_rial, "مبلغ ریالی", allow_negative=True)
    u = _normalize_unit(unit)
    if u in ("ریال", "rial", "rials"):
        return Decimal(n)
    if u in ("تومان", "toman", "tomans"):
        return Decimal(n) / Decimal(RIAL_PER_TOMAN)
    if u in ("میلیون تومان", "million toman", "million tomans"):
        return Decimal(n) / (Decimal(RIAL_PER_TOMAN) * Decimal(1000000))
    raise ValidationError("واحد نمایش نامعتبر است: %s" % unit)


def format_money(amount_rial, unit="تومان", local_digits=False):
    """Render integer Rials in the requested display unit, never rounding."""
    value = from_rial(amount_rial, unit)
    rendered = format(value, ",f")
    if "." in rendered:
        rendered = rendered.rstrip("0").rstrip(".")
    if local_digits:
        rendered = rendered.translate(str.maketrans(ASCII_DIGITS, PERSIAN_DIGITS))
    return "%s %s" % (rendered, unit)


def format_kg(value, unit="کیلوگرم", digits=3):
    """Format a weight without hiding precision."""
    amount = Decimal(str(value)).quantize(Decimal(1).scaleb(-digits))
    rendered = format(amount, ",f").rstrip("0").rstrip(".")
    return "%s %s" % (rendered, unit)


def parse_amount_to_rial(raw, unit="ریال"):
    """Backward compatible alias of :func:`to_rial` (legacy API name)."""
    return to_rial(raw, unit)


# --------------------------------------------------------------------------- #
# Day-number helpers (Howard Hinnant's civil calendar algorithms)
# --------------------------------------------------------------------------- #
def _days_from_civil(y, m, d):
    y -= 1 if m <= 2 else 0
    era = (y if y >= 0 else y - 399) // 400
    yoe = y - era * 400
    doy = (153 * (m + (-3 if m > 2 else 9)) + 2) // 5 + d - 1
    doe = yoe * 365 + yoe // 4 - yoe // 100 + doy
    return era * 146097 + doe - 719468


def _civil_from_days(z):
    z += 719468
    era = (z if z >= 0 else z - 146096) // 146097
    doe = z - era * 146097
    yoe = (doe - doe // 1460 + doe // 36524 - doe // 146096) // 365
    y = yoe + era * 400
    doy = doe - (365 * yoe + yoe // 4 - yoe // 100)
    mp = (5 * doy + 2) // 153
    d = doy - (153 * mp + 2) // 5 + 1
    m = mp + (3 if mp < 10 else -9)
    return (y + (1 if m <= 2 else 0), m, d)


# --------------------------------------------------------------------------- #
# Jalali (Shamsi) calendar
#
# The conversion is built on the Iranian 33 year leap cycle:
#   * a Jalali year has 365 days, 366 when it is a leap year;
#   * leap years satisfy (jy % 33) in {1, 5, 9, 13, 17, 22, 26, 30};
#   * the cycle was interrupted after 1403 AP, so years before 1404 also
#     treat residue 18 as leap (the "old cycle" 1371..1403);
#   * the epoch is anchored on 1403-01-01 == 2024-03-20 (Gregorian).
# Everything is pure integer arithmetic, works fully offline and the two
# directions are exact inverses of each other.
# --------------------------------------------------------------------------- #
_JALALI_LEAP_RESIDUES = (1, 5, 9, 13, 17, 22, 26, 30)
_JALALI_ANCHOR_JY = 1403
_JALALI_ANCHOR_ISO = "2024-03-20"
_JALALI_MONTH_LENGTHS = (31, 31, 31, 31, 31, 31, 30, 30, 30, 30, 30, 29)
_JALALI_MONTHS = ("فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
                  "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند")
JALALI_WEEKDAYS = ("شنبه", "یکشنبه", "دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه")
#: Supported Jalali year range (Borkowski's accuracy window for this rule).
JALALI_MIN_YEAR = 1300
JALALI_MAX_YEAR = 1500


def _is_jalali_leap(jy):
    """True when the Jalali year has 366 days.

    The Iranian 33 year cycle has eight leap years; the pattern repeats every
    33 years (e.g. 1375, 1379, ..., 1403, then 1408, 1412, ...).  The gap
    between 1403 and 1408 is the regular five year gap of the cycle.
    """
    return (jy % 33) in _JALALI_LEAP_RESIDUES


def jalali_leap(year):
    """True when the Jalali year has 366 days."""
    return _is_jalali_leap(int(year))


def _jalali_leap_count(upto):
    """Number of leap years in the range ``[1, upto]``."""
    if upto < 1:
        return 0
    total = 0
    for residue in _JALALI_LEAP_RESIDUES:
        if upto >= residue:
            total += (upto - residue) // 33 + 1
    return total


def _jalali_month_lengths(jy):
    lengths = list(_JALALI_MONTH_LENGTHS)
    if _is_jalali_leap(jy):
        lengths[11] = 30
    return lengths


def _jalali_day_number(jy, jm, jd):
    """Days since 1 Farvardin 1 AP (Jalali ordinal)."""
    lengths = _jalali_month_lengths(jy)
    day_of_year = sum(lengths[:jm - 1]) + jd
    return 365 * (jy - 1) + _jalali_leap_count(jy - 1) + day_of_year - 1


def _jalali_offset():
    anchor_ordinal = _jalali_day_number(_JALALI_ANCHOR_JY, 1, 1)
    anchor_civil = _days_from_civil(2024, 3, 20)
    return anchor_civil - anchor_ordinal


_JALALI_OFFSET = _jalali_offset()


def gregorian_leap(year):
    return (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)


def _days_in_gregorian_month(year, month):
    if month == 2:
        return 29 if gregorian_leap(year) else 28
    if month in (1, 3, 5, 7, 8, 10, 12):
        return 31
    return 30


def gregorian_to_jalali(gy, gm, gd):
    """Convert a Gregorian date to ``(jy, jm, jd)``."""
    gy, gm, gd = int(gy), int(gm), int(gd)
    if not 1 <= gm <= 12:
        raise ValidationError("ماه میلادی نامعتبر است.")
    if gd < 1 or gd > _days_in_gregorian_month(gy, gm):
        raise ValidationError("روز میلادی نامعتبر است.")
    ordinal = _days_from_civil(gy, gm, gd) - _JALALI_OFFSET
    jy = max(1, ordinal // 366 + 1)
    while _jalali_day_number(jy, 1, 1) > ordinal:
        jy -= 1
    while jy + 1 <= JALALI_MAX_YEAR + 1 and _jalali_day_number(jy + 1, 1, 1) <= ordinal:
        jy += 1
    lengths = _jalali_month_lengths(jy)
    remaining = ordinal - _jalali_day_number(jy, 1, 1)
    jm, jd = 12, lengths[11]
    for index, length in enumerate(lengths, 1):
        if remaining < length:
            jm, jd = index, remaining + 1
            break
        remaining -= length
    return jy, jm, jd


def jalali_to_gregorian(jy, jm, jd):
    """Convert a Jalali date to ``(gy, gm, gd)`` (exact inverse)."""
    jy, jm, jd = int(jy), int(jm), int(jd)
    if not JALALI_MIN_YEAR <= jy <= JALALI_MAX_YEAR:
        raise ValidationError("سال شمسی خارج از محدودهٔ پشتیبانی‌شده است "
                               "(%d تا %d)." % (JALALI_MIN_YEAR, JALALI_MAX_YEAR))
    if not 1 <= jm <= 12:
        raise ValidationError("ماه شمسی نامعتبر است.")
    lengths = _jalali_month_lengths(jy)
    if not 1 <= jd <= lengths[jm - 1]:
        raise ValidationError("روز شمسی نامعتبر است (%04d/%02d/%02d نیست)." % (jy, jm, jd))
    ordinal = _jalali_day_number(jy, jm, jd) + _JALALI_OFFSET
    return _civil_from_days(ordinal)


# --------------------------------------------------------------------------- #
# Dates
# --------------------------------------------------------------------------- #
def iso_today():
    return date.today().strftime("%Y-%m-%d")


def now_iso():
    """Local timestamp, second resolution (operational documents)."""
    return datetime.now().replace(microsecond=0).isoformat(sep=" ")


def normalize_iso_date(value, field="تاریخ"):
    """Validate and normalise an ISO ``YYYY-MM-DD`` date string."""
    if value is None or str(value).strip() == "":
        raise ValidationError("%s الزامی است." % field)
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, date):
        return value.strftime("%Y-%m-%d")
    text = str(value).strip()
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", text):
        raise ValidationError("%s باید با قالب YYYY-MM-DD وارد شود." % field)
    try:
        datetime.strptime(text, "%Y-%m-%d")
    except ValueError:
        raise ValidationError("%s تاریخ معتبری نیست." % field)
    return text


def to_jalali(iso_date):
    """Return ``(jy, jm, jd)`` for an ISO date string."""
    gy, gm, gd = (int(part) for part in normalize_iso_date(iso_date).split("-"))
    return gregorian_to_jalali(gy, gm, gd)


def from_jalali(jy, jm, jd):
    """Return the ISO date string for a Jalali date."""
    gy, gm, gd = jalali_to_gregorian(jy, jm, jd)
    return "%04d-%02d-%02d" % (gy, gm, gd)


def format_jalali(iso_date, with_weekday=False):
    """Human readable Jalali representation, e.g. ``1405/07/27``."""
    jy, jm, jd = to_jalali(iso_date)
    text = "%04d/%02d/%02d" % (jy, jm, jd)
    if with_weekday:
        iso = normalize_iso_date(iso_date)
        weekday = date(int(iso[0:4]), int(iso[5:7]), int(iso[8:10]))
        text = "%s %s" % (JALALI_WEEKDAYS[weekday.weekday()], text)
    return text


def format_jalali_long(iso_date):
    """Jalali representation including the month name, e.g. ``27 مهر 1405``."""
    jy, jm, jd = to_jalali(iso_date)
    return "%d %s %d" % (jd, _JALALI_MONTHS[jm - 1], jy)


def parse_jalali(text, field="تاریخ شمسی"):
    """Parse ``1405/07/27`` (also ``1405-7-27`` or ``14050727``) to ISO."""
    raw = normalize_digits(text)
    raw = raw.replace(".", "/").replace("-", "/").replace(" ", "/")
    parts = [p for p in raw.split("/") if p]
    if len(parts) != 3:
        raise ValidationError("%s باید به شکل 1405/07/27 وارد شود." % field)
    try:
        jy, jm, jd = (int(p) for p in parts)
    except ValueError:
        raise ValidationError("%s معتبر نیست." % field)
    return from_jalali(jy, jm, jd)


def jalali_month_range(jy, jm):
    """Return ``(start_iso, end_iso)`` of a Jalali month."""
    start = from_jalali(jy, jm, 1)
    if jm == 12:
        end = from_jalali(jy + 1, 1, 1)
    else:
        end = from_jalali(jy, jm + 1, 1)
    last = date.fromisoformat(end) - timedelta(days=1)
    return start, last.strftime("%Y-%m-%d")


def jalali_year_range(jy):
    """Return ``(start_iso, end_iso)`` of a Jalali year."""
    return from_jalali(jy, 1, 1), from_jalali(jy, 12, _jalali_month_lengths(jy)[11])


# --------------------------------------------------------------------------- #
# Codes and identifiers
# --------------------------------------------------------------------------- #
def make_code(prefix, counter, width=6):
    """Build a stable, human readable document code, e.g. ``SHP-000123``."""
    return "%s-%0*d" % (prefix, width, int(counter))


def next_code(con, table, column, prefix, width=6, where=None, params=()):
    """Allocate the next ``prefix-NNNNNN`` code for ``table`` atomically."""
    sql = "SELECT COALESCE(MAX(%s), '') FROM %s" % (column, table)
    if where:
        sql += " WHERE " + where
    current = con.execute(sql, params).fetchone()[0] or ""
    try:
        number = int(str(current).rsplit("-", 1)[-1]) + 1
    except ValueError:
        number = 1
    return make_code(prefix, number, width)
