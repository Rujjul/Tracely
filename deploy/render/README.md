# Render Free + Neon Free

Prepared on 2026-10-08. Accounts and live integration are pending. This replaces the proposed Oracle deployment; it does not modify local development or application logic.

## Account setup

1. Create accounts at https://dashboard.render.com/ and https://console.neon.tech/. GitHub sign-in simplifies repository authorization. Choose Free plans; do not enable paid compute, paid workers, automatic upgrades or trial-only services. Check bandwidth/build spending settings before deployment; a free instance alone does not exclude other billable usage. Do not add a payment method for automatic overages.
2. In Neon, create a dedicated Tracely project with PostgreSQL 17, in a region near the Render service. Keep scale-to-zero enabled and inspect the account's current storage, compute and transfer quotas. Start with a fresh database; do not import local accounts/events without the user's data-migration decision.
3. Copy the direct (not pooled) `postgresql://` connection URL from Neon's Connect dialog directly into Render's secret `DATABASE_URL` field, retaining TLS parameters. Never paste it into chat, Git or frontend variables. Direct connections support the existing migrations without application changes.
4. Connect Render to the Git repository containing the current code and use the root `render.yaml` Blueprint. Review that the only resource is a **Free Web Service**. Alternatively configure that service manually: leave root directory blank, build `pip install -r backend/requirements.txt`, start `sh deploy/render/start.sh`, Python 3.12.10, and the environment variables below. Include the startup script in the deployed revision.

## Environment and authentication

- `FRONTEND_URL`: actual canonical Vercel HTTPS origin, without a trailing slash.
- `CORS_ORIGINS`: the same exact origin, not `*`.
- `COOKIE_SECURE`: `true`.
- `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET`: existing Tracely Google Web client values, entered privately in Render.
- `GOOGLE_REDIRECT_URI`: `https://<actual-vercel-host>/api/v1/auth/google/callback`. Add this exact URI to the Google client and keep the local callback.

Startup runs existing Alembic migrations before serving, fails closed on migration failure, and disables Uvicorn access logs to avoid OAuth query logging. Keep one API instance. Do not deploy concurrent schema changes. Back up data before later migrations. Hosting-provider request logs are separate; review their retention/access settings.

The default Render TCP health check avoids repeatedly querying Neon while idle. Verify database readiness manually at `/api/v1/health`, requiring `storage: connected`. Cold Neon wake-up may require retrying; the existing database connection timeout is unchanged.

## Vercel cutover (only after backend readiness)

Render provides an HTTPS `onrender.com` hostname, so no separate DNS provider is needed. In `frontend/vercel.json`, change only the first route to:

```json
{"src":"/api/(.*)","dest":"https://<actual-render-host>/api/$1"}
```

Remove that route's old 503 status and preview headers. Retain the filesystem/SPA routes and `VITE_API_BASE_URL=/` build setting. Redeploy Vercel. Browser requests then remain on the Vercel origin, preserving existing SameSite=Lax session and OAuth-state cookies. Do not point the browser directly at a different-site Render API. This cutover is deliberately not applied while accounts/URLs are unknown.

## Free-tier limitations requiring a decision

- Render sleeps after 15 idle minutes; waking can take about a minute. Cold requests can fail through the frontend proxy and need retrying.
- No free Render background-worker service. The detector is not launched by this configuration, so new automatic incidents and recovery will not run. Existing stored incidents remain readable. Do not silently run a paid worker or add artificial keepalive traffic. A separately agreed worker arrangement is required to preserve continuous detection.
- Render Free blocks outbound SMTP ports 25, 465 and 587. Existing SMTP password recovery cannot work on the usual ports. Leave SMTP unconfigured so the app reports its setup error. An alternative email transport/provider needs a separate decision; no recovery code has been changed.
- Neon compute/storage/transfer quotas are finite. A continuous 30-second detector or database health polling can prevent database sleep. Do not promise continuous operation within the free compute allowance.
- No verified scheduled backups or restore procedure exists for this deployment yet. Check available Neon recovery retention and arrange independent encrypted backups before relying on production data.

Official references: https://render.com/docs/free, https://render.com/docs/blueprint-spec, https://neon.com/pricing.

## Acceptance checklist

- [ ] Free accounts, repository access, resource plans and quotas confirmed.
- [ ] Neon TLS connection and migrations through the current Alembic head verified.
- [ ] Public API health returns connected; no secrets in logs.
- [ ] Vercel proxy, CORS, secure cookie and Google callback configured.
- [ ] With local servers stopped: register, password login/logout, Google login, owner-only projects/keys, event ingestion and dashboard verified.
- [ ] Worker hosting and email limitations explicitly accepted or resolved.
- [ ] Incident detection/recovery, backup restore and cold-start behavior verified where supported.

Never label the full deployment complete while these checks are pending.
