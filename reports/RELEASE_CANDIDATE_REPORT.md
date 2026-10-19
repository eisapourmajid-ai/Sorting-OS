# گزارش Release Candidate — SORTING OS 0.2.0

- مرجع: Prompt 34 — release candidate hardening
- شاخه: `arena/db7e4de8-sorting-os`
- base commit: `82ac51a` (Initial commit) — همهٔ تغییرات روی شاخهٔ feature
- تاریخ: 2026-10-19
- **توصیه: NO-GO برای انتشار production** (دلیل در بند ۶)

## ۱) خلاصهٔ وضعیت

| قلم | وضعیت |
|---|---|
| تست‌های headless | **۲۰۹ تست، همه PASS** (۱۷ legacy + ۱۹۲ جدید) — به‌روزرسانی 2026-10-19 پس از DEC-017 |
| آفلاین‌بودن | PASS با آزمون (تحلیل ایستا + جریان کامل با `socket` مسدود) |
| بستهٔ portable | PASS — `dist/SORTING-OS-0.2.0.zip` با SBOM و SHA256 (بازساخت 2026-10-19 پس از DEC-017: sha256 `9868e26129dfb378af81dccb940a6face97fba8e085d6c69632983da3ea29edd`، ۳۰۲٬۵۴۳ بایت؛ `EXE: NOT RUN`) |
| EXE (PyInstaller) | **NOT RUN** — PyInstaller در این محیط نصب نیست |
| نصب‌کننده (NSIS/Inno) | **NOT RUN** — ابزار موجود نیست |
| Windows 7 SP1 x64 | **NOT VERIFIED ON TARGET OS** |
| رابط گرافیکی | **NOT RUN** — tkinter در این محیط نصب نیست |
| تصمیم‌های تجاری | **۱۶ تصمیم باز** (`docs/open-decisions.md`) |

## ۲) RC manifest

| قلم | مقدار |
|---|---|
| نام | SORTING-OS 0.2.0 (portable bundle) |
| منبع | شاخهٔ `arena/db7e4de8-sorting-os` |
| commit | (در زمان ساخت bundle با `git rev-parse --short HEAD` ثبت می‌شود) |
| runtime هدف | Python 3.8+ (مرجع توسعه: 3.11.2) |
| وابستگی زمان اجرا | فقط کتابخانهٔ استاندارد (بدون وابستگی شخص ثالث) |
| مسیر داده | `%LOCALAPPDATA%\SortingOS` (Windows) / `$XDG_DATA_HOME/sorting-os` (POSIX) |
| schema | نسخهٔ ۲ (`schema_meta`) |
| artifact | `dist/SORTING-OS-0.2.0.zip` + `SHA256SUMS.txt` + `SBOM.md` + `RELEASE_NOTES.md` |
| فرمان ساخت | `python3 scripts/build_release.py` (`--exe` برای تلاش برای ساخت EXE) |

## ۳) شواهد آزمون (خروجی واقعی)

- `cd desktop && python3 -m unittest discover -s tests` → `Ran 209 tests … OK` (2026-10-19، پس از DEC-017)
- `python3 scripts/check-doc-links .` → ۰ لینک شکسته، ۰ مسیر بحرانی مفقود
- `python3 -m py_compile …` → OK
- اندازه‌گیری کارایی (Prompt 30): ۱۰۰ posting = ۰.۸۶s، ۳۰۰ گردش انبار = ۰.۴۸s،
  گزارش مالی = ۰.۰۱s، replay = ۰.۰۳s (روی محیط توسعه؛ اندازه‌گیری روی سیستم هدف لازم است)
- آزمون‌های سناریویی A–H (`tests/test_end_to_end.py`) → PASS

## ۴) وضعیت گیت‌های انتشار (`contracts/RELEASE_GATES_FA.md`)

