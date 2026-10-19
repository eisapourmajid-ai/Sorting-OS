# SORTING OS — مستندات مادر پروژه

> مستندات مهندسی برای طراحی، توسعه، آزمون و بهره‌برداری نرم‌افزار آفلاین مدیریت سورتینگ، انبار، فاکتور، تسویه و حسابداری.

## وضعیت صادقانه مخزن
این پوشه مستندات محصول و طراحی است. وجود سندها به معنای وجود سورس اجرایی، تکمیل ماژول‌ها یا تأیید اجرای Windows 7 نیست. هنگام ممیزی، وجود فیزیکی و وضعیت اجرای هر فایل/قابلیت باید بررسی شود. جدول زیر باید با وضعیت واقعی checkout همگام نگه داشته شود.

## مراجع اصلی

| فایل | مسئولیت |
|---|---|
| `PROJECT_SPEC.md` | دامنه محصول، اصول و شناسه نیازمندی‌ها |
| `docs/01-business-workflows.md` | گردش عملیاتی |
| `docs/02-data-model.md` | قرارداد داده و موجودیت‌ها |
| `docs/03-accounting-settlement-rules.md` | قواعد حسابداری و صافی |
| `docs/04-ui-ux-design-system.md` | سامانه طراحی و رابط |
| `docs/05-offline-windows7-architecture.md` | معماری آفلاین و دروازه سازگاری |
| `docs/06-reporting-printing.md` | گزارش و چاپ |
| `docs/07-security-backup-import.md` | امنیت، backup و import |
| `docs/08-testing-acceptance.md` | آزمون و معیار پذیرش |
| `docs/09-phases-and-ai-agent.md` | فازهای محصول |
| `docs/10-master-ai-coding-directive.md` | دستور مادر عامل کدنویسی |
| `docs/11-implementation-roadmap-gates.md` | نقشه جامع اجرا و گیت‌ها |
| `docs/12-data-exchange-identity-matching-and-printing.md` | import/export، matching اشخاص و تنظیم قالب چاپ |
| `docs/13-bank-transactions-import-and-checks.md` | واردسازی بانک، تطبیق و چک |
| `docs/14-repository-readiness-and-evidence.md` | ممیزی، شواهد و وضعیت آمادگی مخزن |
| `docs/decision-log.md` | تصمیم‌های باز/تأییدشده |
| `docs/dependency-matrix-template.md` | جدول وابستگی‌ها |
| `docs/architecture/ADR-template.md` | قالب تصمیم معماری |
| `docs/examples/settlement-example.md` | مثال عددی صافی |
| `docs/examples/import-matching-scenarios.md` | سناریوهای تطبیق اشخاص |
| `.github/ISSUE_TEMPLATE/feature.md` | قالب قابلیت جدید |
| `.github/ISSUE_TEMPLATE/bug.md` | قالب باگ |
| `.github/PULL_REQUEST_TEMPLATE.md` | قالب بازبینی تغییر |
| `CONTRIBUTING.md` | قواعد توسعه |
| `LICENSE-DECISION.md` | تعیین تکلیف مجوز |

## ترتیب امن اجرا
1. `docs/10-master-ai-coding-directive.md` را در عامل کدنویس قرار دهید.
2. فقط ممیزی مخزن را اجرا کنید؛ قبل از مشاهده سورس، امکان پیاده‌سازی را فرض نکنید.
3. تصمیم‌های باز مالی/مالکیت/صافی را در `docs/decision-log.md` مشخص کنید.
4. گیت عمودی آفلاین، ذخیره محلی، RTL، چاپ و Windows 7 را انجام دهید.
5. فازها را یکی‌یکی اجرا کنید؛ پس از هر مرحله build/test واقعی، مرور diff و گزارش شواهد الزامی است.

## اصول غیرقابل مذاکره
- آنلاین نبودن، قابلیت پایه محصول است؛ هیچ login اجباری ابری، CDN، telemetry یا ارسال پنهان داده وجود نداشته باشد.
- مانده حساب و موجودی از اسناد/تراکنش‌های معتبر محاسبه شوند، نه از ویرایش مستقیم اعداد.
- اسناد قطعی بی‌ردپا ویرایش/حذف نشوند؛ اصلاح کنترل‌شده و ثبت‌شده باشد.
- هر شخص می‌تواند چند نقش داشته باشد؛ نام مشابه تنها مبنای ادغام خودکار نیست.
- هر فاز باید معیار پذیرش، تست و شواهد داشته باشد.
- سازگاری Windows 7 تنها پس از تست واقعی قابل اعلام است. با آزمون روی Windows جدید جایگزین نمی‌شود.
