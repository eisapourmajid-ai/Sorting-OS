# Decision Log — SORTING OS

هر تصمیم تجاری/معماری باید شناسه یکتا، مالک، شواهد و اثر migration داشته باشد. تا وضعیت `Accepted` نگرفته، عامل نباید آن را به قانون پنهانی محصول تبدیل کند.

## قالب تصمیم

- ID: `DEC-XXX`
- Status: Proposed / Accepted / Rejected / Superseded
- Date:
- Owner:
- Context:
- Options considered:
- Decision:
- Consequences:
- Evidence/links:
- Affected requirement IDs:
- Migration/compatibility impact:
- Approval evidence:

## تصمیم‌های کسب‌وکار و مالی باز

| ID | موضوع | مالک تصمیم | وضعیت | بلوکه‌کننده برای |
|---|---|---|---|---|
| DEC-001 | مدل کارمزدی، امانی، خریدوفروش یا ترکیبی | مالک کسب‌وکار + حسابدار | Open | posting خرید/فروش و مالکیت موجودی |
| DEC-002 | مالکیت کالا در هر مرحله از ورود تا بارگیری | مالک کسب‌وکار | Open | ارزش‌گذاری موجودی/ترازنامه |
| DEC-003 | مبنا و معنای درصد صافی | مالک کسب‌وکار + مالی | Open | موتور صافی/تسویه |
| DEC-004 | وزن مرجع و اختلاف وزن قابل تسویه | عملیات + بارفروش | Open | تسویه و گزارش کسری |
| DEC-005 | ترتیب کمیسیون، تخفیف، هزینه حمل/کارگری/باربری و کسورات | مالی | Open | سود/زیان و حساب دریافتنی/پرداختنی |
| DEC-006 | روش ارزش‌گذاری موجودی و بهای تمام‌شده | حسابدار | Open | ترازنامه/سود و زیان |
| DEC-007 | تعداد کاربر هم‌زمان و تک‌رایانه/شبکه محلی | مالک کسب‌وکار | Open | معماری ذخیره‌سازی/قفل‌ها |
| DEC-008 | تقویم نمایش/ورود، واحد ورودی/نمایش پیش‌فرض، سال مالی و تاریخ قفل دوره (مبنای ذخیره ledger = integer rial مصوب است) | مالی + عملیات | Open | گزارش دوره و بستن سال |
| DEC-009 | دامنه انطباق حسابداری رسمی/مالیاتی | حسابدار/مشاور | Open | اعلام آمادگی رسمی |
| DEC-010 | افتتاحیه و reconciliation مانده‌های اولیه | مالی | Open | شروع داده واقعی |
| DEC-011 | کدینگ نهایی حساب‌ها و تفصیلی اشخاص/مراکز هزینه | حسابدار | Open | posting production |
| DEC-012 | طبقه‌بندی جریان نقد و جاری/غیرجاری | حسابدار | Open | صورت وجوه نقد و نسبت‌های مالی |
| DEC-013 | واحد مبالغ موجود در Excel/بانک/فاکتورهای تاریخی | مالی + مالک داده | Open | مهاجرت تاریخی |
| DEC-014 | سیاست برگشت، تأیید و قفل سند قطعی | مالک + حسابدار | Open | اختیارات مالی و کنترل تقلب |
| DEC-015 | روش تخصیص وصولات به فاکتورها (FIFO پیش‌فرض) | مالی | Open | گزارش دریافتنی سنی و تسویهٔ جزئی |
| DEC-016 | posting صافی به‌صورت موقت تا تأیید مدل کسب‌وکار | مالی + حسابدار | Open | حساب دریافتنی/سود و زیان صافی |

## تصمیم‌های معماری/پلتفرم باز

| ID | موضوع | مالک | وضعیت |
|---|---|---|---|
| ADR-001 | تأیید معماری نهایی UI/domain/persistence/reporting | مهندس مسئول | Accepted (2026-10-19) — `docs/architecture/ADR-0001-platform-and-runtime.md` |
| ADR-002 | ماتریس پشتیبانی و ساخت واقعی Windows 7 SP1 x64 | مهندس انتشار + مالک | Open — تا آزمون روی W7، وضعیت `NOT VERIFIED ON TARGET OS` |
| ADR-003 | تقویم شمسی آفلاین و پیاده‌سازی تبدیل/آزمون | مسئول فنی | Provisional — موتور آزمون‌شده، تأیید رسمی کسب‌وکار انجام نشده |
| ADR-004 | سیاست نسخه schema و recovery/restore | مسئول فنی | Provisional — migration نسخه‌دار + backup/restore پیاده‌سازی شده |
| ADR-005 | محل قراردادن `party_ref` (فقط خطوط دریافتنی/پرداختنی) | حسابدار | Provisional — نیازمند بازبینی حسابدار |

