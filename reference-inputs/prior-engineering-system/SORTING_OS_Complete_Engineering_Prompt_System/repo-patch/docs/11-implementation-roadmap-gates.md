# نقشه جامع پیاده‌سازی، گیت‌ها و وابستگی‌ها

## اصل اجرا
ترتیب، وابستگی مفهومی است. ممیزی و گیت فناوری ممکن است ترتیب نهایی را با توجه به سورس موجود تغییر دهند؛ تغییر ترتیب باید در این سند ثبت شود. پرامپت‌ها جدا و یکی‌یکی اجرا می‌شوند.

## فازها

| فاز | موضوع | پیش‌نیاز | گیت عبور |
|---|---|---|---|
| P00 | ممیزی مخزن | دسترسی read به مخزن | baseline و status واقعی؛ feature matrix |
| P01 | نمونه عمودی/سازگاری | P00 | launch، RTL، DB write/read، restart، print preview؛ شواهد offline/OS |
| P02 | معماری/تصمیم‌ها | P00–P01 | ADRهای ضروری و تصمیم‌های متعارض آشکار |
| P03 | زیرساخت برنامه | P01–P02 | logging، settings، migrations، DB transactions، restart persistence |
| P04 | مدل داده و دامنه | P02–P03 | schema versioned، constraints، test invariants |
| P05 | کاربران/مجوز/audit | P03–P04 | tests برای عملیات مجاز/غیرمجاز و audit |
| P06 | داده‌های پایه | P04–P05 | Party چندنقشی؛ product/grade/package/vehicle/location |
| P07 | تطبیق و merge شخص | P06 | merge review، FK migration، audit و reconciliation |
| P08 | موتور عمومی import/export | P04–P06 | preview, mapping, validation, duplicate review, transactional commit |
| P09 | باسکول/محموله | P06 | وزن/شماره‌گذاری/traceability آزموده |
| P10 | سورتینگ/بسته‌بندی | P09 | mass balance و اختلاف خارج تلورانس کنترل شود |
| P11 | دفتر موجودی | P09–P10 | stock ledger، reservation، جلوگیری از دوباره‌خروج/منفی |
| P12 | حواله و ارسال | P11 | Dispatch به inventory و weigh-out وصل باشد |
| P13 | فاکتور خرید/هزینه | P04–P08/P09 | allocation و جلوگیری از هزینه تکراری |
| P14 | فاکتور فروش | P12–P13 | allocation شفاف و totals آزموده |
| P15 | صافی | P12–P14 + تصمیم فرمول | مثال‌های عددی مصوب پاس شود |
| P16 | حسابداری دوبل | P13–P15 + تصمیم مدل تجاری | debit=credit، posting idempotent، reversal و reconciliation |
| P17 | بانک/چک | P16 و P08 | batch import، match review، bank reconciliation |
| P18 | گزارش | ماژول‌های مربوط | تعریف KPI، drill-down و aggregate tests |
| P19 | طراح چاپ | P06/P09/P12/P13/P14/P15/P18 | A4/A5، RTL، چندصفحه‌ای و چاپ واقعی |
| P20 | UI/UX تکمیل | P03 و گردش‌های واقعی | تم کامل، RTL، کلیدواژه‌ها، تمام کنترل‌ها واقعی |
| P21 | backup/restore و انتقال تاریخی | P03/P08/P16 | restore از backup واقعی و reconciliation |
| P22 | آزمون سرتاسری | P06–P21 | جریان کامل مثبت و failure paths |
| P23 | کارایی/آفلاین/پایداری | baseline ثابت | شواهد network-off و حجم نماینده |
| P24 | installer/release | P01–P23 | نصب/ارتقا آفلاین، حفظ داده و recovery |
| P25 | pilot/go-live | Release Candidate | checklist و امضای stop/go |
| P26 | نگهداری/patch | نسخه عملیاتی | regression، changelog و انتشار امن |

## گیت‌های سراسری (در تمام فازها)
- Gate A: مخزن و تغییرات قبلی شناسایی شده‌اند.
- Gate B: تصمیم مالی/مالکیت نامعلوم به‌صورت پنهان فرض نشده.
- Gate C: build/test واقعی و diff review انجام شده.
- Gate D: migration در صورت تغییر schema نسخه‌دار و آزموده شده.
- Gate E: عملکرد اصلی هیچ وابستگی آنلاین جدیدی ندارد.
- Gate F: مجوزها، audit و idempotency رعایت شده‌اند.
- Gate G: مستندات و Requirement-to-Test Map به‌روز هستند.
- Gate H: شکست هر گیت باید وضعیت `BLOCKED/PARTIAL` تولید کند، نه `COMPLETE`.

## معیار عمومی پذیرش یک ماژول
1. داده از UI تا persistence و برگشت به UI واقعی است.
2. حالات موفق، نامعتبر، تکراری، لغو، retry و خطای ذخیره آزموده‌اند.
3. نقش‌ها و مجوزها از لایه کاربرد اعمال می‌شوند.
4. اثر بر موجودی/مالی واضح و ردیابی‌پذیر است.
5. گزارش، چاپ، import/export و پرونده شخص مرتبط به‌روزند.
6. راهنما/متن خطای فارسی قابل فهم است.
7. هیچ داده آزمایشی یا قابلیت نمایشی در محیط عملیاتی پنهان نیست.
