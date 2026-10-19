# Change log

## MVP foundation
- Added offline SQLite database and initial schema.
- Added desktop screens for parties, shipments, weighings, invoices, data exchange, backup, and audit history.
- Added safe CSV import preview for party identity conflicts and CSV export.
- Added unit tests for duplicate national ID handling, weighing math, invoices, and import matching.
- Not yet built as a Windows executable or validated on Windows 7 SP1 x64.

## 2026-10-18 — Financial core and unit policy
- Added SQLite-backed double-entry ledger with balanced posting, source idempotency and reversal entries.
- Added integer-rial storage and exact Decimal-based rial/toman/million-toman formatting.
- Added trial balance, balance sheet, income statement, management cash-flow reconciliation, basic ratios and account ledger queries.
- Added accounting/reporting area to the Tkinter interface.
- Added eleven accounting-core tests; full test suite now 17/17 passes in the local package validation.
- Explicitly retained restrictions: legacy invoices are not auto-posted; Jalali calendar, closing periods, operational posting integration, Windows target, installer, and official tax/statutory compliance are not yet verified/complete.
