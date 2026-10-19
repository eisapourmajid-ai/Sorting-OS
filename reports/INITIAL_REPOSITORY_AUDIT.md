# گزارش ممیزی مخزن و نقشه وضعیت — Prompt 00

- **Prompt ID / Title:** Prompt 00 — مبنای شروع و ممیزی مخزن (Repository audit and state map)
- **Status:** PASS
- **Mode:** فقط‌خواندنی؛ هیچ فایل اپلیکیشنی تغییر نکرده است.
- **Branch / base SHA / new commit SHA:** `arena/db7e4de8-sorting-os` / `82ac51ae91ab745f8a06b1565cb67708b28cc704` / ثبت‌شده در گزارش پایانی هر commit
- **Base date:** 2026-10-19 (UTC)
- **Audit type:** بازرسی دستی checkout واقعی + اجرای واقعی تست‌ها + خواندن GitHub API

---

## ۱. خلاصه

- مخزن `eisapourmajid-ai/Sorting-OS` در شاخه `main` فقط شامل یک فایل `README.md` با ۱۳ بایت محتوا بود (`# Sorting-OS`). هیچ کد، تست، CI یا سند فنی در GitHub وجود نداشت.
- بستهٔ مهندسی `SORTING_OS_FINAL_ENGINEERING_PACKAGE_2026-10-18.zip` در مخزن `eisapourmajid-ai/mazand-fos` قرار داشت؛ فایل از طریق GitHub API (blob) دانلود و در این مخزن استخراج شد. اکنون سورس اجرایی MVP، ۳۶ پرامپت، اسناد مرجع مالی و قراردادها در این checkout موجود است.
- MVP اجراشده: `desktop/` با Python/Tkinter + SQLite (فقط کتابخانهٔ استاندارد). خط پایهٔ تست: **۱۷ تست، همه PASS**.
- گزارش‌های مالی از journal lines واقعی تولید می‌شوند و float در آن‌ها وجود ندارد؛ اما اتصال خودکار invoice/settlement/bank/check به دفترکل، تقویم شمسی، بستن دوره و گردش کامل انبار/سورتینگ/ارسال هنوز پیاده‌سازی نشده‌اند.

## ۲. وضعیت شاخه و گیت (شواهد زنده)

| مورد | مقدار واقعی |
|---|---|
| شاخهٔ کاری | `arena/db7e4de8-sorting-os` |
| commit پایه | `82ac51ae91ab745f8a06b1565cb67708b28cc704` («Initial commit») |
| شاخه‌های remote | `main` (تنها شاخهٔ remote) |
| PRهای باز | ندارد |
| Issueها | ندارد |
| Releaseها | ندارد |
| وضعیت worktree در شروع | clean (`git status` → `nothing to commit, working tree clean`) |
| دادهٔ واقعی/کلید/توکن | یافت نشد؛ `.env.example` تنها فایل پیکربندی و فاقد secret است |

**منبع:** `git status`, `git show-ref`, `gh api repos/eisapourmajid-ai/Sorting-OS`, `gh api .../branches`, `gh issue list`, `gh release list` — همه در 2026-10-19 اجرا شدند.

## ۳. فهرست واقعی فایل‌ها (پس از استخراج بسته)

| مسیر | نوع | نقش |
|---|---|---|
| `desktop/main.py` | کد | پوستهٔ Tkinter RTL؛ ورودی برنامه (`python desktop/main.py`) |
| `desktop/database.py` | کد | persistence عملیاتی SQLite (schema v1): اشخاص، محموله، باسکول، فاکتور، audit_log |
| `desktop/accounting_core.py` | کد | هستهٔ حسابداری دوبل: واحد ریال، دفترکل، تراز آزمایشی، ترازنامه، سود و زیان، جریان نقدی، نسبت‌ها |
| `desktop/tests/test_database.py` | تست | ۵ تست persistence |
| `desktop/tests/test_accounting_core.py` | تست | ۱۲ تست هستهٔ مالی |
| `desktop/run_windows.bat`, `desktop/build_windows.bat` | اسکریپت | اجرا و build روی Windows |
| `docs/financial/*` (۴ سند) | سند مرجع | هستهٔ حسابداری، سیاست ریال/تومان، گزارش‌ها، سناریوهای پذیرش |
| `docs/01..15` | سند مرجع | گردش کار، مدل داده، قواعد صافی، طراحی UI، معماری Win7، گزارش/چاپ، امنیت، تست، فازها |
| `contracts/*` (۷ فایل) | قرارداد | آستانهٔ پذیرش، وضعیت پیاده‌سازی، invariantهای داده، release gates |
| `prompts/00..35` (۳۶ فایل) | پرامپت | نقشهٔ اجرای مرحله‌ای |
| `MASTER_PROMPT_FOR_AGENT_FA.md` | قانون مادر | سلسله‌مراتب تصمیم، گاردریل، تعاریف وضعیت |
| `PROJECT_SPEC.md` | سند | چشم‌انداز و دامنهٔ نسخه |
| `.github/workflows/python-tests.yml` | CI | py_compile + unittest روی 3.8/3.11/3.12 |
| `reports/` | خروجی ممیزی | این گزارش و شواهد baseline |

