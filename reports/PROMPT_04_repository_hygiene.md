# گزارش پایان Prompt 04 — پاکیزگی مخزن و دستورهای توسعه

- Prompt ID / Title: 04 — repository hygiene and agent instructions
- Status: **PASS**
- Branch / base SHA / new commit SHA: `arena/db7e4de8-sorting-os` / `429e778` / (این commit)
- Requirements covered (IDs): NFR-OFF-001 (به‌عنوان گیت پاکیزگی)، DEC-013/DEC-014 (قواعد داده و مجوز)،
  کل ردیف‌های traceability (ساختار مستندات به‌عنوان شواهد)
- Files changed and purpose:
  - `scripts/check-doc-links` — ابزار واقعی بررسی لینک‌های محلی Markdown (case-sensitive) به‌همراه
    بررسی مسیرهای بحرانی مخزن؛ خروجی `BROKEN`/`MISSING` و کد خروج ۱ در صورت خطا. هیچ سندی را
    حذف یا ویرایش نمی‌کند.
  - `scripts/required-paths.txt` — فهرست ۴۰ مسیر بحرانی مخزن (README، اسناد مالی، ADRها، هستهٔ
    `sorting_os`، آزمون‌ها) که باید واقعی باشند.
  - `README.md` — وضعیت صادقانهٔ به‌روز، ساختار جدید مخزن، نقشهٔ اسناد، فرمان‌های اجرا و آزمون،
    تصریح `NOT RUN`/`NOT VERIFIED ON TARGET OS`.
  - `CONTRIBUTING.md` — گیت‌های محلی پیش از commit (تست، چک لینک، py_compile)، انضباط مرحله‌ای،
    پیوند به traceability و decision-log.
  - `CHANGELOG.md` — ثبت تغییرات با برچسب `[Prompt XX]`.
  - `.github/workflows/python-tests.yml` — افزودن مرحلهٔ «Documentation link and path check».
- Database migrations / data impact: بدون تغییر داده.
- Security / permissions / audit impact: `.gitignore` دست‌نخورده باقی ماند (فایل‌های `*.sqlite3`،
  `*.csv`، `exports/`، `.env` و کلیدها همچنان مستثنا هستند)؛ هیچ دادهٔ واقعی وارد Git نشد — بررسی با
  `git status` و جست‌وجوی فایل‌های داده در index.
- Offline / OS / print impact: بدون تغییر.
- Commands actually run:
  - `python3 scripts/check-doc-links .` → `checked 36 local links and 40 required paths … 0 broken links`
    (پس از افزودن `CHANGELOG.md`؛ `desktop/sorting_os/ui/app.py` هنوز در Prompt 24 ساخته می‌شود و
    تا آن زمان به‌درستی `MISSING` گزارش می‌شود)
  - `python3 -m unittest discover -s tests` → ۱۲۳ تست، OK
  - `git status --porcelain` → بدون فایل داده/خروجی بانکی
- Test results: passed 123 / failed 0 / not run: GUI
- Build result: `py_compile` OK
- Evidence paths: `scripts/check-doc-links`، `scripts/required-paths.txt`، `reports/BASELINE_EVIDENCE.md`
- Known limitations / open decisions:
  - هیچ سند مرجعی حذف نشد؛ تنها README/CONTRIBUTING به‌روزرسانی شدند.
  - محیط Windows 7 و نصب‌کننده همچنان `NOT RUN`/`NOT VERIFIED ON TARGET OS`.
  - Issue/PR templateهای موجود (`.github/ISSUE_TEMPLATE/*`، `.github/PULL_REQUEST_TEMPLATE.md`) بدون
    تغییر باقی ماندند چون سند مرجع هستند.
- Rollback plan: `git revert <sha>` (مستندات و اسکریپت جدید؛ بدون اثر روی داده/کد اجرایی).
- Is the next prompt unblocked? **بله** — پوستهٔ برنامه و coding standards مرحلهٔ بعدی است.
