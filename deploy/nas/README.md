# NEON on UGREEN NAS

This deployment keeps the current Neon database and Cloudinary photos.

**Status (2026-10-10): DNS has been cut over.** `app.neondistro.co.uk` now routes through the
`neon-nas` Cloudflare Tunnel (Zero Trust → Networking → Tunnels, in the Cloudflare account that
owns the `neondistro.co.uk` zone) to `http://neon:8080` on the NAS. The tunnel connector runs as
its own Docker Compose project on the NAS (`neon-tunnel`, folder `docker/neon-tunnel`) — separate
from this app's `compose.yaml` and not tracked in this repo, since its only content is the
`TUNNEL_TOKEN`. Render (`skladpro-v2.onrender.com`) is still running as a rollback path; only the
DNS record was moved. See step 7 below for shutting it down.

1. Extract the prepared source bundle into a dedicated NAS folder (for example, `docker/neon`).
2. Create `.env` beside `compose.yaml`, copying the existing Render `DATABASE_URL`, `SECRET_KEY` and `CLOUDINARY_URL`. Copy optional API keys if they exist in Render's environment. Never commit this file.
3. In Docker → Project → Create, select that folder and import `compose.yaml`.
4. Deploy and test `http://192.168.0.37:8080`. This uses the LIVE database: avoid test sales, payments and stock changes. App startup runs its existing schema initialisation.
5. Automatic payment reminders are disabled in this NAS deployment while Render remains active.
6. After testing, configure a Cloudflare Tunnel to `http://neon:8080` on the same Docker network. Preserve all existing DNS records, especially email records, when preparing Cloudflare DNS. Switch the public hostname only after tunnel testing. Do not expose the NAS administration UI.
7. After cutover, stop the Render service before re-enabling reminder sending on one host. Keep Render configuration for rollback.

The named `neon_uploads` volume persists local logos/uploads across container updates; do not delete it. Existing local assets from Render should be copied if not already in the source bundle. Cloudinary product photos remain external. Back up the volume and database regularly.

**Update (2026-10-18): SSH access is now set up.** See the "Deployment" section in `CLAUDE.md` for
the current deploy process (`scp -O` + `ssh ... docker compose up -d --build`). The GUI-driven
process described above (steps 1–7) was only needed for the initial setup and for deploys before
SSH access existed; it's no longer the normal path for routine code changes.

**Update (2026-10-18): Product photos moved off Cloudinary, onto the NAS.** `_save_photo()` /
`_save_photo_bytes()` in `app.py` now always save to the local `neon_uploads` volume
(`static/uploads/products/`) instead of uploading to Cloudinary. All 102 pre-existing
Cloudinary-hosted product photos were downloaded and migrated to local files in place
(`scripts/migrate_cloudinary_to_local.py`, already run — it's a no-op if run again since no rows
still hold a Cloudinary URL). `CLOUDINARY_URL` in the compose file is no longer read by the app and
can eventually be removed; the Cloudinary account itself hasn't been deleted and still holds the
original copies.
