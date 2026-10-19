# راهنمای اجرای مرحله‌ای عامل هوش مصنوعی

## اصل
عامل باید فقط یک پرامپت/فاز را در هر نوبت اجرا کند و تا عبور از معیار پذیرش، فاز بعد را آغاز نکند. فایل‌های پرامپت کامل در بسته مهندسی همراه این مستند قرار دارند؛ این سند برای استفاده در مخزن اصلی، خلاصه قواعد اجراست.

## روش اجرا
1. دستور مادر `docs/10-master-ai-coding-directive.md` و اسناد مستقیماً مرتبط را بخوان.
2. `git status`, branch و commit را ثبت کن؛ تغییرات کاربر را حفظ کن.
3. هدف، نیازمندی، فایل‌های درگیر، اثر migration، مجوز، گزارش/چاپ و تست‌ها را قبل از ویرایش مشخص کن.
4. کوچک‌ترین تغییر آزمون‌پذیر را انجام بده؛ از بازنویسی کل ماژول یا ساخت مدل موازی خودداری کن.
5. build و تست را اجرا کن؛ نتیجه واقعی را گزارش بده؛ `NOT RUN` را با PASS اشتباه نگیر.
6. diff و migration و اثر بر داده را بازبینی کن؛ اسناد و test mapping را به‌روز کن.
7. اگر تصمیم کسب‌وکار نامعلوم است، `OPEN DECISION` ثبت کن و کد وابسته را تا تعیین تکلیف متوقف کن.

## قالب گزارش پایان فاز
```text
PHASE STATUS: COMPLETE | PARTIAL | BLOCKED
GOAL / REQUIREMENT IDS:
BASE COMMIT / BRANCH:
CHANGED FILES:
MIGRATIONS:
BUILD COMMAND + RESULT:
TEST COMMANDS + RESULTS:
OFFLINE: PASS / FAIL / NOT RUN + EVIDENCE
WINDOWS 7: PASS / FAIL / NOT RUN + EVIDENCE
DATA SAFETY / ROLLBACK:
OPEN DECISIONS / RISKS:
NEXT RECOMMENDED STEP:
```

## قاعده توقف
اگر build یا تست حیاتی شکست خورد، schema migration ایمن نیست، داده مالی/انبار reconcile نمی‌شود، یا قابلیت به سرویس آنلاین وابسته شده است، وضعیت باید `PARTIAL` یا `BLOCKED` باشد. مرحله را با ادعای «تمام شد» نبند.
