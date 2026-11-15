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

There is no test suite and no linter configured.

## Architecture

This is a single-file Flask application (`app.py`, ~4 600 lines) backed by PostgreSQL (Neon). There are no separate modules — all routes, DB helpers, and PDF generation live in `app.py`.

### Database

- PostgreSQL via **psycopg2**. Connection URL comes from `DATABASE_URL` env var (set automatically by Render from the linked `skladpro-db` database).
- `get_db()` returns a `_Db` context-manager wrapper around a psycopg2 connection using `RealDictCursor` (rows are dicts). Commits on clean exit, rolls back on exception, closes the connection.
- `init_db()` is called at module load. It issues individual `CREATE TABLE IF NOT EXISTS` + `ALTER TABLE … ADD COLUMN IF NOT EXISTS` statements (no migration files).
- Connections are not pooled — each request opens and closes its own connection.
- `next_num(prefix, table)` opens its own separate `get_db()` connection to check for number uniqueness — it does not share the caller's transaction.

**Critical psycopg2 gotcha — `cursor.lastrowid` is always `None`:**  
psycopg2's `cursor.lastrowid` returns the row OID, not the serial primary key. PostgreSQL 12+ creates tables without OIDs by default, so `lastrowid` is always `None` in this app. Whenever you need the ID of a newly inserted row, use `RETURNING id` in the INSERT and call `fetchone()['id']`:

```python
# WRONG — returns None
cur = db.execute("INSERT INTO foo(...) VALUES(...)")
new_id = cur.lastrowid  # None!

# CORRECT
cur = db.execute("INSERT INTO foo(...) VALUES(...) RETURNING id")
new_id = cur.fetchone()['id']
```

There are currently 13 places in `app.py` using `cur.lastrowid` that are affected by this bug.

### Auth & Middleware

- `require_login` (`@app.before_request`) redirects unauthenticated requests to `/login`, except endpoints in `PUBLIC_ROUTES`.
- `@admin_required` decorator restricts routes to `role = 'admin'` users.
- `write_audit` (`@app.after_request`) logs all non-GET requests (with status < 500) to the `audit_log` table.

### Context Processor

- `inject_defaults()` runs on every request and injects `default_wh_id` into every template — the ID of the first warehouse whose name contains "brent" (case-insensitive). If no such warehouse exists, it is `None`. Templates rely on this for pre-selecting a warehouse dropdown.

### Route Pattern

Most routes handle both GET and POST in one function, with all DB work inside a single `with get_db() as db:` block:

```python
@app.route('/things/add', methods=['GET', 'POST'])
@admin_required
def add_thing():
    with get_db() as db:
        # queries that run on both GET and POST
        items = db.execute("SELECT ...").fetchall()
        if request.method == 'POST':
            # insert/update logic
            db.commit()
            return redirect(url_for('things'))
    return render_template('thing_form.html', items=items)
```

### Frontend

- All CSS and JS are inline in `templates/base.html` (no build step, no bundler).
- The app registers a service worker (`static/sw.js`) for basic PWA offline caching.
- `templates/_line_items.html` is a shared partial included by sale, purchase, and quote forms. It requires these Jinja variables to be set before `{% include %}`:
  - `li_price_label` — column header text ("Price" or "Cost")
  - `li_price_field` — JS key from the products array ("price" or "cost")
  - `li_show_wh` — True/False for the per-line warehouse column
  - `li_items` — existing items list or None/[] for new documents
  - `li_edit_doc` — the sale/purchase row being edited, or None
  - `li_currency`, `li_tax`, `li_discount` — display defaults

### PDF Generation

- Sales/purchase invoices use **ReportLab** (`generate_invoice_pdf` and similar helpers, ~line 3 350).
- The product catalogue PDF (`/products/catalog/pdf`) is generated entirely server-side with ReportLab — no Chrome or subprocess.

### Document Numbering

- Sales invoices: `INV-XXXX` where XXXX is a random 4-digit number (via `next_num()`).
- Purchase orders: sequential `PO-YYYYMM-NNN` style.

### Settings

