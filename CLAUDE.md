# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the App

```bash
# Development (local)
python app.py
# runs on http://localhost:5001

# Production-style (gunicorn)
gunicorn --bind 0.0.0.0:8080 --workers 2 --threads 4 app:app

# With venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

Default login: `admin` / `admin123` (created automatically on first run if no users exist).

## Architecture

This is a single-file Flask application (`app.py`, ~4 600 lines) backed by PostgreSQL (Neon). There are no separate modules — all routes, DB helpers, and PDF generation live in `app.py`.

**Key globals:**
- `UPLOAD_FOLDER` — `static/uploads/products/` for product images and `static/uploads/logo.*` for the company logo.

**Database:**
- PostgreSQL via **psycopg2**. Connection URL comes from `DATABASE_URL` env var (set automatically by Render from the linked `skladpro-db` database).
- `get_db()` returns a `_Db` context-manager wrapper around a psycopg2 connection using `RealDictCursor` (rows are dicts). Commits on clean exit, rolls back on exception, closes the connection.
- `init_db()` is called at module load. It issues individual `CREATE TABLE IF NOT EXISTS` + `ALTER TABLE … ADD COLUMN IF NOT EXISTS` statements (no migration files).
- Connections are not pooled — each request opens and closes its own connection.

**Auth & roles:**
- Session-based auth. `require_login` (registered via `@app.before_request`) redirects unauthenticated requests to `/login` for all endpoints except those in `PUBLIC_ROUTES`.
- `@admin_required` decorator restricts certain routes to users with `role = 'admin'`.
- All non-GET requests (by logged-in users) are logged to `audit_log` in `write_audit` via `@app.after_request`.

**Context processor:**
- `inject_defaults()` injects `default_wh_id` into every template — the ID of the first warehouse whose name contains "brent" (case-insensitive). Templates rely on this for pre-selecting a warehouse.

**PDF generation:**
- Sales/purchase invoices are generated with **ReportLab** (`generate_invoice_pdf` and similar helpers, ~line 3 350).
- The product catalogue PDF (`/products/catalog/pdf`) is also generated with **ReportLab** — `catalog_pdf_download()` builds the PDF entirely server-side (gold cover, 4-column product grid, subcategory headers, stock badges). No Chrome or subprocess involved.

**Document numbering:**
- Sales invoices use `INV-XXXX` format where XXXX is a random 4-digit number (generated in `next_num()`).
- Purchase orders use sequential `PO-YYYYMM-NNN` style.

**Settings:**
- Company info, SMTP config, and display preferences are stored as key-value rows in the `settings` table and retrieved via `get_settings()`. Settings are passed as `co` to templates and used inside PDF generation.
- `co_hide_stock` — hides in/out-of-stock badges on the catalogue (web and PDF).

**Email:**
- `_send_email()` sends via SMTP (STARTTLS on port 587, SSL on port 465). Config comes from the `settings` table (`smtp_host`, `smtp_port`, `smtp_user`, `smtp_pass`, `smtp_from`, `smtp_tls`).

**Payment reminders:**
- `send_payment_reminders()` emails customers with outstanding invoices older than 7 days.
- A background thread (`_payment_reminder_worker`) runs this weekly automatically if `reminder_enabled` is set in Settings.
- Each invoice is reminded at most once per 7-day window (tracked in the `payment_reminders` table).
- Admin can also trigger manually via `/admin/send-reminders`.

**Frontend:**
- All CSS and JS are inline in `templates/base.html` (no build step, no bundler).
- The app registers a service worker (`static/sw.js`) for basic PWA offline caching.
- `templates/_line_items.html` is a shared partial included by sale, purchase, and quote forms for the editable line-items table.

**Contacts model:**
- A single `contacts` table covers both customers (type=`customer`) and suppliers (type=`supplier`). The `/customers` and `/purchases` routes filter by type.

**Stock:**
- The `stock` table holds `(product_id, warehouse_id, qty)`. Stock is adjusted in-place when sales are completed/cancelled, purchases received, transfers added, writeoffs confirmed, or inventory counts applied.

## Deployment

**Live URLs:**
- `https://app.neondistro.co.uk` (custom domain — primary)
- `https://skladpro-v2.onrender.com` (Render subdomain — always works)

**Stack:**
- **Render** (free web service, Docker runtime) — hosts the Flask app via gunicorn
- **Neon** (free PostgreSQL, `neondb`) — database; connection string in `DATABASE_URL` env var on Render
- **Hostinger** (`neondistro.co.uk`) — DNS; CNAME record `app → skladpro-v2.onrender.com`

**To deploy a code change:**
```bash
git add <files>
git commit -m "message"
git push origin main   # triggers auto-deploy on Render
```
GitHub remote is SSH: `git@github.com:br-puri/skladpro-v2.git`  
SSH key: `~/.ssh/id_ed25519` (public key added to GitHub as "MacBook Air - SkladPro")

**Render service:** `skladpro-v2` in project "My project → Production"  
- Runtime: Docker (auto-detected from `Dockerfile`) — `python:3.11-slim`, no system deps beyond pip packages
- `SECRET_KEY`: auto-generated by Render
- `DATABASE_URL`: set manually in Render env vars (points to Neon)

**Database (Neon):**
- Project: `skladpro-db`, database: `neondb`, user: `neondb_owner`
- Pooler endpoint: `ep-jolly-sea-atoft6o9-pooler.c-9.us-east-1.aws.neon.tech`
- Migration script: `migrate_sqlite_to_pg.py` — copies all tables from local `skladpro.db` to Neon in FK-safe order

**DNS (Hostinger):**
- Panel: `hpanel.hostinger.com → Domains → neondistro.co.uk → DNS / Nameservers`
- CNAME: `app` → `skladpro-v2.onrender.com`, TTL 14400
