# گیت‌های اجباری انتشار

## Gate A — Repository & baseline
- [ ] مسیرهای اجرا و تست روی checkout پاک ثبت شده‌اند.
- [ ] dependency/runtime و OS واقعی ثبت شده‌اند.
- [ ] status موجود/ناقص/غایب برای هر requirement موجود است.

## Gate B — Architecture & decisions
- [ ] runtime/GUI/database/print choices در ADR آمده‌اند.
- [ ] تصمیم‌های تجاری حساس صاحب، صافی، واحد پول، تقویم، هزینه و ارزش‌گذاری روشن‌اند یا جریان‌های وابسته مسدودند.

## Gate C — Operational vertical slice
- [ ] ورود محصول و توزین قابل ردیابی‌اند.
- [ ] عملیات سورتینگ و mass balance معتبرند.
- [ ] حرکت inventory/dispatch از اسناد قابل بازسازی است.

## Gate D — Finance
- [ ] purchase/sales invoices و expense allocations به‌صورت ردیفی آزمون شده‌اند.
- [ ] journal قطعی متوازن است.
- [ ] settlement با مثال‌های دستی approved تطبیق دارد.
- [ ] دریافت/پرداخت/بانک/چک idempotent و قابل ممیزی است.

## Gate E — Import/export/print
- [ ] preview/validation/dedup/report/rollback آزمون شده‌اند.
- [ ] matching اشخاص بدون merge خودکار نام‌محور کار می‌کند.
- [ ] قالب چاپ A4/A5، RTL و page break بررسی شده است.

## Gate F — Security & recovery
- [ ] مجوزها در backend/service enforce می‌شوند.
- [ ] audit شامل عملیات حساس است.
- [ ] backup/restore روی داده آزمایشی از ابتدا تا انتها آزمون شده است.

## Gate G — Quality & target OS
- [ ] unit/integration/E2E/migration tests پاس هستند.
- [ ] offline test واقعی انجام شده است.
- [ ] نصب روی سیستم تمیز و OS target اجرا شده است.
- [ ] اگر Windows 7 هدف است، همان Windows 7 SP1 x64 با runtime، فونت و چاپگر هدف آزمون شده است.

## Gate H — Release handover
- [ ] artifact نسخه‌دار، SHA256، changelog و release notes موجود است.
- [ ] راهنمای نصب، کاربر، مدیر سیستم، backup و recovery موجود است.
- [ ] گزارش شناخته‌شده‌ها، migration، rollback و مالک پشتیبانی وجود دارد.
- [ ] تصمیم Go/No-Go توسط مسئول محصول/مالی ثبت شده است.

هیچ گیتی با تیک توصیفی پر نمی‌شود؛ برای هر مورد evidence path و test result ثبت شود.


## گیت مالی اجباری (FINANCIAL RELEASE GATE)

انتشار به‌عنوان نرم‌افزار مالی واقعی فقط زمانی مجاز است که تمام موارد زیر با شواهد آزمون شوند:
- تبدیل دقیق ریال/تومان و import/export round-trip؛
- journal balancing، idempotency، rollback، reversal و audit؛
- trial balance و drill-down به journal؛
- ترازنامه با اختلاف صفر و صورت سود و زیان با تطبیق حساب‌ها؛
- جریان وجوه نقد با آشتی صندوق/بانک و mapping تأییدشده حسابدار؛
- افتتاحیه، بستن دوره و انتقال سود/زیان؛
- اتصال تمام اسناد مصوب (خرید/فروش/هزینه/دریافت/پرداخت/بانک/چک/صافی) به posting بدون duplicate؛
- migration و reconciliation داده تاریخی بدون تفسیر حدسی واحد پول؛
- آزمون تقویم/سال مالی، backup/restore و مجوزهای مالی؛
- تأیید کدینگ، سیاست‌ها و گزارش‌های قانونی/مالیاتی در صورت ادعای پشتیبانی رسمی؛
- UAT و سیستم‌عامل/چاپگر هدف با نتیجه ثبت‌شده.

نبود هرکدام از این شواهد مانع ادعای `Production Ready Accounting` است، حتی اگر UI یا تست‌های هسته موفق باشند.
