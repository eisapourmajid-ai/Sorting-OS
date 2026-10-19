# -*- coding: utf-8 -*-
"""Versioned, transactional schema migrations for SORTING OS.

Rules (see ``docs/02-data-model.md`` section 7 and Prompt 06):

1. every migration has a number and a description;
2. migrations are executed inside a transaction;
3. they are tested on an empty database *and* on a database created with the
   previous version;
4. a failure leaves no half-migrated data behind;
5. migrations are additive only - no table is dropped and no column is
   rewritten, so historic operational and ledger data stays intact.

Money columns are always ``INTEGER`` rials; weights are stored in kilogram
(``REAL`` is acceptable for physical measurements, never for money).
"""
from __future__ import annotations

# --------------------------------------------------------------------------- #
# Migration 1 - the operational schema shipped with the MVP
# --------------------------------------------------------------------------- #
MIGRATION_1 = [
    (
        "operational schema (parties, shipments, weighing, invoices, audit)",
        [
            """CREATE TABLE IF NOT EXISTS schema_meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )""",
            """CREATE TABLE IF NOT EXISTS parties (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE,
                display_name TEXT NOT NULL,
                phone TEXT,
                national_id TEXT,
                address TEXT,
                roles TEXT NOT NULL DEFAULT 'مالک کالا',
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )""",
            "CREATE INDEX IF NOT EXISTS ix_parties_name ON parties(display_name)",
            "CREATE INDEX IF NOT EXISTS ix_parties_national_id ON parties(national_id)",
            "CREATE INDEX IF NOT EXISTS ix_parties_phone ON parties(phone)",
            """CREATE TABLE IF NOT EXISTS shipments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                owner_party_id INTEGER NOT NULL REFERENCES parties(id),
                product_name TEXT NOT NULL,
                received_weight REAL NOT NULL CHECK(received_weight >= 0),
                received_at TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'دریافت‌شده',
                notes TEXT,
                created_at TEXT NOT NULL
            )""",
            "CREATE INDEX IF NOT EXISTS ix_shipments_owner ON shipments(owner_party_id)",
            "CREATE INDEX IF NOT EXISTS ix_shipments_received_at ON shipments(received_at)",
            """CREATE TABLE IF NOT EXISTS weighing_tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                ticket_type TEXT NOT NULL,
                shipment_id INTEGER REFERENCES shipments(id),
                vehicle_plate TEXT,
                driver_name TEXT,
                gross_weight REAL NOT NULL CHECK(gross_weight >= 0),
                tare_weight REAL NOT NULL CHECK(tare_weight >= 0),
                net_weight REAL NOT NULL CHECK(net_weight >= 0),
                weighed_at TEXT NOT NULL,
                operator_name TEXT,
                notes TEXT,
                created_at TEXT NOT NULL,
                CHECK(gross_weight >= tare_weight)
            )""",
            "CREATE INDEX IF NOT EXISTS ix_weighings_shipment ON weighing_tickets(shipment_id)",
            """CREATE TABLE IF NOT EXISTS invoices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                party_id INTEGER NOT NULL REFERENCES parties(id),
                invoice_type TEXT NOT NULL,
                document_date TEXT NOT NULL,
                amount REAL NOT NULL CHECK(amount >= 0),
                description TEXT,
                shipment_id INTEGER REFERENCES shipments(id),
                status TEXT NOT NULL DEFAULT 'پیش‌نویس',
                created_at TEXT NOT NULL,
                created_by TEXT
            )""",
            "CREATE INDEX IF NOT EXISTS ix_invoices_party ON invoices(party_id)",
            "CREATE INDEX IF NOT EXISTS ix_invoices_date ON invoices(document_date)",
            """CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_at TEXT NOT NULL,
                actor TEXT NOT NULL,
                action TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                entity_id TEXT,
                details TEXT
            )""",
        ],
    ),
]