## ۴. فناوری‌ها، entry point و وابستگی‌ها

- **زبان/-runtime:** Python 3.8+ (سورس با `from __future__ import annotations` و بدون سینتکس جدیدتر از 3.8 نوشته شده).
- **GUI:** Tkinter (`tkinter`, `tkinter.ttk`, `tkinter.messagebox`, `tkinter.filedialog`).
- **ذخیره‌سازی:** SQLite با `PRAGMA foreign_keys=ON`، تراکنش‌های صریح `BEGIN IMMEDIATE`.
- **وابستگی runtime:** هیچ — `desktop/requirements.txt` عمداً خالی است. شبکه در runtime لازم نیست.
- **Entry point:** `desktop/main.py::main()`؛ `desktop/run_windows.bat` روی Windows، `python desktop/main.py` در سایر محیط‌ها.
- **Test entry point:** از پوشهٔ `desktop`: `python -m unittest discover -s tests -v`.
- **Build:** `desktop/build_windows.bat` (فرآیند build را آغاز می‌کند؛ گواهی سازگاری Windows 7 نیست).

## ۵. جدول «موجود / ناقص / غایب / اثبات‌نشده»

| ماژول | وضعیت | مسیر واقعی سورس | تست قابل اجرا | گیت بعدی |
|---|---|---|---|---|
| پوستهٔ دسکتاپ RTL | ناقص | `desktop/main.py` | ندارد (GUI) | 05, 24 |
| ذخیره‌سازی محلی SQLite | موجود؛ framework مهاجرت ناقص | `desktop/database.py` | `tests/test_database.py` | 06 |
| اشخاص (master) | ناقص (نقش‌ها در ستون متنی) | `desktop/database.py::save_party` | `test_party_create_and_duplicate_national_id_rejected` | 07 |
| تطبیق/ادغام اشخاص | غایب (فقط preview CSV) | `database.py::import_parties_preview` | `test_import_preview_never_merges_by_name` | 08 |
| محصول/درجه/بسته‌بندی | غایب (نام محصول آزاد) | `shipments.product_name` | ندارد | 09 |
| باسکول | ناقص (یک محموله) | `database.py::create_weighing` | `test_weighing_net_and_gross_tare_validation` | 10 |
| محموله و lifecycle | ناقص | `database.py::create_shipment` | `test_shipment_requires_active_party_and_accepts_zero_weight` | 11 |
| سورتینگ و تراز جرم | غایب | — | — | 12 |
| دفتر انبار/مکان/رزرو | غایب | — | — | 13 |
| ارسال/حواله/حمل | غایب | — | — | 14 |
| خرید و هزینه | غایب | — | — | 15 |
| فاکتور فروش | ناقص (سربرگ، مبلغ `REAL`) | `database.py::create_invoice` | `test_invoice_and_dashboard_aggregate` | 16 |
| دفترکل دوبل | موجود (هستهٔ جدید) | `desktop/accounting_core.py` | ۱۲ تست `test_accounting_core.py` | 17 |
| گردش حساب طرف (تفصیلی) | ناقص (`party_ref` روی ردیف بدون مانده تفصیلی) | `accounting_core.account_ledger` | — | 17 |
| صافی/تسویه | غایب | — | — | 18 |
| بانک و تطبیق گردش | غایب (فقط سند مرجع) | — | — | 19 |
| چک | غایب | — | — | 20 |
| import/export جامع | ناقص (۴ CSV ثابت) | `database.py::export_rows` | `test_csv_export_headers` | 21 |
| گزارش‌ساز و KPI | ناقص | `database.py::counts` | `test_invoice_and_dashboard_aggregate` | 22 |
| طراح چاپ | غایب | — | — | 23 |
| UI design system/RTL | ناقص | `main.py::_configure_style` | ندارد | 24 |
| کاربر/مجوز/audit | ناقص (audit log بدون کاربر/مجوز) | `database.py::audit` | ندارد | 25 |
| backup | ناقص (کپی فایل در UI) | `main.py::backup_db` | ندارد | 26 |
| آفلاین/Win7 | اثبات‌نشده | — | — | 27 |
| تست واحد | ناقص (۱۷ تست) | `desktop/tests/` | PASS در baseline | 28 |
| integration/E2E | غایب | — | — | 29 |
| کارایی/مقاوم‌بودن داده | غایب (تنها `UNIQUE(source_type,source_id)`) | `accounting_core.post_entry` | `test_duplicate_source_posting_is_rejected` | 30 |
| installer/release packaging | غایب (فقط bat) | `desktop/build_windows.bat` | — | 31 |
| مهاجرت داده تاریخی | غایب | — | — | 32 |
| پایلوت/UAT، RC، انتشار | غایب | — | — | 33–35 |

## ۶. ماتریس مالی (مستقل از UI)

