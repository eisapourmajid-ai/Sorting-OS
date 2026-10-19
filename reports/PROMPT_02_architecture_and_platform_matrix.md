# گزارش پایان Prompt 02 — تصمیم معماری و ماتریس سازگاری

- Prompt ID / Title: 02 — architecture decision and platform matrix
- Status: **PASS**
- Branch / base SHA / new commit SHA: `arena/db7e4de8-sorting-os` / `429e778` / (این commit)
- Requirements covered (IDs): NFR-OFF-001, NFR-OFF-002, NFR-OFF-003, FIN-MONEY-001..012, FIN-CORE-001..040, RPT-FIN-01..10, RPT-OPS-01..03 (سطح طراحی/پیاده‌سازی — نه VERIFIED ON TARGET)
- Files changed and purpose:
  - `docs/architecture/ADR-0001-platform-and-runtime.md` — تصمیم معماری: Python 3.8+ / Tkinter / SQLite، چهار لایهٔ اجباری (core / persistence / services / ui / reporting)، قواعد پول و تراکنش، مقایسهٔ گزینه‌ها با هزینهٔ مهاجرت و ریسک.
  - `docs/architecture/platform-compatibility-matrix.md` — ماتریس سازگاری با وضعیت واقعی هر قلم (VERIFIED / TESTED / DESIGNED / NOT VERIFIED ON TARGET OS / NOT RUN).
- Database migrations / data impact: بدون تغییر داده (این مرحله تصمیم معماری است). قواعد مهاجرت نسخه‌دار به‌عنوان بند صریح ADR ثبت شد.
- Security / permissions / audit impact: بدون تغییر؛ قاعدهٔ «هیچ تماس شبکه‌ای در runtime» و «دادهٔ عملیاتی وارد Git نشود» در ADR تثبیت شد.
- Offline / OS / print impact: چاپ و Windows 7 صریحاً `NOT VERIFIED ON TARGET OS` ثبت شد؛ علت (نبود سیستم‌عامل هدف و نبود tkinter) مکتوب است.
- Commands actually run:
  - `python3 -m unittest discover -s tests` (پوشهٔ `desktop`) → ۱۲۳ تست، OK
  - `python3 scripts/check-doc-links .` → ۳۶ لینک محلی، ۰ لینک شکسته
- Test results: **passed 123 / failed 0 / not run: GUI, Windows 7, installer** (`NOT RUN`)
- Build result: `py_compile` OK؛ ساخت EXE `NOT RUN` (PyInstaller در این محیط نصب نیست)
- Evidence paths: `docs/architecture/ADR-0001-platform-and-runtime.md`، `docs/architecture/platform-compatibility-matrix.md`، `reports/BASELINE_EVIDENCE.md`
- Known limitations / open decisions:
  - ADR-002 (روش packaging و آزمون W7) — Open
  - ADR-003 (تأیید رسمی تقویم شمسی) — Provisional
  - ADR-004 (سیاست نسخهٔ schema) — Provisional
  - هیچ سازگاری‌ای با Windows 7 ادعا نشده است.
- Rollback plan: حذف دو فایل مستند (هیچ کد/داده‌ای تغییر نکرده) ⇒ `git revert <sha>` کافی است.
- Is the next prompt unblocked? **بله** — شناسه‌های نیازمندی برای traceability در Prompt 03 ساخته می‌شوند.

### جمع‌بندی تصمیم‌ها

| تصمیم | وضعیت |
|---|---|
| پلتفرم: Python 3.8+ / Tkinter / SQLite (بدون تغییر فناوری) | Accepted |
| چهار لایهٔ اجباری و جداسازی UI از دامنه | Accepted |
| مبنای پول: `int` ریال، `Decimal` فقط در مرز، ممنوعیت float | Accepted (TECH-001) |
| موتور تقویم شمسی آفلاین درون‌برنامه‌ای | Accepted (TECH-002) / تأیید رسمی: Pending |
| migration نسخه‌دار + تراکنش + backup/restore | Accepted (TECH-004) |
| «سازگار با Windows 7» | مجاز نیست تا آزمون واقعی (ADR-002 باز) |
