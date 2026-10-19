# دفتر اجرای فازها و شواهد

از این فایل در مخزن اصلی استفاده کنید. هر فاز باید با شاهد و نتیجه واقعی ثبت شود.

| فاز | وضعیت | Branch/Commit | Build | Tests | Offline | Windows 7 | شواهد/لینک | بلوکر |
|---|---|---|---|---|---|---|---|---|
| P00 — فاز 00 — ممیزی مخزن و نقشه وضعیت | NOT STARTED | — | NOT RUN | NOT RUN | NOT RUN | NOT RUN | — | — |
| P01 — فاز 01 — آماده‌سازی محیط و اثبات امکان اجرا | NOT STARTED | — | NOT RUN | NOT RUN | NOT RUN | NOT RUN | — | — |
| P02 — فاز 02 — تثبیت معماری و تصمیم‌های باز | NOT STARTED | — | NOT RUN | NOT RUN | NOT RUN | NOT RUN | — | — |
| P03 — فاز 03 — پوسته برنامه و زیرساخت پایه | NOT STARTED | — | NOT RUN | NOT RUN | NOT RUN | NOT RUN | — | — |
| P04 — فاز 04 — مدل داده، مهاجرت و قرارداد دامنه | NOT STARTED | — | NOT RUN | NOT RUN | NOT RUN | NOT RUN | — | — |
| P05 — فاز 05 — کاربران، مجوزها و ردپای ممیزی | NOT STARTED | — | NOT RUN | NOT RUN | NOT RUN | NOT RUN | — | — |
| P06 — فاز 06 — اشخاص، نقش‌ها و داده‌های پایه | NOT STARTED | — | NOT RUN | NOT RUN | NOT RUN | NOT RUN | — | — |
| P07 — فاز 07 — تطبیق، بررسی تکراری و ادغام اشخاص | NOT STARTED | — | NOT RUN | NOT RUN | NOT RUN | NOT RUN | — | — |
| P08 — فاز 08 — موتور عمومی ورود و خروج داده | NOT STARTED | — | NOT RUN | NOT RUN | NOT RUN | NOT RUN | — | — |
| P09 — فاز 09 — باسکول، دریافت و چرخه محموله | NOT STARTED | — | NOT RUN | NOT RUN | NOT RUN | NOT RUN | — | — |
| P10 — فاز 10 — عملیات سورتینگ، خروجی، ضایعات و بسته‌بندی | NOT STARTED | — | NOT RUN | NOT RUN | NOT RUN | NOT RUN | — | — |
| P11 — فاز 11 — دفتر موجودی، محل، انتقال و انبارگردانی | NOT STARTED | — | NOT RUN | NOT RUN | NOT RUN | NOT RUN | — | — |
| P12 — فاز 12 — حواله خروج، بارگیری و ردیابی ارسال | NOT STARTED | — | NOT RUN | NOT RUN | NOT RUN | NOT RUN | — | — |
| P13 — فاز 13 — فاکتور خرید، هزینه و تخصیص | NOT STARTED | — | NOT RUN | NOT RUN | NOT RUN | NOT RUN | — | — |
| P14 — فاز 14 — فاکتور فروش و آماده‌سازی صافی | NOT STARTED | — | NOT RUN | NOT RUN | NOT RUN | NOT RUN | — | — |
| P15 — فاز 15 — موتور محاسبه صافی بارفروش/مالک | NOT STARTED | — | NOT RUN | NOT RUN | NOT RUN | NOT RUN | — | — |
| P16 — فاز 16 — هسته حسابداری دوبل و دفتر اشخاص | NOT STARTED | — | NOT RUN | NOT RUN | NOT RUN | NOT RUN | — | — |
| P17 — فاز 17 — صورت‌حساب بانکی، تطبیق، چک و مغایرت‌گیری | NOT STARTED | — | NOT RUN | NOT RUN | NOT RUN | NOT RUN | — | — |
| P18 — فاز 18 — گزارش‌ها، داشبورد و تعریف شاخص‌ها | NOT STARTED | — | NOT RUN | NOT RUN | NOT RUN | NOT RUN | — | — |
| P19 — فاز 19 — طراح قالب چاپ و پیش‌نمایش | NOT STARTED | — | NOT RUN | NOT RUN | NOT RUN | NOT RUN | — | — |
| P20 — فاز 20 — طراحی رابط، هدر، تم و چیدمان شخصی | NOT STARTED | — | NOT RUN | NOT RUN | NOT RUN | NOT RUN | — | — |
| P21 — فاز 21 — پشتیبان‌گیری، بازیابی و انتقال داده تاریخی | NOT STARTED | — | NOT RUN | NOT RUN | NOT RUN | NOT RUN | — | — |
| P22 — فاز 22 — آزمون خودکار، یکپارچه و End-to-End | NOT STARTED | — | NOT RUN | NOT RUN | NOT RUN | NOT RUN | — | — |
| P23 — فاز 23 — کارایی، پایداری و ممیزی آفلاین | NOT STARTED | — | NOT RUN | NOT RUN | NOT RUN | NOT RUN | — | — |
| P24 — فاز 24 — بسته‌بندی، نصب و به‌روزرسانی آفلاین | NOT STARTED | — | NOT RUN | NOT RUN | NOT RUN | NOT RUN | — | — |
| P25 — فاز 25 — استقرار آزمایشی، بهره‌برداری و آموزش | NOT STARTED | — | NOT RUN | NOT RUN | NOT RUN | NOT RUN | — | — |
| P26 — فاز 26 — نگهداری، پشتیبانی و رگرسیون نسخه‌ها | NOT STARTED | — | NOT RUN | NOT RUN | NOT RUN | NOT RUN | — | — |

## تصمیم‌های باز

| ID | پرسش/تناقض | اثر | گزینه‌ها | تصمیم‌گیر | وضعیت | لینک شواهد |
|---|---|---|---|---|---|---|
| DEC-001 | مدل تجاری/مالکیت محصول برای هر گردش | مالی/موجودی/صافی | خدمت سورتینگ؛ خریدوفروش؛ ترکیبی | صاحب کسب‌وکار | OPEN | — |
| DEC-002 | فرمول دقیق صافی، پایه درصد و گردکردن | حسابداری | ثبت گزینه‌ها بعد از مثال واقعی | صاحب کسب‌وکار/مالی | OPEN | — |
| DEC-003 | تک‌رایانه یا چندکاربره همزمان | persistence/قفل‌گذاری | تک‌رایانه؛ shared service؛ گزینه دیگر | مسئول فنی/صاحب کسب‌وکار | OPEN | — |
| DEC-004 | هدف قطعی Windows 7 و سطح ریسک پذیرفته‌شده | runtime/امنیت | الزام سخت؛ گذار به OS جدید | صاحب محصول | OPEN | — |
| DEC-005 | تقویم/منطقه زمانی/شماره‌گذاری اسناد | گزارش/داده تاریخی | مصوب‌شده در ADR | صاحب محصول | OPEN | — |
