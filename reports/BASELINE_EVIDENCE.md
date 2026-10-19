# شواهد خط مبنا (Baseline) — Prompt 01

- **Prompt ID / Title:** Prompt 01 — ثبت خط مبنا و تکرارپذیری (Baseline build and test evidence)
- **Status:** PARTIAL
- **Branch / base SHA:** `arena/db7e4de8-sorting-os` / `82ac51ae91ab745f8a06b1565cb67708b28cc704`
- **دامنه:** فقط ثبت شواهد اجرای واقعی روی محیط در دسترس؛ بدون توسعهٔ قابلیت جدید.

> **چرا PARTIAL:** تست‌های واحد و syntax check با موفقیت واقعی اجرا شدند، اما آزمون رابط گرافیکی و آزمون روی سیستم‌عامل هدف (Windows 7 SP1 x64) در این محیط **قابل اجرا نبود** و طبق قاعدهٔ صداقت اجرایی، `NOT VERIFIED` ثبت می‌شود، نه pass.

---

## ۱. مشخصات محیط (واقعی)

| مؤلفه | مقدار |
|---|---|
| تاریخ اجرا | `Mon Oct 19 16:17:02 UTC 2026` |
| سیستم‌عامل | `Linux e2b.local 6.1.158+ #1 SMP Tue Dec 29 16:35:00 UTC 2026 x86_64 GNU/Linux` (کانتینر لینوکسی headless) |
| نسخهٔ Python | `Python 3.11.2` (`/usr/bin/python3`) |
| نسخهٔ SQLite | `3.40.1` (module version `2.6.0`) |
| pip | `pip 23.0.1` (نصب نشده — هیچ dependency خارجی لازم نیست) |
| Git | `git version 2.39.5` |
| Tkinter | **در دسترس نیست** → `ModuleNotFoundError: No module named 'tkinter'` |
| Display | ندارد (headless) |

## ۲. فرمان‌های اجراشده و خروجی واقعی

### ۲.۱ بررسی نحوی سورس (همان چیزی که CI اجرا می‌کند)

```
$ cd desktop && python3 -m py_compile main.py database.py accounting_core.py
py_compile OK
```

### ۲.۲ مجموعهٔ تست موجود

```
$ cd desktop && python3 -m unittest discover -s tests -v
test_balance_sheet_and_income_statement (test_accounting_core.AccountingCoreTests.test_balance_sheet_and_income_statement) ... ok
test_cash_flow_reconciles (test_accounting_core.AccountingCoreTests.test_cash_flow_reconciles) ... ok
test_duplicate_source_posting_is_rejected (test_accounting_core.AccountingCoreTests.test_duplicate_source_posting_is_rejected) ... ok
test_internal_rial_amounts_never_silently_truncate (test_accounting_core.AccountingCoreTests.test_internal_rial_amounts_never_silently_truncate) ... ok
test_invalid_fractional_rial_and_negative_rejected (test_accounting_core.AccountingCoreTests.test_invalid_fractional_rial_and_negative_rejected) ... ok
test_ledger_reversal_date_filter (test_accounting_core.AccountingCoreTests.test_ledger_reversal_date_filter) ... ok
test_legacy_invoice_does_not_auto_post_into_financial_reports (test_accounting_core.AccountingCoreTests.test_legacy_invoice_does_not_auto_post_into_financial_reports) ... ok
test_post_and_trial_balance (test_accounting_core.AccountingCoreTests.test_post_and_trial_balance) ... ok
test_reversal_creates_counter_entry_not_deletion (test_accounting_core.AccountingCoreTests.test_reversal_creates_counter_entry_not_deletion) ... ok
test_rial_toman_conversion_exact_and_persian_digits (test_accounting_core.AccountingCoreTests.test_rial_toman_conversion_exact_and_persian_digits) ... ok
test_unbalanced_journal_rejected (test_accounting_core.AccountingCoreTests.test_unbalanced_journal_rejected) ... ok
test_csv_export_headers (test_database.DatabaseTests.test_csv_export_headers) ... ok
test_import_preview_never_merges_by_name (test_database.DatabaseTests.test_import_preview_never_merges_by_name) ... ok
test_invoice_and_dashboard_aggregate (test_database.DatabaseTests.test_invoice_and_dashboard_aggregate) ... ok
test_party_create_and_duplicate_national_id_rejected (test_database.DatabaseTests.test_party_create_and_duplicate_national_id_rejected) ... ok
test_shipment_requires_active_party_and_accepts_zero_weight (test_database.DatabaseTests.test_shipment_requires_active_party_and_accepts_zero_weight) ... ok
test_weighing_net_and_gross_tare_validation (test_database.DatabaseTests.test_weighing_net_and_gross_tare_validation) ... ok

----------------------------------------------------------------------
Ran 17 tests in 0.281s

OK
```

