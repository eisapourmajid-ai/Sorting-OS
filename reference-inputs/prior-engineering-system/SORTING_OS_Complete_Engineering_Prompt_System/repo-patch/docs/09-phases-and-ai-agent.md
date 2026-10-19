# برنامه اجرایی توسعه و دستورهای عامل هوش مصنوعی

## 1. قواعد عامل برنامه‌نویس

عامل باید قبل از هر کار این فایل‌ها را بخواند:
- `PROJECT_SPEC.md`
- سند تخصصی مرتبط در `docs/`
- آخرین تصمیم‌های معماری ثبت‌شده
- آزمون‌های مربوط به محدوده کار

عامل نباید ابهام تجاری را به دلخواه خود حل کند. اگر تصمیم لازم است، Issue با عنوان `OPEN DECISION` ایجاد کند و کار وابسته را متوقف یا در مرز امن نگه دارد.

## 2. فازها و گیت‌ها

### Phase 0 — Discovery & Compatibility Spike

کارها:
- استخراج تصمیم‌های باز;
- ساخت ماتریس تکنولوژی/نسخه/مجوز/سیستم‌عامل;
- ساخت نمونه WPF/RTL;
- اتصال پایگاه داده محلی;
- ثبت و بازیابی یک رکورد;
- چاپ نمونه;
- ساخت installer آزمایشی و اجرای آن بدون اینترنت.

خروجی‌ها:
- `docs/architecture/technology-matrix.md`
- `docs/testing/windows-7-validation.md`
- Architecture Decision Record برای انتخاب stack

Gate: بدون اثبات نصب/اجرا در محیط هدف، توسعه کامل آغاز نشود.

### Phase 1 — Foundation

- solution structure;
- logging;
- settings;
- migration runner;
- local database;
- login and permission skeleton;
- backup skeleton.

Gate: restart persistence، migration و transaction tests موفق.

### Phase 2 — Master Data & Weighing

- Parties/Roles;
- Products/Grades/Packaging;
- Vehicles;
- inbound/outbound weigh tickets;
- search and document numbering.

Gate: باسکول و شخص قابل ردیابی باشند.

### Phase 3 — Shipment & Sorting

- shipment lifecycle;
- sorting operation;
- output lines;
- waste/loss/difference categories;
- reconciliation and approval queue.

Gate: conservation/tolerance rules آزمون شده باشند.

### Phase 4 — Inventory & Dispatch

- locations;
- inventory transactions;
- reservation;
- internal transfer;
- physical count;
- dispatch and gate-out.

Gate: موجودی منفی و خروج تکراری کنترل شوند.

### Phase 5 — Invoices & Expenses

- invoice header/lines;
- paper-invoice capture;
- expenses and allocations;
- discount/commission rule engine.

Gate: duplicate cost/expense شناخته و مهار شده باشد.

### Phase 6 — Salesperson Settlement

- dispatch lines imported to settlement draft;
- reported weights;
- line-level price and amounts;
- deductions/additions;
- percentage/amount mode;
- review/approval.

Gate: مثال‌های واقعی مورد تأیید کاربر از ابتدا تا انتها پاس شوند.

### Phase 7 — Accounting

- chart of accounts;
- journal entries and lines;
- receivable/payable;
- receipts/payments;
- posting rules per business model;
- account ledger and trial balance validation.

Gate: اسناد قطعی متوازن و قابل بازسازی باشند.

### Phase 8 — UI/Reports

- dashboard queries;
- workflow queues;
- reporting engine;
- A4/A5 reflow;
- print tests;
- styling and keyboard review.

Gate: تمام نمودارها داده واقعی و مسیر جزئیات داشته باشند.

### Phase 9 — Release Hardening

- offline installer;
- security review;
- backup/restore test;
- test on Windows 7 and modern Windows;
- versioning and changelog;
- operational guide.

Gate: Release candidate دارای evidence pack کامل باشد.

## 3. دستور اصلی برای آغاز هر فاز

