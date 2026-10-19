# وضعیت واقعی قابلیت‌ها در تحویل MVP

| حوزه | وضعیت | توضیح |
|---|---|---|
| پوسته دسکتاپ RTL | Partial | Tkinter UI فارسی ایجاد شده؛ تست روی نمایشگر/Windows هدف لازم است. |
| ذخیره‌سازی محلی SQLite | Implemented/Tests | schema اولیه و transaction helpers وجود دارد؛ migration framework کامل نیست. |
| اشخاص | Partial | ثبت/ویرایش/search پایه و جلوگیری از تکرار کد ملی در insert/update. |
| تطبیق/merge اشخاص | Partial | CSV preview با هشدار تشابه؛ صف تطبیق کامل و merge ارجاعات پیاده‌سازی نشده. |
| محموله ورودی | Partial | owner/product/weight/time/status پایه؛ چندقلمی و lifecycle کامل نیست. |
| باسکول | Partial | ثبت gross/tare/net و اتصال اختیاری به یک محموله؛ multi-shipment link هنوز نیست. |
| سورتینگ و تراز جرم | Missing | خروجی چنددرجه‌ای، افت/ضایعات و mass balance وجود ندارد. |
| دفتر انبار/رزرو/حواله | Missing | موجودی ledger-based و dispatch posting کامل نیست. |
| فاکتور | Partial | سربرگ ساده و مبلغ کل، بدون ردیف‌های کامل/اصلاحیه/ledger posting. |
| دفترکل دوبل | Partial / Implemented in new accounting core | `desktop/accounting_core.py` و صفحه حسابداری posting متوازن، یکتایی منبع و برگشت سند را پشتیبانی می‌کنند؛ اتصال اتوماتیک invoice/settlement به journal هنوز کامل نیست. |
| صافی | Missing | engine نسخه‌دار و تأییدشده ندارد. |
| ریال/تومان و مبالغ | Implemented in accounting core; legacy partial | مبنای دفترکل integer ریال، تبدیل دقیق تومان و formatter دارد؛ مبلغ‌های legacy فاکتور هنوز واحد/مهاجرت تأییدشده ندارند. |
| تراز آزمایشی/ترازنامه/سود و زیان | Implemented in accounting core; acceptance required | query واقعی دفترکل و UI گزارش وجود دارد؛ دوره مالی، تقویم شمسی و تأیید حسابدار کامل نشده‌اند. |
| جریان نقدی/نسبت‌ها | Partial / management only | گزارش پایه و reconciliation نقد دارد؛ mapping و نسبت جاری نیازمند کدینگ/بازبینی حسابدار است. |
| بانک/چک | Missing in application | spec موجود است؛ UI/service/ledger integration نیازمند پیاده‌سازی است. |
| Import/Export | Partial | CSV ساده، preview اشخاص و چهار خروجی؛ XLSX/mapping همه جداول کامل نیست. |
| طراح چاپ | Missing | print designer نهایی وجود ندارد. |
| backup | Partial | تهیه backup موجود است؛ restore wizard و recovery drills کامل نیست. |
| audit | Partial | log محلی رویدادهای ثبت شده؛ امنیت ضد دستکاری و coverage کامل نیازمند بررسی است. |
| آزمون‌ها | Partial | ۱۷ unit tests فعلی برای هسته عملیاتی و مالی پاس شده‌اند؛ integration/E2E و OS matrix باقی است. |
| EXE/Installer | Not built | script build وجود دارد، artifact اجراشده و آزموده‌شده تحویل نشده است. |
| Windows 7 SP1 x64 | Not verified | فقط آزمون مستقیم روی OS هدف می‌تواند وضعیت را عوض کند. |

این جدول مرجع صادقانه برای عامل است؛ با پیشرفت برنامه باید از test evidence و commit واقعی به‌روزرسانی شود. هسته مالی جدید هنوز به معنی نرم‌افزار حسابداری رسمی آماده بهره‌برداری نیست.
