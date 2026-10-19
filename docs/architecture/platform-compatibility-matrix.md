# ماتریس سازگاری پلتفرم — وضعیت واقعی (Platform Compatibility Matrix)

- مرجع تصمیم: `docs/architecture/ADR-0001-platform-and-runtime.md`
- تاریخ به‌روزرسانی: 2026-10-19
- محیط مرجع اندازه‌گیری: Linux (sandbox), Python 3.11.2, SQLite 3.40.1 — **بدون** tkinter

## تعریف وضعیت‌ها

| برچسب | معنی |
|---|---|
| `VERIFIED` | روی همان محیط/سیستم‌عامل هدف با آزمون واقعی تأیید شده است. |
| `TESTED` | با آزمون خودکار روی محیط توسعه تأیید شده (نه لزوماً سیستم‌عامل هدف). |
| `DESIGNED` | طراحی/پیاده‌سازی شده ولی آزمون اجرایی در دسترس نبوده. |
| `NOT VERIFIED ON TARGET OS` | ادعای سازگاری با سیستم‌عامل هدف **نداریم**؛ فقط طراحی شده. |
| `NOT RUN` | امکان اجرا در این محیط نبوده (مثلاً GUI بدون tkinter). |

## سازگاری پلتفرم‌های هدف

| قلم | Windows 7 SP1 x64 | Windows 10/11 x64 | Linux (توسعه/CI) | وضعیت |
|---|---|---|---|---|
| اجرای هستهٔ دامنه/مالی | Python 3.8.10 | Python 3.11 | Python 3.11.2 | `TESTED` (۱۲۳ تست) |
| SQLite (schema v2 + migration) | بله (stdlib) | بله | ۳.۴۰.۱ | `TESTED` |
| تقویم شمسی آفلاین | بله (بدون API) | بله | بله | `TESTED` (۱۴ لنگر + ۷۳٬۳۲۳ روز) |
| رابط Tkinter | `NOT VERIFIED ON TARGET OS` | `NOT RUN` | `NOT RUN` (tkinter نصب نیست) | `DESIGNED` |
| چاپ (متن/PLAIN) | `NOT VERIFIED ON TARGET OS` | `NOT RUN` | `TESTED` (رندر متنی) | `TESTED` برای منطق |
| PDF/چاپگر | `NOT VERIFIED ON TARGET OS` | `NOT RUN` | `NOT RUN` | `DESIGNED` |
| ساخت EXE | `NOT RUN` | `NOT RUN` | `NOT RUN` | `NOT RUN` (پرچم Win7 لازم) |
| نصب‌کننده | `NOT RUN` | `NOT RUN` | `NOT RUN` | `NOT RUN` |
| بکاپ/بازیابی | بله (sqlite backup API) | بله | بله | `TESTED` |
| تطبیق فایل بانکی CSV | بله | بله | بله | `TESTED` |
| احراز هویت/رمز PBKDF2 | بله (`hashlib`) | بله | بله | `TESTED` |
| گزارش‌گیری و چاپ واحد صریح | بله | بله | بله | `TESTED` |

## محدودیت‌های محیط آزمون (چرا «سازگار» ادعا نمی‌شود)

- این محیط لینوکسی است و **tkinter نصب نیست** ⇒ هیچ پنجره‌ای باز نشده و هیچ تصویر UI ثبت نشده است.
- Windows 7 SP1 x64 در دسترس نیست ⇒ هیچ ادعای «سازگار با ویندوز ۷» مجاز نیست.
- PyInstaller/NSIS نصب نیست ⇒ ساخت EXE و نصب‌کننده `NOT RUN` است.
- بدون اینترنت عملیاتی: هیچ مسیر runtime به شبکه وابسته نیست (قابل بازرسی در کد؛ تست خودکارِ
  «بدون شبکه» در Prompt 27 افزوده می‌شود).

## نتیجهٔ تصمیم

- گزینهٔ منتخب: **Python 3.8+ / Tkinter / SQLite** (ADR-0001، Accepted).
- تا زمانی که آزمون روی Windows 7 SP1 x64 اجرا نشود، وضعیت سازگاری W7 همیشه
  `NOT VERIFIED ON TARGET OS` باقی می‌ماند و در گزارش‌ها نیز همین‌طور درج می‌شود.
- بسته‌بندی: `ADR-0002` باز است (PyInstaller با پرچم Win7 در برابر بستهٔ ZIP + launcher).

## نقاط باز

- `ADR-0002` — روش نهایی packaging و آزمون روی W7.
- `ADR-0003` — تأیید تقویم شمسی توسط کسب‌وکار (موتور پیاده شده و آزمون‌شده، اما «رسمی» نیست).
- `ADR-0004` — سیاست نسخهٔ schema و recovery (نسخه‌دار شد، اما سیاست نگهداری نسخه‌ها باز است).