```text
You are implementing SORTING OS according to PROJECT_SPEC.md.
Read the project specification and all directly relevant docs before editing code.
Work only within the approved phase and its issue scope.
Do not guess unresolved business/accounting rules. Record an OPEN DECISION issue instead.
Do not replace functional behavior with mockups or hard-coded dashboard data.
Keep domain rules outside UI event handlers.
Add automated tests for every non-trivial rule and all critical edge cases.
Use explicit database migrations; do not mutate schema silently.
Make financial and inventory operations transactional and idempotent where retries are possible.
Never edit/delete posted documents without a controlled reversal/correction workflow.
Do not add a dependency without documenting version, license, platform requirements and offline packaging.
Do not claim Windows 7 compatibility without executing the approved test matrix on the target environment.
Do not add runtime internet calls, telemetry, remote fonts, CDN assets, cloud login, or online license checks.
At the end, report: changed files, requirement IDs covered, tests executed, pass/fail, database migration, dependency changes, offline validation, platform validation, remaining risks and evidence.
If a mandatory gate fails, do not mark the phase complete.
```

## 4. AI prompts per phase

### Prompt Phase 0

```text
Analyze PROJECT_SPEC.md and produce a compatibility spike plan. Do not implement all modules.
Create the technology matrix, dependency inventory template and Windows 7 validation procedure.
Build the smallest vertical slice proving offline launch, Persian RTL rendering, local database write/read, restart persistence and print preview on Windows 7 SP1 x64 and a current Windows version. Record exact OS build, runtime versions, package versions and results. If the target fails, recommend alternatives with evidence before continuing.
```

### Prompt Phase 1

```text
Implement only the application foundation: solution structure, settings, logging, local database abstraction, schema version/migrations, local user authentication skeleton and backup foundation. Add unit/integration tests for migration, transaction rollback and restart persistence. Keep internet disabled and do not add business modules outside master data.
```

### Prompt Phase 2

```text
Implement parties with multiple roles, products, grades, packaging types, vehicles and manual inbound/outbound weigh tickets. Add server-independent document numbering, validation, search and audit events. Preserve source document numbers separately from internal IDs. Add tests for invalid weights and duplicate submission.
```

### Prompt Phase 3

```text
Implement shipment lifecycle and sorting operations with multi-line outputs, separate waste/loss/measurement difference, configurable tolerance and approval workflow. Inventory effects must occur only on approved posting. Include tests for mass balance and explain every exception.
```

### Prompt Phase 4

```text
Implement inventory ledger, locations, reservation, transfers, physical counts, dispatch and dispatch lines. Make stock movements transactional and idempotent. Block unauthorized negative stock and duplicate posting. Add reconciliation tests.
```

### Prompt Phase 5

```text
Implement invoices with multiple lines, legacy paper-document entry, expenses, allocations, commission and discount rules. Distinguish expense recognition from settlement display. Make source-document links explicit and prevent duplicate accounting recognition. Do not finalize accounting policy not approved in the decision log.
```

### Prompt Phase 6

```text
Implement salesperson settlement using dispatch lines. Keep sent weight and reported weight independently. Calculate weight differences per line and percent from an explicit base. Support amount-input and rate-input modes with exactly one authoritative input at a time. Show full calculation detail; route threshold exceptions for approval. Do not post settlement cash receipt automatically.
```

### Prompt Phase 7

```text
Implement chart of accounts, journal header/lines, receipts, payments, ledger and balance validation. Enforce debit equals credit for posted entries, prevent duplicate posting, and implement correction/reversal rather than editing posted entries. Only implement posting rules approved for the chosen business model.
```

### Prompt Phase 8

```text
Implement data-backed dashboard, filters, operational queues and required reports. All metrics must derive from database queries with documented definitions. Build real A4/A5 reflow and preview. Test Persian rendering, long rows, multi-page reports, empty data and target printers. Remove any placeholder feature from production navigation unless clearly marked as unavailable.
```

### Prompt Phase 9

```text
Perform release hardening: full offline acceptance, Windows 7 compatibility tests, modern Windows tests, backup/restore, migration recovery, access-control review, installer test, dependency/license inventory, changelog and user guide. Produce a release evidence report. Do not state that a test passed unless evidence exists.
```

## 5. Issue labels

- `type:feature`
- `type:bug`
- `type:security`
- `type:docs`
- `type:decision`
- `area:weighing`
- `area:inventory`
- `area:accounting`
- `area:settlement`
- `area:ui`
- `area:offline`
- `area:printing`
- `gate:windows7`
- `blocked:business-rule`

## 6. Release naming

از Semantic Versioning یا سیاست نسخه‌گذاری مشخص استفاده شود. برای نسخه‌های اولیه می‌توان `0.x.y` انتخاب کرد تا زمانی که قواعد اصلی و مدل داده تثبیت شوند. شماره نسخه برنامه، نسخه schema و commit hash جدا ثبت شوند.
