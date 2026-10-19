# فهرست اجرایی پرامپت‌های SORTING OS — از صفر تا انتشار

این بسته شامل ۳۶ پرامپت مرحله‌ای (00 تا 35) است. هر پرامپت مستقل است اما وابستگی‌ها به ترتیب شماره تعریف شده‌اند. عامل کدنویس باید هر بار فقط یک پرامپت را اجرا کند؛ اجرای دسته‌ای همه مراحل در یک درخواست ممنوع است.

## قرارداد اجرای توالی
1. Prompt 00 خواندنی و بدون کدنویسی است.
2. Prompt 01 baseline را ثبت می‌کند.
3. Promptهای 02–04 معماری، تصمیم‌ها و ساختار مخزن را تثبیت می‌کنند.
4. Promptهای 05–24 توسعهٔ عمودی قابلیت‌ها هستند.
5. Promptهای 25–32 ایمنی، آزمون و مهاجرت را می‌بندند.
6. Promptهای 33–35 شامل پایلوت، RC، انتشار و handover هستند.
7. هر مرحله تا ثبت گزارش پذیرش نباید به عنوان PASS علامت بخورد.

## مراجع اجباری در تمام مراحل مالی
پیش از Prompt 00، فایل `docs/agent-system/UPLOAD_FIRST_ORDER_FA.md` را اجرا/مطالعه کنید. قبل از تغییر هر مبلغ/گزارش، چهار سند مرجع زیر الزام‌آورند: `docs/financial/ACCOUNTING_CORE_SPEC_FA.md`, `docs/financial/MONEY_UNIT_POLICY_FA.md`, `docs/financial/FINANCIAL_REPORTS_AND_ANALYTICS_FA.md`, `docs/financial/ACCOUNTING_ACCEPTANCE_SCENARIOS_FA.md`. هسته واحد پول `integer rial` است؛ ۱ تومان = ۱۰ ریال. هر صورت مالی باید از journal lines و داده واقعی ساخته شود، نه mock/hard-code.

## فهرست
- [00 — مبنای شروع و ممیزی مخزن](prompts/00-repository-audit-and-state-map.md)
- [01 — ثبت خط مبنا و تکرارپذیری](prompts/01-baseline-build-and-test-evidence.md)
- [02 — تصمیم معماری و ماتریس سازگاری](prompts/02-architecture-decision-and-platform-matrix.md)
- [03 — تطبیق نیازمندی‌ها و تصمیم‌های باز](prompts/03-requirements-traceability-and-decision-log.md)
- [04 — پاکیزگی مخزن و دستورهای توسعه](prompts/04-repository-hygiene-and-agent-instructions.md)
- [05 — پوسته برنامه و قراردادهای برنامه‌نویسی](prompts/05-application-shell-and-coding-standards.md)
- [06 — زیرساخت پایگاه داده و migration](prompts/06-database-infrastructure-and-migrations.md)
- [07 — هویت اشخاص و نقش‌ها](prompts/07-party-master-data-and-roles.md)
- [08 — تطبیق و ادغام اشخاص](prompts/08-identity-matching,-review-queue-and-safe-merge.md)
- [09 — اطلاعات پایه محصول، درجه و بسته‌بندی](prompts/09-products,-grades,-packaging-and-units.md)
- [10 — باسکول و اسناد توزین](prompts/10-weighing-tickets.md)
- [11 — محموله و دریافت کالا](prompts/11-shipment-intake-and-lifecycle.md)
- [12 — عملیات سورتینگ و تراز جرم](prompts/12-sorting-operations-and-mass-balance.md)
- [13 — گردش انبار، مکان، رزرو و موجودی](prompts/13-inventory-ledger,-locations-and-reservations.md)
- [14 — ارسال، حواله و حمل](prompts/14-dispatch,-loading-and-transport.md)
- [15 — خرید، رسید خرید و هزینه‌ها](prompts/15-purchasing,-purchase-invoices-and-expenses.md)
- [16 — فروش، ردیف فاکتور و تخصیص محموله](prompts/16-sales-invoices-and-shipment-allocations.md)
- [17 — دفترکل دوبل و گردش حساب اشخاص](prompts/17-double-entry-ledger-and-party-subledger.md)
- [18 — موتور صافی و تسویه](prompts/18-settlement-calculation-engine.md)
- [19 — ورود گردش بانکی و تطبیق تراکنش](prompts/19-bank-statement-import-and-reconciliation.md)
- [20 — چرخه چک، دریافت و پرداخت](prompts/20-check-lifecycle-and-receipts-payments.md)
- [21 — موتور جامع ورود/خروج Excel/CSV](prompts/21-universal-import-export-engine.md)
- [22 — گزارش‌ساز و داشبورد](prompts/22-reporting-engine-and-kpi-dashboard.md)
- [23 — قالب چاپ قابل تنظیم و پیش‌نمایش](prompts/23-configurable-print-layout-designer.md)
- [24 — سامانه طراحی رابط و RTL](prompts/24-ui-design-system-and-rtl-polish.md)
- [25 — کاربران، مجوزها و ممیزی](prompts/25-authentication,-granular-permissions-and-audit.md)
- [26 — پشتیبان‌گیری، بازیابی و مهاجرت داده](prompts/26-backup,-restore-and-data-migration.md)
- [27 — آفلاین بودن و سازگاری Windows 7](prompts/27-offline-and-legacy-os-verification.md)
- [28 — آزمون‌های واحد و خواص دامنه](prompts/28-unit-tests-and-invariant-property-tests.md)
- [29 — تست integration و سناریوی سرتاسری](prompts/29-integration,-e2e-and-acceptance-scenarios.md)
- [30 — کارایی، اطمینان و مقاوم بودن داده](prompts/30-performance,-reliability-and-data-integrity.md)
- [31 — بسته‌بندی، نصب و به‌روزرسانی](prompts/31-installer-and-release-packaging.md)
- [32 — ورود داده تاریخی و سازگاری Excel](prompts/32-historical-data-migration-and-reconciliation.md)
- [33 — پایلوت و پذیرش کاربر](prompts/33-pilot-deployment-and-uat.md)
- [34 — تثبیت نسخه کاندید انتشار](prompts/34-release-candidate-hardening.md)
- [35 — انتشار و تحویل نهایی](prompts/35-final-release,-handover-and-maintenance.md)

## ماتریس فازها
| بازه | دامنه | گیت لازم |
|---|---|---|
| 00–04 | ممیزی، خط مبنا، معماری، الزامات و مخزن | شواهد و تصمیم‌های ثبت‌شده |
| 05–09 | اسکلت، داده، اشخاص، تطبیق، کاتالوگ | migration و تست دامنه |
| 10–16 | باسکول، محموله، سورتینگ، انبار، ارسال و فاکتور | ردیابی فیزیکی و مالی قابل پیگیری |
| 17–20 | دفترکل، صافی، بانک و چک | تأیید قواعد مالی + آزمون تراز |
| 21–26 | تبادل داده، گزارش، چاپ، UI، امنیت و بازیابی | تست import/export, permission, backup |
| 27–32 | آفلاین/ویندوز، تست‌ها، performance، package و migration | شواهد سیستم هدف و تطبیق داده |
| 33–35 | پایلوت، RC و انتشار | Go/No-Go و handover امضاشده |