| Gate | وضعیت | توضیح |
|---|---|---|
| A — Repository & baseline | **PASS** | ممیزی، خط مبنا، چک لینک اسناد، شواهد در `reports/` |
| B — Architecture & decisions | **PARTIAL** | ADR-0001 و DEC-017 (تخصیص درصد صافی) پذیرفته شده‌اند؛ ۱۷ تصمیم تجاری باز و مسدودکنندهٔ مسیرهای وابسته (از جمله معنای عددی درصد صافی، DEC-003) |
| C — Operational vertical slice | **TESTED (UI NOT RUN)** | محموله/توزین/سورتینگ/انبار/ارسال با آزمون؛ UI اجرا نشده |
| D — Finance | **PARTED/PARTIAL** | دفترکل، posting، صافی، بانک/چک با آزمون؛ مدل کسب‌وکار و کدینگ نهایی تأیید نشده |
| E — Import/export/print | **PARTIAL** | preview/idempotency/ادغام امن با آزمون؛ چاپ فیزیکی و A4/A5 آزموده نشده |
| F — Security & recovery | **PASS (tested)** | مجوز، audit با زنجیرهٔ هش، backup/restore آزموده‌شده |
| G — Quality & target OS | **FAIL** | تست‌ها پاس؛ **offline پاس**؛ نصب روی سیستم تمیز و OS هدف اجرا نشده |
| H — Release handover | **PARTIAL** | artifact نسخه‌دار + SHA256 + changelog + release notes موجود؛ **tag/release منتشر نشده** |

## ۵) خطاهای شناخته‌شده و محدودیت‌ها

1. رابط گرافیکی هرگز اجرا نشده ⇒ هیچ ادعایی دربارهٔ چیدمان RTL، فوکوس، modal یا هشدار
   تغییرات ذخیره‌نشده مجاز نیست.
2. Windows 7 SP1 x64 آزموده نشده ⇒ «سازگار با ویندوز ۷» ادعا نمی‌شود.
3. EXE/نصب‌کننده ساخته نشده ⇒ نصب آفلاین و «بدون نیاز به admin» آزموده نشده.
4. قواعد صافی، درصدها و بهای تمام‌شده فرضی/موقت هستند (DEC-003، DEC-006).
5. گزارش جریان نقد و نسبت‌ها «مدیریتی» هستند و تأیید حسابدار ندارند (DEC-012).
6. طبقه‌بندی جاری/غیرجاری کامل نیست (DEC-012).

## ۶) توصیهٔ Go/No-Go

**NO-GO برای انتشار production.** دلایل:

1. Gate G ناقص است: بدون آزمون روی سیستم‌عامل هدف و بدون نصب روی سیستم تمیز، انتشار
   «سازگار با Windows 7» از نظر شواهد ممکن نیست.
2. رابط کاربری اجرا نشده است؛ آسیب‌پذیری‌های عملیاتی UI (کلید اشتباه، از دست رفتن فرم)
   کشف نشده‌اند.
3. تصمیم‌های تجاری کلیدی امضا نشده‌اند؛ بدون آن‌ها posting در محیط واقعی قابل دفاع نیست.

**آنچه بدون ابهام قابل تحویل است:** بستهٔ portable به‌همراه سورس، مستندات، SBOM، checksum و
مجموعهٔ آزمون — به‌عنوان «نمونهٔ مهندسی/نسخهٔ ارزیابی»، نه محصول پرداخت‌شده.

## ۷) گام بعدی برای رسیدن به GO

1. اجرای چک‌لیست `docs/verification/target-os-verification.md` روی Windows 7 SP1 x64 و ثبت
   خروجی واقعی (۸ بند).
2. نصب PyInstaller روی ماشین build و ساخت EXE؛ آزمون اجرای EXE روی سیستم بدون Python.
3. امضای DEC-001..DEC-016 توسط مالک کسب‌وکار و حسابدار.
4. اجرای UAT با اپراتور واقعی طبق `docs/release/UAT_PLAN_FA.md` و ثبت لاگ issue.
5. ساخت دوبارهٔ bundle، به‌روزرسانی checksum، و تنها سپس tag و release.
