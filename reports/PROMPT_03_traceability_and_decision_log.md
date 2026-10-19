# گزارش پایان Prompt 03 — تطبیق نیازمندی‌ها و تصمیم‌های باز

- Prompt ID / Title: 03 — requirements traceability and decision log
- Status: **PASS**
- Branch / base SHA / new commit SHA: `arena/db7e4de8-sorting-os` / `429e778` / (این commit)
- Requirements covered (IDs): FIN-MONEY-001..012، FIN-CORE-001..040، RPT-FIN-01..10، RPT-OPS-01..03
  به‌علاوهٔ FR-PAR-001/002، FR-CAT-001، FR-OPS-001..004، FR-SAL-001، FR-SET-001، FR-BNK-001،
  FR-CHQ-001، FR-IMP-001، FR-PRT-001، FR-UI-001، FR-SEC-001، FR-BKP-001، NFR-OFF-001..003 (۸۴ ردیف)
- Files changed and purpose:
  - `docs/requirements-traceability.csv` — ستون‌های `Status` (implemented/partial/missing/blocked) و
    `EvidenceLevel` (DESIGNED/IMPLEMENTED/TESTED/VERIFIED ON TARGET) جدا، به‌علاوهٔ مالک، پرامپت،
    شواهد، شناسهٔ تست و تصمیم مرتبط.
  - `docs/open-decisions.md` — فهرست تصمیم‌های باز با «اثر تا زمان تصمیم» و وضعیت قابلیت وابسته
    (`PARTIAL` / `BLOCKED`).
  - `docs/decision-log.md` — افزودن DEC-015 (تخصیص وصولات) و DEC-016 (posting موقت صافی)، ارتقای
    ADR-001 به Accepted و افزودن ADR-005، و بخش «تصمیم‌های فنی پذیرفته‌شده» (TECH-001..006).
- Database migrations / data impact: بدون تغییر داده.
- Security / permissions / audit impact: بدون تغییر کد؛ الزام مجوز/audit به‌عنوان شناسه‌های
  FIN-CORE-037/038 ردیابی شدند.
- Offline / OS / print impact: NFR-OFF-002 (Windows 7) و NFR-OFF-003 (بسته‌بندی) صریحاً `missing` /
  `DESIGNED` ثبت شدند تا کسی آن‌ها را پیاده‌سازی‌شده فرض نکند.
- Commands actually run:
  - `python3 -m unittest discover -s tests` → ۱۲۳ تست، OK
  - `python3 scripts/check-doc-links .` → ۰ لینک شکسته
  - `python3 -c "..."` (تولید CSV) → ۸۴ ردیف، ۱۲ ستون
- Test results: passed 123 / failed 0 / not run: UI, W7
- Build result: `py_compile` OK
- Evidence paths: `docs/requirements-traceability.csv`، `docs/open-decisions.md`، `docs/decision-log.md`
- Known limitations / open decisions:
  - ۱۴ تصمیم تجاری/مالی باز (DEC-001..016) + ۳ تصمیم معماری باز (ADR-002..005)؛ فهرست و اثرشان در
    `docs/open-decisions.md`.
  - هیچ شناسه‌ای `VERIFIED ON TARGET` علامت نخورده است (تعریف اثبات: محیط هدف اجرا نشده).
  - FIN-CORE-027 (شناسنامهٔ کامل KPI) و FIN-CORE-037 (فیلتر مجوز در UI) `partial` باقی ماندند.
- Rollback plan: `git revert <sha>` (فقط مستند).
- Is the next prompt unblocked? **بله** — شناسه‌ها و وضعیت‌ها برای گیت‌های Prompt 04 آماده است.

### خلاصهٔ وضعیت ردیابی (خوداظهاری صادقانه)

| وضعیت | تعداد |
|---|---|
| implemented | ۷۳ |
| partial | ۹ |
| missing | ۲ (Windows 7، بسته‌بندی نصب‌کننده) |
| blocked | ۰ در سطح ردیف (قابلیت‌های وابسته به DEC-ها در `docs/open-decisions.md` `BLOCKED` علامت خورده‌اند) |
| VERIFIED ON TARGET | ۰ |

سطح شواهد: `TESTED` = ۷۳، `IMPLEMENTED` = ۹، `DESIGNED` = ۲ (بدون `VERIFIED ON TARGET`).