| سطر | مسیر واقعی سورس | تست قابل اجرا | وضعیت | گیت بعدی |
|---|---|---|---|---|
| واحد پول integer ریال، بدون float | `accounting_core.parse_amount_to_rial`, `format_money` | `test_rial_toman_conversion_exact_and_persian_digits`, `test_internal_rial_amounts_never_silently_truncate` | موجود/TESTED | 21 (CSV base column) |
| دفترکل دوبل و تعادل سند | `accounting_core.post_entry` | `test_unbalanced_journal_rejected` | موجود/TESTED | 17 |
| یکتایی منبع (idempotency) | `journal_entries.UNIQUE(source_type,source_id)` | `test_duplicate_source_posting_is_rejected` | موجود/TESTED | 17 |
| برگشت با سند معکوس | `accounting_core.reverse_entry` | `test_reversal_creates_counter_entry_not_deletion` | موجود/TESTED | 17 |
| تراز آزمایشی | `accounting_core.trial_balance` | `test_post_and_trial_balance` | موجود/TESTED | 22 |
| ترازنامه | `accounting_core.balance_sheet` | `test_balance_sheet_and_income_statement` | موجود/TESTED | 22 |
| سود و زیان | `accounting_core.income_statement` | همان تست بالا | موجود/TESTED | 22 |
| جریان وجوه نقد (مدیریتی) | `accounting_core.cash_flow_statement` | `test_cash_flow_reconciles` | موجود/TESTED؛ نیازمند تأیید حسابدار (DEC-012) | 22 |
| نسبت‌ها | `accounting_core.ffinancial_ratios` | — | موجود/بدون تست اختصاصی؛ heuristic و «نیازمند تنظیم» | 22 |
| اتصال فاکتور/صافی/بانک/چک به دفترکل | — | — | **غایب** (مقدار `invoices.amount` از نوع `REAL` و بدون واحد مصوب) | 16–20 |
| صافی | — | — | **غایب** | 18 |
| تقویم شمسی | — | — | **غایب** (فقط ISO میلادی) | 27/05 |
| دادهٔ legacy | `invoices.amount REAL` | `test_legacy_invoice_does_not_auto_post_into_financial_reports` | مهاجرت/جمع با دفترکل ممنوع (DEC-013) | 32 |
| طبقه‌بندی جاری/غیرجاری | heuristic پیشوند کد در `financial_ratios` | — | ناقص | 22 |

## ۷. شواهد اجرایی این ممیزی

| فرمان | نتیجهٔ مشاهده‌شده |
|---|---|
| `git status` (شروع) | `nothing to commit, working tree clean` |
| `gh api repos/eisapourmajid-ai/Sorting-OS/contents` | تنها `README.md` (۱۳ بایت) |
| `gh api repos/eisapourmajid-ai/mazand-fos/contents` | `SORTING_OS_FINAL_ENGINEERING_PACKAGE_2026-10-18.zip` (۶۷۴٬۷۵۷ بایت) |
| `python3 -m unittest discover -s tests -v` (از `desktop/`) | `Ran 17 tests ... OK` |
| `python3 -c "import tkinter"` | `ModuleNotFoundError: No module named 'tkinter'` → GUI در این محیط **NOT RUN** |

## ۸. محدودیت‌ها و NOT VERIFIED

- **GUI:** در این محیط `tkinter` نصب نیست؛ هیچ ادعایی دربارهٔ اجرای واقعی UI یا چاپ نمی‌شود. وضعیت UI = `NOT RUN` در این محیط، `NOT VERIFIED ON TARGET OS` برای Windows 7.
- **Windows 7 SP1 x64:** هیچ آزمونی روی سیستم هدف انجام نشده → `NOT VERIFIED ON TARGET OS`.
- **EXE/Installer:** ساخته نشده → `NOT BUILT`.
- **مقادیر مالی legacy:** `invoices.amount` از نوع `REAL` و بدون واحد مصوب؛ طبق `MONEY_UNIT_POLICY_FA.md` جمع با دفترکل ممنوع است.
- **دسترسی:** فقط به `github.com`/`api.github.com`؛ شبکهٔ runtime برنامه اصلاً لازم نیست و آزمون نشد چون چنین مسیری در کد وجود ندارد.

## ۹. تصمیم‌های باز مؤثر بر ممیزی

DEC-001 تا DEC-014 طبق `docs/decision-log.md` همگی `Open` هستند. اثر مستقیم بر این ممیزی: مالکیت کالا (DEC-001/002)، مبنای درصد صافی (DEC-003)، ترتیب کمیسیون و کسورات (DEC-005)، کدینگ نهایی (DEC-011)، واحد دادهٔ تاریخی (DEC-013). تا زمانی که این تصمیم‌ها `Accepted` نشوند، قابلیت‌های وابسته با `BLOCKED`/feature-flag ارائه می‌شوند و فرمول تجاری جعلی ساخته نمی‌شود.

## ۱۰. مرحلهٔ بعد

`Prompt 01 — ثبت خط مبنا و تکرارپذیری` (گزارش: `reports/BASELINE_EVIDENCE.md`).
