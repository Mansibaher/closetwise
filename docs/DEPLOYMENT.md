# Practical deployment: one HTTPS VM

Use a small Linux VM with Docker Compose, an SSD, a domain, and ports 80/443 open. Keep PostgreSQL and FastAPI private on the Compose network. Bind frontend's published port to loopback (`127.0.0.1:3000:3000`) and run Caddy on the host as an HTTPS reverse proxy. The repository includes a Caddyfile example; replace the domain and configure DNS first.

1. Copy the repository, excluding local databases, node_modules and image data. Install Docker/Compose and Caddy through their maintained package sources.
2. Copy `.env.example` to `.env`. Set `ENVIRONMENT=production`, `AUTH_SECRET` to a securely generated random value of at least 32 characters, `POSTGRES_PASSWORD` to a strong URL-safe value, and `ALLOWED_ORIGINS=https://closetwise.example.com`. Never commit `.env`.
3. Disable anonymous demo provisioning with `DEMO_ENABLED=false` for a private application. For a public portfolio demo, retain it only behind an edge rate limit, add account/upload retention cleanup, and monitor disk usage. The fixed CLI demo password is public: change or disable that named account before accepting sensitive data.
4. Change the frontend port binding to loopback. Build with `docker compose up --build -d`; verify service health. Configure the host Caddy service using `deploy/Caddyfile`. TLS must terminate at Caddy so production Secure cookies work.
5. Add rate limiting at your edge (for example a CDN/WAF with explicit rules for `/api/auth/*`, `/api/uploads`, `/api/outfits/*`), request-size limits, and access-log retention. The app itself is not an abuse prevention service.
6. Back up PostgreSQL with `pg_dump` and the image volume together. Test a restore in a separate environment. Alternatively use a private S3 bucket with versioning and scoped IAM credentials and a managed PostgreSQL database, using the documented environment variables.
7. For updates, back up first, build new images, and apply migrations with only one API startup process. This student configuration uses one worker; migrating from every replica would be inappropriate for a scaled deployment.

The source currently creates the named CLI demo account on every first startup. If disabling demo provisioning, remove the `python -m app.seed` step from the backend command for a fresh production install, or change the named demo account password through an operator script. Normal accounts are never seeded automatically.

## Operational scope

Health checks cover API/database reachability. Logs should not include API keys, session cookies, or uploaded bytes. Optional vision keys stay on the backend. S3 objects remain private and are delivered through ownership checks. Use mounted secret files or your platform's secret manager when available. Add account recovery, email verification, automatic expiry of abandoned suggestions/demo accounts, and atomic preference updates before operating this as a larger public product.

Compose configuration is provided; see `VERIFICATION.md` for whether the Docker/PostgreSQL deployment was actually exercised. Paid vision and S3 behavior require credentials and are documented optional paths rather than claims of live-provider verification.
