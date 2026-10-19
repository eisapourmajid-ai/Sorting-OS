# Changelog — SORTING OS

قالب: Keep a Changelog. نسخه‌ها با تاریخ ISO و برچسب `[Prompt XX]` مشخص می‌شوند تا مسیر اجرای
مرحله‌ای (۰۰ تا ۳۵) قابل ردیابی بماند.

## [Unreleased]

### Added

- هستهٔ چهارلایهٔ `desktop/sorting_os/` (ADR-0001): `core.py` (سیاست پول و تقویم شمسی آفلاین)،
  `db.py` (تراکنش/مهاجرت/audit)، `migrations.py` (MIGRATION_1 و MIGRATION_2)، `services/` (۱۳ سرویس
  دامنه) و `ui/app.py` (پوستهٔ فارسی/RTL). `[Prompt 05..24]`
- مجموعهٔ آزمون headless در `desktop/tests/`: **۱۹۰ آزمون** (۱۷ پایه + ۱۷۳ جدید) شامل تست‌های invariant
  مالی/انبار، import/export، بانک/چک، امنیت، backup/restore، گزارش‌ها، دورهٔ مالی، property
  (دادهٔ تصادفی قطعی)، سناریوهای پذیرش A–H، کارایی و آفلاین. `[Prompt 28..30]`
- `desktop/sorting_os/services/migration.py` — مهاجرت دادهٔ تاریخی با واحد صریح، preview،
  خطای ردیف، reconciliation و idempotency. `[Prompt 32]`
- `scripts/build_release.py` — ساخت بستهٔ پرتابل نسخه‌دار با SBOM، release notes و SHA256. `[Prompt 31]`
- `docs/release/UAT_PLAN_FA.md`، `reports/RELEASE_CANDIDATE_REPORT.md` (توصیهٔ NO-GO) و
  `docs/HANDOVER_FA.md`. `[Prompt 33..35]`
- `docs/architecture/ADR-0001-platform-and-runtime.md` و `docs/architecture/platform-compatibility-matrix.md`
  (ماتریس سازگاری با وضعیت واقعی هر قلم). `[Prompt 02]`
- `docs/requirements-traceability.csv` (۸۴ نیازمندی با وضعیت و سطح شواهد) و `docs/open-decisions.md`. `[Prompt 03]`
- `scripts/check-doc-links` (بررسی لینک‌های محلی و مسیرهای بحرانی اسناد) و `scripts/required-paths.txt`. `[Prompt 04]`
- `CHANGELOG.md`. `[Prompt 04]`

### Changed

- `desktop/accounting_core.py` اکنون توابع پول را از `sorting_os.core` می‌گیرد (single source of truth) و
  `initialize_schema()`/`ACCOUNTING_SCHEMA_SQL` را صادر می‌کند. `[Prompt 05]`
- `desktop/sorting_os/services/ledger.py` فقط روی خطوط حساب‌های دریافتنی/پرداختنی `party_ref` می‌نویسد
  (ماندهٔ طرف از دفترکل درست بازسازی می‌شود). `[Prompt 17, ADR-005]`
- `services/settlement.py`: مبنای محاسبه، مبلغ خالص اعلام‌شده است و کمیسیون/اضافه/کسر پس از آن اعمال
  می‌شود. `[Prompt 18]`
- `services/exchange.py`: نگاشت پیش‌فرض ستون‌های فارسی/انگلیسی (بدون نیاز به نگاشت دستی) به‌علاوهٔ
  نگاشت صریح. `[Prompt 21]`
- `services/periods.py`: سود دوره بستانکار (و زیان بدهکار) به ۳۱۰۰ منتقل می‌شود و سند بستن همیشه
  متوازن است. `[Prompt 17]`
- `.github/workflows/python-tests.yml` اکنون ساختار جدید و چک لینک اسناد را هم می‌آزماید. `[Prompt 04]`

### Fixed

- خطای `HAVING clause on a non-aggregate query` در گزارش دریافتنی طرف حساب (به subquery بازنویسی شد).
- گزارش دریافتنی سنی اکنون وصولات را FIFO به فاکتورها تخصیص می‌دهد و مبلغ وصول‌نشده را جدا
  گزارش می‌کند (`receipts-fifo-v1`، موقت تا تأیید مالی — DEC-015).
- شمارهٔ ردیف توزین/کسری/ضایعات در سورتینگ از روی خطوط محاسبه می‌شود (پارامتر فقط «پیش‌فرض» است و
  تناقض با خطوط ⇒ `ValidationError`).
- فقط خطوط `output` به موجودی انبار وارد می‌شوند؛ ضایعات/افت سند موجودی نمی‌سازند.
- بازیابی از backup خراب با `ConflictError` رد می‌شود (به‌جای خطای خام `sqlite3`).

### Known limitations / Not verified

- رابط گرافیکی: `NOT RUN` در این محیط (tkinter نصب نیست).
- بستهٔ EXE و نصب‌کننده: `NOT RUN` (PyInstaller/NSIS در دسترس نیست) — فقط bundle پرتابل ساخته شد.
- Windows 7 SP1 x64: `NOT VERIFIED ON TARGET OS`.
- ساخت EXE/نصب‌کننده: `NOT RUN`.
- تصمیم‌های تجاری باز (مدل کسب‌وکار، درصد صافی، بهای تمام‌شده، کدینگ نهایی، سال مالی،
  طبقه‌بندی جریان نقد، واحد دادهٔ تاریخی) — فهرست در `docs/open-decisions.md`.
