# ماتریس وابستگی‌ها و سازگاری

این فایل باید پیش از تثبیت stack و برای هر انتشار تکمیل شود. عباراتی مانند «آخرین نسخه» برای dependency release قابل قبول نیست.

| Dependency | Exact version | Purpose | License | Target framework | Windows 7 test | Offline included | Native architecture | Security/update notes |
|---|---|---|---|---|---|---|---|---|
| .NET Framework | TBD | Runtime | Microsoft terms | TBD | Not tested | Installer/prereq plan required | x64 target | See official support matrix |
| WPF | Runtime framework | Desktop UI | Framework | TBD | Not tested | Included through runtime | x64 target | Verify DPI/RTL |
| SQLite provider | TBD | Embedded DB | Must verify | TBD | Not tested | DLLs shipped locally | x64 | Test backup, transaction and native DLL |
| Report/print library | TBD | Reports | Must verify | TBD | Not tested | Must be local | TBD | Verify Persian shaping and license |
| Chart library | TBD | Dashboard charts | Must verify | TBD | Not tested | Must be local | TBD | Avoid external scripts/CDN |

## Validation rule

برای هر ردیف، وضعیت باید یکی از این مقادیر باشد: `Not evaluated`, `Documented`, `Tested`, `Rejected`. تنها `Tested` با evidence قابل پیوست، اثبات سازگاری پروژه‌ای محسوب می‌شود.

## Evidence record

- Tested build:
- OS version/service pack:
- VM/physical system:
- Runtime version:
- Installer hash:
- Test date:
- Test operator:
- Test result and known issues:
