# ترتیب بارگذاری مرجع به عامل کدنویس (قبل از Prompt 00)

این فایل پاسخ می‌دهد که کدام فایل‌ها باید ابتدا در context عامل قرار گیرند و در چه ترتیبی. «بارگذاری» یعنی افزودن متن مرجع به context مخزن/عامل؛ نیازی به بارگذاری فایل‌های کاربر یا پایگاه داده واقعی نیست.

## مرحله صفر — ابتدا همیشه بارگذاری شود

1. `MASTER_PROMPT_FOR_AGENT_FA.md` — نقش عامل، گاردریل‌ها، تعاریف وضعیت و فرآیند Git.
2. `PROJECT_SPEC.md` — چشم‌انداز، محدوده نسخه و نیازمندی‌های پایه.
3. `contracts/CURRENT_IMPLEMENTATION_STATUS_FA.md` — چه چیزی در کد هست/نیست.
4. `docs/agent-system/SOURCE_OF_TRUTH_AND_CONFLICT_ORDER_FA.md` — سلسله‌مراتب مراجع و نحوه حل تعارض.
5. `docs/financial/ACCOUNTING_CORE_SPEC_FA.md` — الزام هسته حسابداری و گزارش‌ها.
6. `docs/financial/MONEY_UNIT_POLICY_FA.md` — سیاست قطعی ریال/تومان.
7. `docs/financial/FINANCIAL_REPORTS_AND_ANALYTICS_FA.md` — قرارداد گزارش‌های مالی/تحلیلی.
8. `docs/03-accounting-settlement-rules.md` و `docs/13-bank-transactions-import-and-checks.md` یا منبع متناظر در `reference-inputs/` — قواعد عملیاتی/مالی و بانک.
9. `docs/04-ui-ux-design-system.md` و `reference-inputs/UI_LAYOUT_THEME_HEADER_SPEC.md` — زبان طراحی و رفتار رابط.
10. `PROMPT_INDEX_00_TO_35_FA.md` — نقشه ترتیب اجرا، برای برنامه‌ریزی فقط؛ این به معنی اجرای هم‌زمان مراحل نیست.

## پس از بارگذاری مراجع

- به عامل اجازه دهید **فقط** `prompts/00-repository-audit-and-state-map.md` را اجرا کند.
- عامل باید checkout واقعی مخزن، branch، commit SHA، وضعیت تغییرات کاربر، فایل‌های موجود، build/tests و گپ‌ها را گزارش کند.
- تا زمانی که ممیزی و baseline ثبت و بازبینی نشده‌اند، هیچ پرامپت feature توسعه اجرا نشود.
- هر Prompt فقط پس از PASS گیت قبلی اجرا شود. در هر نوبت فقط یک مرحله فعال است.

## مراجع مشروط

- `reference-inputs/` و `reference-inputs/prior-engineering-system/` شامل نسخه‌های قبلی و مواد اصلی هستند؛ برای ردیابی لازم‌اند، نه اینکه همگی هم‌زمان به‌عنوان قانون جاری تزریق شوند.
- در تعارض، دستور صریح و تازه مالک محصول اولویت دارد، سپس `PROJECT_SPEC.md` و اسناد canonical جاری زیر `docs/` و قراردادهای مالی، سپس ADRهای Accepted. نسخه‌های آرشیوی صرفاً شواهد تاریخی‌اند.
- اگر عامل به GitHub یا سیستم هدف دسترسی ندارد، باید `BLOCKED`/`NOT VERIFIED` گزارش دهد؛ نباید موفقیت ساخت، PR، build یا آزمون را ادعا کند.

## بسته حداقلی برای context محدود

اگر ابزار فقط چند فایل را می‌پذیرد، در این ترتیب استفاده کنید: `MASTER_PROMPT_FOR_AGENT_FA.md`; `PROJECT_SPEC.md`; `contracts/CURRENT_IMPLEMENTATION_STATUS_FA.md`; `docs/financial/ACCOUNTING_CORE_SPEC_FA.md`; `docs/financial/MONEY_UNIT_POLICY_FA.md`; `docs/financial/FINANCIAL_REPORTS_AND_ANALYTICS_FA.md`; `docs/03-accounting-settlement-rules.md`; `PROMPT_INDEX_00_TO_35_FA.md`; و سپس فایل پرامپت همان مرحله.
