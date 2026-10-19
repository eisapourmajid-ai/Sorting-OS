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
| DEC-003 | مبنا و معنای دقیق درصد صافی (سهم طرف در برابر سهم مجموعه) | مالک کسب‌وکار + مالی | Open (تخصیص درصد طبق DEC-017 قطعی شد؛ معنای عددی همچنان باز است) | فرمول نهایی سود و زیان صافی |
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
| DEC-017 | تخصیص درصد صافی: پیش‌فرض قابل ویرایش + نرخ هر حساب طرف + نرخ هر فاکتور | مالک محصول | **Accepted (2026-10-19)** | — |

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

### TECH-007 — ترتیب اعمال و نسخه‌بندی نرخ صافی
- Status: Accepted (2026-10-19) — همراه DEC-017
- Decision: ترتیب اعمال نرخ `invoice → party → default` و ورود دستی بالاتر از همه؛ هر نرخ یک ردیف
  نسخه‌دار با `valid_from/valid_to` است؛ ویرایش نرخ نسخهٔ قبلی را می‌بندد و نسخهٔ جدید می‌سازد؛
  صافی محاسبه‌شده هرگز بازنویسی نمی‌شود.
- Evidence: `desktop/sorting_os/services/settlement.py`، `desktop/tests/test_settlement_rates.py`
- Affected: FIN-SET-001..004

### TECH-006 — شناسنامهٔ تخصیص وصولات
- Status: Provisional (DEC-015)
- Decision: تخصیص FIFO در سطح طرف حساب (`receipts-fifo-v1`)؛ مقدار آن در خروجی گزارش درج می‌شود.
- Evidence: `desktop/sorting_os/services/reporting.py:receivables_aging`
- Affected: RPT-FIN-07

## تصمیم‌های کسب‌وکار پذیرفته‌شده (DEC-017)

### DEC-017 — تخصیص درصد صافی در سطح پیش‌فرض/حساب طرف/فاکتور

- Status: **Accepted** (2026-10-19)
- Owner: مالک محصول
- Approval evidence: دستور صریح مالک محصول در جلسهٔ کاری: «درصد صافی‌ها باید قابل تخصیص برای هر
  حساب فرشنده یا فاکتور لحاظ شود… قابلیت پیش‌فرض داشته باشد و قابلیت ویرایش وجود داشته باشد».
- Context: درصد صافی در عمل بین طرف‌ها و حتی بین فاکتورهای یک طرف یکسان نیست؛ تاکنون فقط مقدار
  در لحظهٔ محاسبه وارد می‌شد و نگهداری نمی‌شد.
- Options considered:
  1. فقط مقدار دستی در هر محاسبه (وضعیت قبل) ⇒ خطای ورودی انسانی و نبود سابقه؛ رد شد.
  2. یک نرخ ثابت سراسری ⇒ با واقعیت کسب‌وکار ناسازگار؛ رد شد.
  3. **نرخ نسخه‌دار در سه سطح (پیش‌فرض ← حساب طرف ← فاکتور)** ⇒ انتخاب‌شده.
- Decision:
  1. درصد صافی یک ویژگی قابل تخصیص است، نه مقدار ثابت کد.
  2. سه سطح: **پیش‌فرض سراسری** (همیشه قابل ویرایش)، **حساب طرف صافی** (فرشنده/باغدار) و
     **فاکتور**.
  3. ترتیب اعمال: `فاکتور ← حساب طرف ← پیش‌فرض`؛ ورود دستی در لحظهٔ محاسبه بالاتر از همه است.
  4. ویرایش نرخ = بستن نسخهٔ قبلی و ثبت نسخهٔ جدید (سابقه حفظ می‌شود)؛ صافی‌های محاسبه‌شدهٔ
     قبلی **تغییر نمی‌کنند** (snapshot).
  5. اگر هیچ نرخی در هیچ سطحی نباشد، محاسبه با پیام روشن رد می‌شود (فرض درصد ممنوع).
- Consequences:
  - نرخ مؤثر و **منشأ آن** در snapshot صافی و در چاپ صورتحساب صافی ثبت و نمایش داده می‌شود.
  - ویرایش نرخ، گذشته را بازنویسی نمی‌کند ⇒ حسابرسی‌پذیر.
  - معنای عددی درصد (سهم طرف در برابر سهم مجموعه) همچنان **باز** است (DEC-003) و در سند
    صافی همچنان با یادداشت «موقت» ثبت می‌شود.
- Evidence: `desktop/sorting_os/services/settlement.py` (set_rate/resolve_rate/calculate)،
  `desktop/sorting_os/migrations.py` (MIGRATION_3)، `desktop/tests/test_settlement_rates.py`،
  `reports/SETTLEMENT_RATE_ASSIGNMENT.md`
- Affected requirement IDs: FIN-SET-001..004، RPT-FIN-10
- Migration/compatibility impact: `MIGRATION_3` (تراکنشی، نسخه‌دار) — جدول `settlement_rates` و سه
  ستون جدید روی `settlements`. صافی‌های قدیمی بدون `rate_source` باقی می‌مانند و `NULL` می‌مانند.
- Approval evidence: پیام مالک محصول (۱۴۰۵/۰۷/۲۷) + پیاده‌سازی و آزمون‌های
  `desktop/tests/test_settlement_rates.py`.

## قاعده

هیچ مقدار balancing جعلی، واحد پول حدس‌زده، مالکیت کالای فرضی یا درصد صافی «رایج» برای عبور از یک گیت استفاده نشود. اگر تصمیم گرفته نشده، مسیر وابسته با وضعیت `BLOCKED` بماند.