## تصمیم‌های فنی پذیرفته‌شده (Technical, Accepted)

این‌ها تصمیم‌های فنی مصوب‌شده در محدودهٔ ADR-0001 هستند؛ اثر تجاری ندارند ولی در traceability
به آن‌ها ارجاع داده می‌شود.

### TECH-001 — واحد پول
- Status: Accepted (2026-10-19)
- Decision: مبنای ذخیره `int` ریال؛ `۱ تومان = ۱۰ ریال`؛ `Decimal` فقط در مرز تبدیل؛ `float` ممنوع؛
  واحد نمایش و واحد ورودی مستقل؛ واحد همیشه در گزارش/چاپ درج می‌شود.
- Evidence: `desktop/sorting_os/core.py`، `desktop/tests/test_core.py` (T-MONEY-001..012)
- Affected: FIN-MONEY-001..012

### TECH-002 — تقویم شمسی آفلاین
- Status: Accepted (پیاده‌سازی)، تأیید رسمی: Pending (ADR-003)
- Decision: موتور تقویم درون‌برنامه‌ای با عدد روز صحیح؛ لنگر `1403-01-01 = 2024-03-20`؛ بازهٔ
  پشتیبانی‌شدهٔ 1300–1500 هجری شمسی؛ بدون هیچ API شبکه‌ای.
- Evidence: `desktop/sorting_os/core.py`، ۱۴ لنگر + رفت‌وبرگشت ۷۳٬۳۲۳ روزه بدون خطا
- Affected: FIN-CORE-033

### TECH-003 — قرارداد `party_ref`
- Status: Provisional (ADR-005)
- Decision: `party_ref` فقط روی خطوط حساب‌های دریافتنی/پرداختنی (1100/2000) نوشته می‌شود؛ خطوط
  درآمد/هزینه/نقد بدون `party_ref` هستند تا ماندهٔ طرف از دفترکل درست بازسازی شود.
- Evidence: `desktop/sorting_os/services/ledger.py`، `desktop/tests/test_finance.py`
- Affected: FIN-CORE-014، RPT-FIN-06

### TECH-004 — تراکنش و مهاجرت
- Status: Accepted (2026-10-19)
- Decision: هر نوشتن در `BEGIN IMMEDIATE` + تراکنش؛ migration نسخه‌دار در `schema_meta` و اجرای
  تراکنشی هر نسخه؛ `PRAGMA foreign_keys=ON` و `busy_timeout`.
- Evidence: `desktop/sorting_os/db.py`، `desktop/sorting_os/migrations.py`، `desktop/tests/test_migrations.py`
- Affected: FIN-CORE-012، FIN-CORE-015

### TECH-005 — عدم posting خودکار فاکتور legacy
- Status: Accepted (2026-10-19)
- Decision: فاکتور با `amount_rial IS NULL` (دادهٔ legacy) قابل posting نیست و نباید در گزارش
  مالی وارد شود؛ مادهٔ «قطعی» صرفاً وضعیت عملیاتی است و سند مالی نمی‌سازد.
- Evidence: `desktop/sorting_os/services/ledger.py`، `desktop/tests/test_migrations.py`
- Affected: FIN-MONEY-012، DEC-013

### TECH-006 — شناسنامهٔ تخصیص وصولات
- Status: Provisional (DEC-015)
- Decision: تخصیص FIFO در سطح طرف حساب (`receipts-fifo-v1`)؛ مقدار آن در خروجی گزارش درج می‌شود.
- Evidence: `desktop/sorting_os/services/reporting.py:receivables_aging`
- Affected: RPT-FIN-07

## قاعده

هیچ مقدار balancing جعلی، واحد پول حدس‌زده، مالکیت کالای فرضی یا درصد صافی «رایج» برای عبور از یک گیت استفاده نشود. اگر تصمیم گرفته نشده، مسیر وابسته با وضعیت `BLOCKED` بماند.