# --------------------------------------------------------------------------- #
# Migration 2 - domain, finance and operations extensions
# --------------------------------------------------------------------------- #
MIGRATION_2 = [
    (
        "party identity, roles, merge review queue",
        [
            "ALTER TABLE parties ADD COLUMN legal_name TEXT",
            "ALTER TABLE parties ADD COLUMN notes TEXT",
            "ALTER TABLE parties ADD COLUMN created_by TEXT",
            "ALTER TABLE parties ADD COLUMN updated_by TEXT",
            "ALTER TABLE parties ADD COLUMN normalized_name TEXT",
            """CREATE TABLE IF NOT EXISTS party_roles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                party_id INTEGER NOT NULL REFERENCES parties(id),
                role_code TEXT NOT NULL,
                valid_from TEXT NOT NULL,
                valid_to TEXT,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                created_by TEXT,
                UNIQUE(party_id, role_code, valid_from)
            )""",
            """CREATE TABLE IF NOT EXISTS party_aliases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                party_id INTEGER NOT NULL REFERENCES parties(id),
                alias_text TEXT NOT NULL,
                alias_type TEXT NOT NULL DEFAULT 'نام',
                created_at TEXT NOT NULL
            )""",
            """CREATE TABLE IF NOT EXISTS party_match_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_party_id INTEGER NOT NULL REFERENCES parties(id),
                candidate_party_id INTEGER NOT NULL REFERENCES parties(id),
                score REAL NOT NULL,
                reason TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'open' CHECK(status IN ('open','merged','dismissed')),
                decided_by TEXT,
                decided_at TEXT,
                created_at TEXT NOT NULL,
                UNIQUE(source_party_id, candidate_party_id)
            )""",
            """CREATE TABLE IF NOT EXISTS party_merge_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                merged_party_id INTEGER NOT NULL,
                target_party_id INTEGER NOT NULL,
                actor TEXT NOT NULL,
                merged_at TEXT NOT NULL,
                details TEXT
            )""",
            "CREATE INDEX IF NOT EXISTS ix_parties_normalized ON parties(normalized_name)",
        ],
    ),
    (
        "product, grade and packaging master data",
        [
            """CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                category TEXT,
                base_unit TEXT NOT NULL DEFAULT 'کیلوگرم',
                is_active INTEGER NOT NULL DEFAULT 1,
                notes TEXT,
                created_at TEXT NOT NULL,
                created_by TEXT
            )""",
            """CREATE TABLE IF NOT EXISTS grades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                sort_order INTEGER NOT NULL DEFAULT 0,
                is_active INTEGER NOT NULL DEFAULT 1
            )""",
            """CREATE TABLE IF NOT EXISTS packaging_types (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                reference_weight_kg REAL,
                count_unit TEXT NOT NULL DEFAULT 'سبد',
                is_active INTEGER NOT NULL DEFAULT 1
            )""",
            """CREATE TABLE IF NOT EXISTS product_packaging_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL REFERENCES products(id),
                grade_id INTEGER REFERENCES grades(id),
                packaging_id INTEGER NOT NULL REFERENCES packaging_types(id),
                valid_from TEXT NOT NULL,
                valid_to TEXT,
                is_active INTEGER NOT NULL DEFAULT 1
            )""",
        ],
    ),
    (
        "shipment lines, multi-shipment weighing, sorting and mass balance",
        [
            "ALTER TABLE shipments ADD COLUMN delivering_party_id INTEGER REFERENCES parties(id)",
            "ALTER TABLE shipments ADD COLUMN ownership_model TEXT NOT NULL DEFAULT 'undetermined'",
            "ALTER TABLE shipments ADD COLUMN contract_ref TEXT",
            "ALTER TABLE shipments ADD COLUMN current_state TEXT NOT NULL DEFAULT 'received'",
            "ALTER TABLE shipments ADD COLUMN updated_at TEXT",
            """CREATE TABLE IF NOT EXISTS shipment_lines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                shipment_id INTEGER NOT NULL REFERENCES shipments(id),
                product_id INTEGER REFERENCES products(id),
                grade_id INTEGER REFERENCES grades(id),
                packaging_id INTEGER REFERENCES packaging_types(id),
                description TEXT,
                quantity REAL NOT NULL DEFAULT 0,
                unit TEXT NOT NULL DEFAULT 'کیلوگرم',
                weight_kg REAL NOT NULL DEFAULT 0 CHECK(weight_kg >= 0),
                created_at TEXT NOT NULL
            )""",
            "CREATE INDEX IF NOT EXISTS ix_shipment_lines_shipment ON shipment_lines(shipment_id)",
            """CREATE TABLE IF NOT EXISTS weighing_ticket_shipments (
                weighing_ticket_id INTEGER NOT NULL REFERENCES weighing_tickets(id),
                shipment_id INTEGER NOT NULL REFERENCES shipments(id),
                weight_kg REAL NOT NULL DEFAULT 0 CHECK(weight_kg >= 0),
                PRIMARY KEY(weighing_ticket_id, shipment_id)
            )""",
            """CREATE TABLE IF NOT EXISTS sorting_operations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                shipment_id INTEGER NOT NULL REFERENCES shipments(id),
                input_weight_kg REAL NOT NULL CHECK(input_weight_kg >= 0),
                waste_weight_kg REAL NOT NULL DEFAULT 0 CHECK(waste_weight_kg >= 0),
                loss_weight_kg REAL NOT NULL DEFAULT 0 CHECK(loss_weight_kg >= 0),
                difference_weight_kg REAL NOT NULL DEFAULT 0,
                measured_at TEXT NOT NULL,
                operator TEXT,
                status TEXT NOT NULL DEFAULT 'draft' CHECK(status IN ('draft','confirmed','cancelled')),
                notes TEXT,
                created_at TEXT NOT NULL,
                created_by TEXT
            )""",
            """CREATE TABLE IF NOT EXISTS sorting_output_lines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                operation_id INTEGER NOT NULL REFERENCES sorting_operations(id),
                line_type TEXT NOT NULL CHECK(line_type IN ('output','waste','loss','difference')),
                product_id INTEGER REFERENCES products(id),
                grade_id INTEGER REFERENCES grades(id),
                packaging_id INTEGER REFERENCES packaging_types(id),
                weight_kg REAL NOT NULL CHECK(weight_kg >= 0),
                package_count INTEGER NOT NULL DEFAULT 0,
                description TEXT,
                created_at TEXT NOT NULL
            )""",
            "CREATE INDEX IF NOT EXISTS ix_sorting_lines_op ON sorting_output_lines(operation_id)",
        ],
    ),
    (
        "inventory ledger, locations and reservations",
        [
            """CREATE TABLE IF NOT EXISTS inventory_locations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                kind TEXT NOT NULL DEFAULT 'warehouse',
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
            )""",
            """CREATE TABLE IF NOT EXISTS inventory_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_at TEXT NOT NULL,
                movement_type TEXT NOT NULL,
                product_id INTEGER REFERENCES products(id),
                grade_id INTEGER REFERENCES grades(id),
                packaging_id INTEGER REFERENCES packaging_types(id),
                shipment_id INTEGER REFERENCES shipments(id),
                location_id INTEGER REFERENCES inventory_locations(id),
                quantity REAL NOT NULL DEFAULT 0,
                unit TEXT NOT NULL DEFAULT 'کیلوگرم',
                weight_kg REAL NOT NULL DEFAULT 0,
                source_type TEXT NOT NULL,
                source_id TEXT NOT NULL,
                source_line_id TEXT NOT NULL DEFAULT '',
                purpose TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'posted' CHECK(status IN ('posted','reversed')),
                actor TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(source_type, source_id, source_line_id, purpose)
            )""",
            "CREATE INDEX IF NOT EXISTS ix_inventory_tx_product ON inventory_transactions(product_id, grade_id, status)",
            "CREATE INDEX IF NOT EXISTS ix_inventory_tx_shipment ON inventory_transactions(shipment_id)",
            """CREATE TABLE IF NOT EXISTS inventory_reservations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                shipment_id INTEGER REFERENCES shipments(id),
                product_id INTEGER REFERENCES products(id),
                grade_id INTEGER REFERENCES grades(id),
                location_id INTEGER REFERENCES inventory_locations(id),
                party_id INTEGER REFERENCES parties(id),
                quantity REAL NOT NULL DEFAULT 0,
                weight_kg REAL NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active','released','consumed')),
                expires_at TEXT,
                created_at TEXT NOT NULL,
                created_by TEXT
            )""",
        ],
    ),
    (
        "dispatch (outbound) documents",
        [
            """CREATE TABLE IF NOT EXISTS dispatches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                carrier_party_id INTEGER REFERENCES parties(id),
                vehicle_plate TEXT,
                driver_name TEXT,
                dispatched_at TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'draft' CHECK(status IN ('draft','confirmed','cancelled')),
                note TEXT,
                created_at TEXT NOT NULL,
                created_by TEXT
            )""",
            """CREATE TABLE IF NOT EXISTS dispatch_lines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dispatch_id INTEGER NOT NULL REFERENCES dispatches(id),
                shipment_id INTEGER REFERENCES shipments(id),
                product_id INTEGER REFERENCES products(id),
                grade_id INTEGER REFERENCES grades(id),
                packaging_id INTEGER REFERENCES packaging_types(id),
                weight_kg REAL NOT NULL DEFAULT 0 CHECK(weight_kg >= 0),
                package_count INTEGER NOT NULL DEFAULT 0,
                billing_weight_kg REAL,
                billing_basis TEXT NOT NULL DEFAULT 'dispatched',
                note TEXT,
                created_at TEXT NOT NULL
            )""",
            "CREATE INDEX IF NOT EXISTS ix_dispatch_lines_dispatch ON dispatch_lines(dispatch_id)",
        ],
    ),
    (
        "invoice lines in integer rials, expenses and allocations",
        [
            "ALTER TABLE invoices ADD COLUMN amount_rial INTEGER",
            "ALTER TABLE invoices ADD COLUMN due_date TEXT",
            "ALTER TABLE invoices ADD COLUMN currency_unit TEXT",
            "ALTER TABLE invoices ADD COLUMN doc_number TEXT",
            "ALTER TABLE invoices ADD COLUMN kind TEXT NOT NULL DEFAULT 'sales'",
            "ALTER TABLE invoices ADD COLUMN posted_entry_id INTEGER",
            "ALTER TABLE invoices ADD COLUMN approved_by TEXT",
            "ALTER TABLE invoices ADD COLUMN posted_at TEXT",
            "ALTER TABLE invoices ADD COLUMN notes TEXT",
            """CREATE TABLE IF NOT EXISTS invoice_lines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_id INTEGER NOT NULL REFERENCES invoices(id),
                product_id INTEGER REFERENCES products(id),
                grade_id INTEGER REFERENCES grades(id),
                packaging_id INTEGER REFERENCES packaging_types(id),
                description TEXT,
                quantity REAL NOT NULL DEFAULT 0,
                unit TEXT NOT NULL DEFAULT 'کیلوگرم',
                unit_price_rial INTEGER NOT NULL DEFAULT 0 CHECK(unit_price_rial >= 0),
                weight_kg REAL NOT NULL DEFAULT 0 CHECK(weight_kg >= 0),
                billing_weight_kg REAL,
                discount_rial INTEGER NOT NULL DEFAULT 0 CHECK(discount_rial >= 0),
                line_total_rial INTEGER NOT NULL DEFAULT 0 CHECK(line_total_rial >= 0),
                shipment_id INTEGER REFERENCES shipments(id),
                sort_order INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            )""",
            "CREATE INDEX IF NOT EXISTS ix_invoice_lines_invoice ON invoice_lines(invoice_id)",
            """CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                category TEXT NOT NULL,
                amount_rial INTEGER NOT NULL CHECK(amount_rial >= 0),
                expense_date TEXT NOT NULL,
                party_id INTEGER REFERENCES parties(id),
                payment_method TEXT NOT NULL DEFAULT 'cash',
                status TEXT NOT NULL DEFAULT 'recorded' CHECK(status IN ('recorded','approved','paid','cancelled')),
                is_billable INTEGER NOT NULL DEFAULT 0,
                recognized_entry_id INTEGER,
                note TEXT,
                created_at TEXT NOT NULL,
                created_by TEXT
            )""",
            """CREATE TABLE IF NOT EXISTS expense_allocations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                expense_id INTEGER NOT NULL REFERENCES expenses(id),
                target_type TEXT NOT NULL,
                target_id INTEGER NOT NULL,
                amount_rial INTEGER NOT NULL CHECK(amount_rial >= 0),
                method TEXT NOT NULL DEFAULT 'manual',
                created_at TEXT NOT NULL
            )""",
        ],
    ),
    (
        "versioned settlement engine",
        [
            """CREATE TABLE IF NOT EXISTS settlement_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                kind TEXT NOT NULL CHECK(kind IN ('commission','deduction','addition')),
                method TEXT NOT NULL CHECK(method IN ('percent','fixed')),
                basis TEXT NOT NULL CHECK(basis IN ('gross','net','contract')),
                scope TEXT NOT NULL DEFAULT 'shipment',
                rate_percent REAL,
                amount_rial INTEGER,
                cap_rial INTEGER,
                floor_rial INTEGER,
                payer_party_id INTEGER REFERENCES parties(id),
                valid_from TEXT NOT NULL,
                valid_to TEXT,
                is_active INTEGER NOT NULL DEFAULT 1,
                notes TEXT,
                created_at TEXT NOT NULL,
                created_by TEXT
            )""",
            """CREATE TABLE IF NOT EXISTS settlements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                party_id INTEGER NOT NULL REFERENCES parties(id),
                shipment_id INTEGER REFERENCES shipments(id),
                calculation_mode TEXT NOT NULL CHECK(calculation_mode IN ('net_amount_input','net_rate_input')),
                reference_amount_rial INTEGER NOT NULL DEFAULT 0,
                net_rate_percent REAL,
                net_amount_rial INTEGER NOT NULL DEFAULT 0,
                commission_rial INTEGER NOT NULL DEFAULT 0,
                deductions_rial INTEGER NOT NULL DEFAULT 0,
                additions_rial INTEGER NOT NULL DEFAULT 0,
                formula_version TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'draft' CHECK(status IN ('draft','approved','posted','cancelled')),
                approved_by TEXT,
                approved_at TEXT,
                posted_entry_id INTEGER,
                payload_json TEXT,
                created_at TEXT NOT NULL,
                created_by TEXT
            )""",
            """CREATE TABLE IF NOT EXISTS settlement_lines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                settlement_id INTEGER NOT NULL REFERENCES settlements(id),
                product_id INTEGER REFERENCES products(id),
                grade_id INTEGER REFERENCES grades(id),
                packaging_id INTEGER REFERENCES packaging_types(id),
                dispatched_weight_kg REAL NOT NULL DEFAULT 0,
                declared_weight_kg REAL,
                unit_price_rial INTEGER NOT NULL DEFAULT 0,
                gross_amount_rial INTEGER NOT NULL DEFAULT 0,
                line_total_rial INTEGER NOT NULL DEFAULT 0,
                basis TEXT NOT NULL DEFAULT 'dispatched',
                created_at TEXT NOT NULL
            )""",
            """CREATE TABLE IF NOT EXISTS settlement_adjustments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                settlement_id INTEGER NOT NULL REFERENCES settlements(id),
                adjustment_type TEXT NOT NULL CHECK(adjustment_type IN ('discount','addition','expense','shortage','other')),
                amount_rial INTEGER NOT NULL,
                basis TEXT,
                reason TEXT,
                source_type TEXT,
                source_id TEXT,
                status TEXT NOT NULL DEFAULT 'draft' CHECK(status IN ('draft','approved','rejected')),
                approved_by TEXT,
                created_at TEXT NOT NULL,
                created_by TEXT
            )""",
        ],
    ),
    (
        "bank accounts, statement import, reconciliation, cheques and payments",
        [
            """CREATE TABLE IF NOT EXISTS bank_accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                bank_name TEXT,
                account_number_masked TEXT,
                currency TEXT NOT NULL DEFAULT 'IRR',
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
            )""",
            """CREATE TABLE IF NOT EXISTS bank_statements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bank_account_id INTEGER NOT NULL REFERENCES bank_accounts(id),
                file_name TEXT,
                imported_at TEXT NOT NULL,
                imported_by TEXT NOT NULL,
                unit TEXT NOT NULL,
                row_count INTEGER NOT NULL DEFAULT 0,
                checksum TEXT,
                status TEXT NOT NULL DEFAULT 'preview' CHECK(status IN ('preview','committed','failed')),
                created_at TEXT NOT NULL
            )""",
            """CREATE TABLE IF NOT EXISTS bank_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                statement_id INTEGER NOT NULL REFERENCES bank_statements(id),
                row_no INTEGER NOT NULL,
                transaction_date TEXT NOT NULL,
                description TEXT,
                amount_rial INTEGER NOT NULL CHECK(amount_rial >= 0),
                direction TEXT NOT NULL CHECK(direction IN ('in','out')),
                reference TEXT,
                external_id TEXT,
                status TEXT NOT NULL DEFAULT 'unmatched' CHECK(status IN ('unmatched','matched','ignored','posted')),
                matched_type TEXT,
                matched_id INTEGER,
                created_at TEXT NOT NULL,
                UNIQUE(statement_id, row_no)
            )""",
            """CREATE TABLE IF NOT EXISTS bank_matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transaction_id INTEGER NOT NULL REFERENCES bank_transactions(id),
                target_type TEXT NOT NULL,
                target_id INTEGER NOT NULL,
                confidence REAL NOT NULL,
                status TEXT NOT NULL DEFAULT 'suggested' CHECK(status IN ('suggested','accepted','rejected')),
                decided_by TEXT,
                decided_at TEXT,
                note TEXT,
                created_at TEXT NOT NULL
            )""",
            """CREATE TABLE IF NOT EXISTS cheques (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                cheque_type TEXT NOT NULL CHECK(cheque_type IN ('received','issued')),
                party_id INTEGER REFERENCES parties(id),
                amount_rial INTEGER NOT NULL CHECK(amount_rial >= 0),
                issue_date TEXT NOT NULL,
                due_date TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'issued' CHECK(status IN ('issued','in_process','cleared','bounced','cancelled')),
                bank_account_id INTEGER REFERENCES bank_accounts(id),
                account_code TEXT,
                cleared_entry_id INTEGER,
                note TEXT,
                created_at TEXT NOT NULL,
                created_by TEXT
            )""",
            """CREATE TABLE IF NOT EXISTS cheque_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cheque_id INTEGER NOT NULL REFERENCES cheques(id),
                event_type TEXT NOT NULL,
                event_at TEXT NOT NULL,
                actor TEXT NOT NULL,
                amount_rial INTEGER,
                note TEXT
            )""",
            """CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                party_id INTEGER NOT NULL REFERENCES parties(id),
                direction TEXT NOT NULL CHECK(direction IN ('in','out')),
                amount_rial INTEGER NOT NULL CHECK(amount_rial >= 0),
                method TEXT NOT NULL DEFAULT 'cash',
                payment_date TEXT NOT NULL,
                bank_account_id INTEGER REFERENCES bank_accounts(id),
                cheque_id INTEGER REFERENCES cheques(id),
                source_type TEXT,
                source_id TEXT,
                posted_entry_id INTEGER,
                note TEXT,
                created_at TEXT NOT NULL,
                created_by TEXT
            )""",
            "CREATE INDEX IF NOT EXISTS ix_payments_party ON payments(party_id, payment_date)",
        ],
    ),
    (
        "users, roles, permissions and tamper-evident audit chain",
        [
            """CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                full_name TEXT,
                role_code TEXT NOT NULL DEFAULT 'operator',
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                last_login_at TEXT
            )""",
            """CREATE TABLE IF NOT EXISTS roles (
                code TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT
            )""",
            """CREATE TABLE IF NOT EXISTS role_permissions (
                role_code TEXT NOT NULL REFERENCES roles(code),
                permission TEXT NOT NULL,
                PRIMARY KEY(role_code, permission)
            )""",
            """CREATE TABLE IF NOT EXISTS user_roles (
                user_id INTEGER NOT NULL REFERENCES users(id),
                role_code TEXT NOT NULL REFERENCES roles(code),
                PRIMARY KEY(user_id, role_code)
            )""",
            "ALTER TABLE audit_log ADD COLUMN user_id INTEGER",
            "ALTER TABLE audit_log ADD COLUMN prev_hash TEXT",
            "ALTER TABLE audit_log ADD COLUMN entry_hash TEXT",
            "CREATE INDEX IF NOT EXISTS ix_audit_entity ON audit_log(entity_type, entity_id)",
        ],
    ),
    (
        "import/export batches and print templates",
        [
            """CREATE TABLE IF NOT EXISTS import_batches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_key TEXT UNIQUE NOT NULL,
                entity TEXT NOT NULL,
                file_name TEXT,
                unit TEXT,
                mapping_json TEXT,
                status TEXT NOT NULL DEFAULT 'preview' CHECK(status IN ('preview','committed','failed')),
                row_count INTEGER NOT NULL DEFAULT 0,
                error_count INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                created_by TEXT,
                committed_at TEXT
            )""",
            """CREATE TABLE IF NOT EXISTS import_batch_rows (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_id INTEGER NOT NULL REFERENCES import_batches(id),
                row_no INTEGER NOT NULL,
                action TEXT,
                status TEXT NOT NULL DEFAULT 'preview',
                error TEXT,
                payload_json TEXT,
                created_at TEXT NOT NULL
            )""",
            """CREATE TABLE IF NOT EXISTS export_batches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity TEXT NOT NULL,
                file_name TEXT,
                row_count INTEGER NOT NULL DEFAULT 0,
                checksum TEXT,
                created_at TEXT NOT NULL,
                created_by TEXT
            )""",
            """CREATE TABLE IF NOT EXISTS print_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL,
                name TEXT NOT NULL,
                document_type TEXT NOT NULL,
                version INTEGER NOT NULL DEFAULT 1,
                is_active INTEGER NOT NULL DEFAULT 1,
                template_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                created_by TEXT,
                UNIQUE(code, version)
            )""",
        ],
    ),
    (
        "fiscal periods, period locks and settings",
        [
            """CREATE TABLE IF NOT EXISTS fiscal_periods (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                title TEXT,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'open' CHECK(status IN ('open','closed')),
                closed_by TEXT,
                closed_at TEXT,
                closing_entry_id INTEGER,
                created_at TEXT NOT NULL
            )""",
            """CREATE TABLE IF NOT EXISTS period_locks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                period_id INTEGER NOT NULL REFERENCES fiscal_periods(id),
                locked_from TEXT NOT NULL,
                locked_until TEXT NOT NULL,
                reason TEXT,
                created_at TEXT NOT NULL,
                created_by TEXT
            )""",
            """CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TEXT NOT NULL,
                updated_by TEXT
            )""",
        ],
    ),
]

MIGRATIONS = [
    (1, "operational baseline schema", MIGRATION_1),
    (2, "domain, finance, banking, security and printing extensions", MIGRATION_2),
]

LATEST_SCHEMA_VERSION = MIGRATIONS[-1][0]
