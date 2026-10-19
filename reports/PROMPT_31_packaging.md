# گزارش پایان Prompt 31 — بسته‌بندی و انتشار

- Prompt ID / Title: 31 — installer and release packaging
- Status: **PARTIAL**
- Branch / base SHA / new commit SHA: `arena/db7e4de8-sorting-os` / `6806419` / (این commit)
- Requirements covered (IDs): FR-REL-001، NFR-OFF-003 (بسته‌بندی آفلاین)، ADR-0002
- Files changed and purpose:
  - `scripts/build_release.py` — ساخت bundle نسخه‌دار: کپی سورس + مستندات + `run_app.bat` +
    `RELEASE_NOTES.md` + `SBOM.md` + `SHA256SUMS.txt` + فایل ZIP. گزینهٔ `--exe` تلاش برای ساخت
    EXE با PyInstaller دارد و در نبود آن **صریحاً `NOT RUN` گزارش می‌کند**.
  - `desktop/sorting_os.spec` — مشخصات PyInstaller (بدون دارایی شبکه‌ای، بدون دادهٔ کاربر).
  - `desktop/run_app.py` — entry point مشترک سورس و EXE.
- Database migrations / data impact: بدون تغییر داده. دادهٔ کاربر هرگز داخل bundle نیست
  (مسیر داده بیرون از نصب است — `sorting_os/paths.py`).
- Security / permissions / audit impact: بدون تغییر؛ SBOM تصریح می‌کند که هیچ وابستگی زمان
  اجرای شخص ثالثی وجود ندارد (فقط کتابخانهٔ استاندارد).
- Offline / OS / print impact: بستهٔ portable کاملاً آفلاین است؛ EXE/نصب‌کننده `NOT RUN`.
- Commands actually run:
  - `python3 scripts/build_release.py` → bundle در `dist/SORTING-OS-0.2.0/`، آرشیو ZIP با
    `sha256 = 8691099397aa712cac3edd3bafbcabe9173109be97baa390d4df461897c8f183`، اندازهٔ ۲۸۵٬۳۶۷ بایت،
    و پیام `EXE: NOT RUN — use --exe on a machine that has PyInstaller installed`.
  - `cd desktop && python3 -m unittest discover -s tests` → ۱۹۰ تست، OK
- Test results: passed 190 / failed 0 / not run: EXE، نصب‌کننده، نصب روی سیستم تمیز
- Build result: **portable bundle ساخته شد**؛ **EXE و installer ساخته نشدند** (`NOT RUN`).
- Evidence paths: `dist/SORTING-OS-0.2.0/` (خروجی محلی؛ در Git نیست)، `scripts/build_release.py`،
  `desktop/sorting_os.spec`
- Known limitations / open decisions:
  - ADR-002 (روش نهایی packaging و آزمون W7) — باز.
  - "نصب/حذف/به‌روزرسانی روی سیستم تمیز" و "بدون نیاز به admin" آزموده نشده‌اند.
  - checksum باید در زمان انتشار نهایی دوباره تولید شود (commit نهایی).
- Rollback plan: `git revert <sha>`؛ خروجی `dist/` حذف‌شدنی است (در `.gitignore`).
- Is the next prompt unblocked? **بله** (Pilot/UAT) — با این شرط که این مرحله «partial» باقی
  بماند و هیچ ادعای «نصب‌کننده آماده» داده نشود.

### نکتهٔ صداقت
بستهٔ ساخته‌شده یک **bundle پرتابل** است، نه نصب‌کننده. هیچ EXE یا نصب‌کننده‌ای ساخته نشده و
هیچ نصبی روی سیستم تمیز آزموده نشده است؛ بنابراین Gate G همچنان **FAIL** می‌ماند.
