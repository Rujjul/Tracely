# Oracle Always Free deployment — prepared, not provisioned

The frontend remains https://tracely-nu.vercel.app. Application code, local Compose and local environment files are unchanged. As of 2026-10-08, the user still needs to create the Oracle account; no cloud resource, domain, migration, remote backup or public backend verification has been performed.

## Account and cost gate

Create an account at https://signup.cloud.oracle.com/ and complete verification personally. Never send card details, passwords, OAuth secrets or SSH private-key contents in chat. Use the tenancy's home region. Inventory **all** existing usage before creating resources, including volumes/backups in other compartments. Verify the console's Always Free eligibility and remaining quota; do not rely on trial credits or a zero estimate covered by credits. Stop if capacity is unavailable; do not substitute another shape, paid database, NAT gateway, load balancer or marketplace image.

Current official limits: A1 total 2 OCPUs/12 GB (1,500 OCPU-hours/9,000 GB-hours monthly); combined boot/block volumes 200 GB; five volume backups. Object Storage has tier/account-state limits; use a dedicated private Standard bucket capped below 7 GiB and verify total usage remains within the account's free allocation. Source: https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm

Proposed small allocation, subject to the above check: one eligible Ubuntu A1 VM, 1 OCPU/6 GB, 50 GB boot plus 50 GB data volume, public IPv4, VCN/public subnet/Internet Gateway, and the dedicated backup bucket. Self-host PostgreSQL 17 on the VM; do not provision Oracle's paid managed PostgreSQL service. No autoscaling or trial-only resources. Record resource IDs and the actual console eligibility checks before proceeding.

Oracle can reclaim an idle VM after seven days of low CPU/network activity (and low A1 memory use). A worker running every 30 seconds does not guarantee protection. No artificial load will be used to avoid reclamation. This is a single-server deployment with possible downtime; off-host backups support recovery rather than availability.

## Domain and network

