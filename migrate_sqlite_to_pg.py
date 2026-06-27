#!/usr/bin/env python3
"""Migrate data from local SQLite database to Neon PostgreSQL."""

import sqlite3
import psycopg2
import psycopg2.extras

SQLITE_PATH = "/Users/br_puri/Downloads/skladpro_v2/skladpro.db"
DATABASE_URL = "postgresql://neondb_owner:npg_O0TCzu7hFocp@ep-jolly-sea-atoft6o9-pooler.c-9.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"

# Tables in FK-safe insertion order (parents before children)
TABLE_ORDER = [
    "settings",
    "users",
    "warehouses",
    "categories",
    "contacts",
    "products",
    "stock",
    "exchange_rates",
    "discounts",
    "quotes",
    "quote_items",
    "sales",
    "sale_items",
    "purchases",
    "purchase_items",
    "transactions",
    "credit_notes",
    "credit_note_items",
    "debit_notes",
    "debit_note_items",
    "transfers",
    "writeoffs",
    "writeoff_items",
    "inventory_counts",
    "inventory_count_items",
    "supplier_orders",
    "supplier_order_items",
    "audit_log",
    # Extra tables that exist in SQLite (may not be in PG - will skip if missing)
    "catalog_category_order",
    "catalog_product_order",
    "catalog_subcategory_order",
    "contact_history",
    "invoice_payments",
    "ttns",
]

def get_pg_tables(pg_cur):
    pg_cur.execute("""
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
    """)
    return {r[0] for r in pg_cur.fetchall()}

def get_pg_columns(pg_cur, table):
    pg_cur.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = %s
        ORDER BY ordinal_position
    """, (table,))
    return [r[0] for r in pg_cur.fetchall()]

def migrate():
    sq = sqlite3.connect(SQLITE_PATH)
    sq.row_factory = sqlite3.Row

    pg = psycopg2.connect(DATABASE_URL)
    pg.autocommit = False
    pg_cur = pg.cursor()

    # Get available PG tables
    pg_tables = get_pg_tables(pg_cur)
    print(f"PostgreSQL has {len(pg_tables)} tables: {sorted(pg_tables)}\n")

    # Get SQLite tables
    sq_tables = {r[0] for r in sq.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name != 'sqlite_sequence'"
    ).fetchall()}

    # Insert in FK-safe order (parents before children)

    total_rows = 0
    for table in TABLE_ORDER:
        if table not in sq_tables:
            print(f"  SKIP {table} (not in SQLite)")
            continue
        if table not in pg_tables:
            print(f"  SKIP {table} (not in PostgreSQL)")
            continue

        # Get columns that exist in BOTH SQLite and PostgreSQL
        sq_cols_raw = [d[0] for d in sq.execute(f"SELECT * FROM {table} LIMIT 0").description or []]
        pg_cols = get_pg_columns(pg_cur, table)

        # Find intersection (columns in both)
        pg_cols_set = set(pg_cols)
        cols = [c for c in sq_cols_raw if c in pg_cols_set]

        if not cols:
            print(f"  SKIP {table} (no matching columns)")
            continue

        rows = sq.execute(f'SELECT {", ".join(repr(c) if c == "desc" else c for c in cols)} FROM {table}').fetchall()
        if not rows:
            print(f"  {table}: 0 rows (empty)")
            continue

        # Build INSERT with quoted column names for reserved words
        quoted_cols = [f'"{c}"' if c in ("desc", "user", "order", "group", "table") else c for c in cols]
        placeholders = ", ".join(["%s"] * len(cols))
        sql = f'INSERT INTO {table} ({", ".join(quoted_cols)}) VALUES ({placeholders}) ON CONFLICT DO NOTHING'

        count = 0
        for row in rows:
            values = [row[i] for i in range(len(cols))]
            try:
                pg_cur.execute(sql, values)
                count += 1
            except Exception as e:
                pg.rollback()
                print(f"    ERROR row in {table}: {e} | values={values[:3]}...")
                break

        pg.commit()
        total_rows += count
        print(f"  {table}: {count}/{len(rows)} rows migrated")

    # Reset sequences for all SERIAL columns
    print("\nResetting sequences...")
    pg_cur.execute("""
        SELECT sequence_name FROM information_schema.sequences
        WHERE sequence_schema = 'public'
    """)
    sequences = [r[0] for r in pg_cur.fetchall()]
    for seq in sequences:
        # Derive table and column from sequence name (pattern: tablename_columnname_seq)
        parts = seq.rsplit("_seq", 1)[0].rsplit("_", 1)
        if len(parts) == 2:
            tbl, col = parts
            try:
                pg_cur.execute(f"SELECT setval('{seq}', COALESCE((SELECT MAX({col}) FROM {tbl}), 1))")
                pg.commit()
                print(f"  Reset {seq}")
            except Exception as e:
                pg.rollback()
                print(f"  Could not reset {seq}: {e}")

    print(f"\nDone! Total rows migrated: {total_rows}")
    sq.close()
    pg_cur.close()
    pg.close()

if __name__ == "__main__":
    migrate()
