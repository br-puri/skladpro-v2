"""One-time migration: download all Cloudinary-hosted product/supplier-order
photos and re-save them to the local NAS volume, updating the DB to point at
the new local filenames instead of Cloudinary URLs. Run once, inside the
running container, with `docker exec`.
"""
import os
import uuid
import urllib.request
import psycopg2
import psycopg2.extras

DATABASE_URL = os.environ['DATABASE_URL']
UPLOAD_FOLDER = '/app/static/uploads/products'


def download(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = resp.read()
    ext = url.rsplit('.', 1)[-1].split('?')[0].lower()
    if ext not in ('jpg', 'jpeg', 'png', 'webp', 'gif', 'avif'):
        ext = 'jpg'
    return data, ext


def main():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
    cur = conn.cursor()

    url_to_filename = {}

    def migrate_table(table):
        cur.execute(f"SELECT id, photo FROM {table} WHERE photo LIKE 'http%'")
        rows = cur.fetchall()
        print(f"{table}: {len(rows)} rows to migrate")
        for r in rows:
            url = r['photo']
            if url not in url_to_filename:
                try:
                    data, ext = download(url)
                    filename = f"{uuid.uuid4().hex}.{ext}"
                    with open(os.path.join(UPLOAD_FOLDER, filename), 'wb') as f:
                        f.write(data)
                    url_to_filename[url] = filename
                    print(f"  downloaded {url} -> {filename} ({len(data)} bytes)")
                except Exception as e:
                    print(f"  FAILED {url}: {e}")
                    continue
            filename = url_to_filename[url]
            cur.execute(f"UPDATE {table} SET photo=%s WHERE id=%s", (filename, r['id']))
        conn.commit()

    migrate_table('products')
    migrate_table('supplier_order_items')

    print(f"Done. {len(url_to_filename)} unique images downloaded.")


if __name__ == '__main__':
    main()