The user chose a free DNS subdomain. Claim a unique hostname through a free provider such as DuckDNS (https://www.duckdns.org/) and point it at the assigned public IPv4. The provider account/token stays outside Git. Confirm DNS resolves correctly before requesting TLS. Retain/update the hostname if the instance IP changes; DNS and certificate availability are external dependencies. The Vercel address is the frontend, not the Oracle VM's hostname.

OCI ingress: TCP 80/443 public for HTTPS/ACME; TCP 22 only from the administrator's current public /32 address. Remove any broader default SSH security-list entry: security-list and NSG allows are additive. No public 5432/8000; no IPv6 ingress unless separately secured. Use an SSH key, disable password/root login only after verifying key access, and test a second SSH session before closing the first. Apply equivalent host firewall rules; do not assume UFW blocks Docker-published ports. The Compose file publishes only Caddy's 80/443. PostgreSQL and the detector share an internal-only Docker network. API outbound HTTPS/SMTP is needed for OAuth/password recovery; allow only necessary destinations/ports when refining egress. Do not open the Caddy admin port.

## Install on the dedicated VM

1. Install Docker Engine and Compose from the official Ubuntu instructions: https://docs.docker.com/engine/install/ubuntu/. Install the OCI CLI on the host for backups using the official OCI installation instructions. Do not run unreviewed piped installer scripts.
2. Attach the new data block volume and identify it by its persistent device identifier. Format only a verified **new empty** volume. Mount at `/srv/tracely` and persist by filesystem UUID in `/etc/fstab`. Do not continue if the mount fails; avoid `nofail` for this required data mount. This is an operator checkpoint, not an automatic destructive script.
3. Upload an allowlisted deployment bundle to `/opt/tracely`: `backend/app`, `backend/alembic`, `backend/alembic.ini`, `backend/requirements.txt`, `.dockerignore`, and `deploy/oracle`. No `.env`, keys, local DB dumps, screenshots or Git metadata. Use SFTP/SCP with verified SSH host keys.
4. Create root-owned `/etc/tracely` (0700). Copy `production.env.example` to `/etc/tracely/production.env` (0600), populate directly on the server. Use fresh production DB credentials and a matching URL-encoded `DATABASE_URL`; never display `docker compose config` without `--quiet`. Container administrators can inspect environment variables; restrict Docker/root access.
5. Add `https://tracely-nu.vercel.app/api/v1/auth/google/callback` to the Google Web OAuth client's authorized redirects, retaining the local redirect. Store its secret only in the server environment. Reuse the existing SMTP provider configuration for password resets; verify actual delivery on port 587/465. Do not claim email works until tested.
6. From `/opt/tracely`, run:

```sh
sudo sh deploy/oracle/compose.sh config --quiet
sudo sh deploy/oracle/compose.sh build
sudo sh deploy/oracle/compose.sh up -d --wait --wait-timeout 180
```

Migration service waits for PostgreSQL and must exit successfully before API/worker startup. One API process preserves existing in-memory rate-limit behavior. The app container runs as non-root, with a read-only filesystem and dropped capabilities. Runtime logs rotate; HTTP access logs are disabled to avoid OAuth codes, cookies or ingestion keys. Caddy request-related error logs are suppressed too. Do not debug by dumping environment/config/request headers.

7. Install `docker-tracely.conf` at `/etc/systemd/system/docker.service.d/tracely-storage.conf` (dedicated VM only). Install the supplied `tracely.service`, `tracely-backup.service`, and `tracely-backup.timer` in `/etc/systemd/system`. Run `systemctl daemon-reload`, then enable Docker and `tracely.service`. The Docker dependency prevents daemon container restarts ahead of the required data mount. No `down -v`, destructive schema reset or automatic data import is part of startup.

Existing local data migration is **not yet authorized/decided**. Do not import it or overwrite any database. If requested, make a protected custom-format dump, restore into a separate empty database and verify before cutover. Existing session/reset tokens should not be blindly reused across environments.

## Backups and restore gate

Use a dedicated private Standard Object Storage bucket with versioning disabled, no replication and no paid storage features. Create an instance-principal dynamic group matching only this VM. Grant it bucket-read and object manage access restricted to this single backup bucket, rather than tenancy-wide permissions. `/etc/tracely/backup.env` (0600) contains `OCI_NAMESPACE` and `OCI_BACKUP_BUCKET`; no API private key is required on the server.

Enable `tracely-backup.timer` only after a successful manual run. At 02:15 UTC daily (plus up to five minutes jitter), the job creates a PostgreSQL custom-format dump, validates its catalogue, keeps root-only local copies and uploads to the private bucket. It rejects dumps over 1 GiB, keeps at most seven daily off-host names, and refuses to rotate unexpected objects. The same-day rerun overwrites that day's object. Existing older copies remain if uploading fails. Account-wide free-tier limits must still be monitored independently. Check `systemctl status tracely-backup.timer` and `journalctl -u tracely-backup.service` regularly; failed jobs require operator action. This is not an alert-delivery feature.

Before declaring backups verified: download one dump, restore it with `pg_restore --no-owner --no-acl --exit-on-error` into a **separate disposable database**, compare schema/version and row counts, then test an application read against it. Never test restore by overwriting production. Retain a protected off-cloud copy periodically; a local backup alone does not survive loss of the Oracle account/volume.

## Vercel cutover and cookies

Do not change the live Vercel unavailable route until the Oracle API passes health checks. Then change only its `/api/(.*)` route destination to `https://<API_DOMAIN>/api/$1`, removing the 503 status and retaining no-store. Keep `VITE_API_BASE_URL=/`.

Browser requests and OAuth callbacks go through the Vercel origin, so existing host-only `SameSite=Lax`, HttpOnly session/state cookies work without authentication rewrites. Production sets COOKIE_SECURE=true and restricts FRONTEND_URL/CORS_ORIGINS to the exact Vercel production origin. Do not point browsers directly at an unrelated DNS domain or use wildcard credentialed CORS. Caddy proxies the original API paths. No proxy secret is embedded in the Vite bundle.

## Required live acceptance (still pending)

Before calling deployment complete, stop only Tracely's local API/demo/detector servers after identifying their processes; preserve unrelated programs. Verify:

- Public HTTPS health reports database connected; 5432/8000 are unreachable externally and SSH is restricted.
- Register/login/logout, 30-minute secure cookie, Google callback and existing-account linking; user performs Google consent privately. Test actual password-reset delivery.
- Project creation returns a one-time key; ingest a synthetic event, replay it without duplication, and read it in the Vercel dashboard. Another account cannot read it.
- Keep the **remote** detector running with default policy. Generate qualifying synthetic requests in a dedicated test project and observe one incident after two evaluations, then healthy recovery. Never confuse local/synthetic tests with this result.
- Reboot/recreate containers without deleting volumes; verify records persist and API/worker recover. Run and restore a scheduled off-host backup.
- Record the domain, resource sizes, eligible quota, timestamps, failures and remaining limits in `progress.md`. Until these pass, Vercel remains frontend-only.