**نتیجه:** ۱۷ تست، ۱۷ پاس، ۰ شکست، exit code = 0.

### ۲.۳ تلاش اجرای GUI (شکست محیطی، نه کد)

```
$ python3 -c "import tkinter"
ModuleNotFoundError: No module named 'tkinter'
```

`python3 desktop/main.py` اجرا نشد → رابط گرافیکی در این محیط **NOT RUN** است. علت: بستهٔ سیستم `python3-tk` در image موجود نیست و نصب آن نیازمند شبکه‌ای خارج از فهرست مجاز است.

### ۲.۴ build

- `desktop/build_windows.bat`: قابل اجرا نیست (Windows batch). روی لینوکس **NOT RUN**.
- خروجی EXE/installer: **NOT BUILT** — هیچ artifact اجراشده و آزموده‌شده‌ای وجود ندارد.

## ۳. وضعیت هر قابلیت در baseline

| قابلیت | وضعیت | شاهد |
|---|---|---|
| تبدیل ریال/تومان بدون float | TESTED | `test_rial_toman_conversion_exact_and_persian_digits` |
| سند متوازن و رد سند نامتوازن | TESTED | `test_unbalanced_journal_rejected` |
| idempotency منبع مالی | TESTED | `test_duplicate_source_posting_is_rejected` |
| برگشت با سند معکوس | TESTED | `test_reversal_creates_counter_entry_not_deletion` |
| تراز آزمایشی/ترازنامه/سود و زیان | TESTED | `test_post_and_trial_balance`, `test_balance_sheet_and_income_statement` |
| جریان نقدی (آشتی‌شونده) | TESTED | `test_cash_flow_reconciles` |
| عدم auto-post فاکتور legacy | TESTED | `test_legacy_invoice_does_not_auto_post_into_financial_reports` |
| persistence عملیاتی پایه | TESTED | ۵ تست `test_database.py` |
| رابط گرافیکی | **NOT RUN** | `tkinter` موجود نیست |
| چاپ | **NOT RUN** | نیازمند GUI/پرینتر |
| Windows 7 SP1 x64 | **NOT VERIFIED ON TARGET OS** | سیستم هدف در دسترس نیست |
| EXE/Installer | **NOT BUILT** | — |

## ۴. تکرارپذیری

- فرمان واحد بازتولید:
  ```
  cd desktop && python3 -m unittest discover -s tests -v
  ```
- تست‌ها دادهٔ مصنوعی و فایل SQLite موقت (`tempfile.TemporaryDirectory`) می‌سازند؛ هیچ دادهٔ واقعی، بانکی یا مشتری در repository یا خروجی تست وجود ندارد.
- هیچ فایل دیتابیس عملیاتی، backup یا export در Git اضافه نشده است (`.gitignore` این الگوها را پوشش می‌دهد).
- خط پایهٔ تست: **17 passed / 0 failed** — معیار بازگشت (regression gate) برای مراحل بعدی.

## ۵. نقص‌ها و محدودیت‌های کشف‌شده در baseline

1. `tkinter` در محیط CI/توسعه موجود نیست → تست GUI و هر تست UI باید `skipUnless` یا صرفاً بر پایهٔ سرویس (بدون Tk) نوشته شود.
2. `desktop/requirements.txt` عمداً خالی است؛ هر افزودن dependency جدید باید مجوز سازگار و بسته‌بندی آفلاین داشته باشد.
3. CI فقط `py_compile` سه فایل را بررسی می‌کند؛ با رشد ماژول‌ها باید کل بسته compile و test شود.
4. `invoices.amount` از نوع `REAL` است؛ تا تعیین واحد (DEC-013) نباید به دفترکل متصل یا جمع شود.

## ۶. مرحلهٔ بعد

`Prompt 02 — تصمیم معماری و ماتریس سازگاری` (بازبینی معماری + ثبت ADR/تصمیم‌های معماری به‌همراه شواهد baseline بالا).