- Company info, SMTP config, and display preferences are stored as key-value rows in the `settings` table and retrieved via `get_settings()`. Passed as `co` to templates and used inside PDF generation.
- `co_hide_stock` — hides in/out-of-stock badges on the catalogue (web and PDF).

### Email & Payment Reminders

- `_send_email()` sends via SMTP (STARTTLS on port 587, SSL on port 465). Config from `settings` table.
- `send_payment_reminders()` emails customers with outstanding invoices older than 7 days. A background thread (`_payment_reminder_worker`) runs this weekly if `reminder_enabled` is set. Admin can also trigger manually via `/admin/send-reminders`.

### Contacts & Stock

- A single `contacts` table covers both customers (`type='customer'`) and suppliers (`type='supplier'`).
- The `stock` table holds `(product_id, warehouse_id, qty)`. Stock is adjusted in-place when sales are completed/cancelled, purchases received, transfers added, writeoffs confirmed, or inventory counts applied.

## Deployment

**Live URL:** `https://app.neondistro.co.uk` — routed via a Cloudflare Tunnel (`neon-nas`, Zero
Trust → Networking → Tunnels, in the Cloudflare account that owns the `neondistro.co.uk` zone) to
`http://neon:8080` on the NAS. DNS was cut over from Render on 2026-10-10.

**Stack:**
- **UGREEN NAS** (`DXP2800GT-Home`, LAN IP `192.168.0.37`) — hosts the Flask app via Docker Compose + gunicorn. This is the live deployment target.
- **Neon** (free PostgreSQL, `neondb`) — database; connection string in `DATABASE_URL`, set directly in the compose file on the NAS
- **Cloudflare Tunnel** — separate Compose project `neon-tunnel` (folder `docker/neon-tunnel` on the NAS), not tracked in this repo (only holds a `TUNNEL_TOKEN`)
- Render (`skladpro-v2.onrender.com`) still exists as a rollback path but is not the live deploy target — do not `git push` expecting it to update the live site.

**NAS access — SSH (primary deploy method):**
- Alias configured in `~/.ssh/config`: `Host skladpro-nas` → `192.168.0.37`, user `"Balram Puri"` (yes, the NAS account's Unix username has a literal space — always quote it), key `~/.ssh/skladpro_nas_ed25519`
- Connect: `ssh skladpro-nas`
- Project directory on the NAS: `/volume1/docker/neon` (this is the real filesystem path behind the Files-app's `Shared Folder/docker/neon`)
- The **active** compose file is `docker-compose.yaml`, not `compose.yaml` (there's a stale duplicate — always target `docker-compose.yaml` explicitly)
- The NAS's `rsync` binary is shadowed by a UGOS sync wrapper and does not work as plain rsync — use `scp -O` (legacy SCP protocol; the NAS's sshd doesn't support modern SFTP-based scp) instead
- The `Balram Puri` account is in the `docker` group, so `docker`/`docker compose` work without `sudo`

**To deploy a code change:**
```bash
scp -O app.py "skladpro-nas:/volume1/docker/neon/app.py"
scp -O templates/<changed>.html "skladpro-nas:/volume1/docker/neon/templates/<changed>.html"
ssh skladpro-nas "cd /volume1/docker/neon && docker compose -f docker-compose.yaml up -d --build"
curl -s -o /dev/null -w '%{http_code}\n' https://app.neondistro.co.uk/login   # expect 200
```
`docker compose up -d --build` handles the full rebuild/recreate in one step — no manual
container/image deletion needed (that was only required when driving the NAS's GUI Docker app via
screenshots, before SSH access was set up on 2026-10-18).

**Database (Neon):**
- Project: `skladpro-db`, database: `neondb`, user: `neondb_owner`
- Pooler endpoint: `ep-jolly-sea-atoft6o9-pooler.c-9.us-east-1.aws.neon.tech`
- Migration script: `migrate_sqlite_to_pg.py` — copies all tables from local `skladpro.db` to Neon in FK-safe order

**DNS (Hostinger):**
- Panel: `hpanel.hostinger.com → Domains → neondistro.co.uk → DNS / Nameservers`
- CNAME: `app` → `skladpro-v2.onrender.com`, TTL 14400
