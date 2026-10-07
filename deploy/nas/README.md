# NEON on UGREEN NAS

This deployment keeps the current Neon database and Cloudinary photos. It does not switch DNS or stop Render.

1. Extract the prepared source bundle into a dedicated NAS folder (for example, `docker/neon`).
2. Create `.env` beside `compose.yaml`, copying the existing Render `DATABASE_URL`, `SECRET_KEY` and `CLOUDINARY_URL`. Copy optional API keys if they exist in Render's environment. Never commit this file.
3. In Docker → Project → Create, select that folder and import `compose.yaml`.
4. Deploy and test `http://192.168.0.37:8080`. This uses the LIVE database: avoid test sales, payments and stock changes. App startup runs its existing schema initialisation.
5. Automatic payment reminders are disabled in this NAS deployment while Render remains active.
6. After testing, configure a Cloudflare Tunnel to `http://neon:8080` on the same Docker network. Preserve all existing DNS records, especially email records, when preparing Cloudflare DNS. Switch the public hostname only after tunnel testing. Do not expose the NAS administration UI.
7. After cutover, stop the Render service before re-enabling reminder sending on one host. Keep Render configuration for rollback.

The named `neon_uploads` volume persists local logos/uploads across container updates; do not delete it. Existing local assets from Render should be copied if not already in the source bundle. Cloudinary product photos remain external. Back up the volume and database regularly.
