# GKE Ecommerce Starter

A minimal FastAPI ecommerce MVP for GKE Autopilot with PostgreSQL through the
Cloud SQL Auth Proxy.

## Local development

```bash
docker compose up --build
```

Open http://localhost:8080.

## Google Cloud prerequisites

Install and authenticate `gcloud`, `kubectl`, and Docker. Create a Cloud SQL
PostgreSQL instance and database/user. This starter assumes:

- instance name: `ecommerce-db`
- database: `shop`
- database user: `shop`
- domain: `shop.example.com`

Because the manifest passes `--auto-iam-authn`, configure the database user for
Cloud SQL IAM authentication, or remove that flag and use standard database
credentials. Do not commit a production password.

## Deploy

```bash
export PROJECT_ID="your-project"
export REGION="us-central1"
export SQL_INSTANCE="ecommerce-db"
export DOMAIN="shop.yourdomain.com"
chmod +x deploy.sh
./deploy.sh
```

Update the Kubernetes Secret safely:

```bash
kubectl -n ecommerce create secret generic ecommerce-secrets \
  --from-literal=DB_PASSWORD='YOUR_PASSWORD' \
  --dry-run=client -o yaml | kubectl apply -f -
kubectl -n ecommerce rollout restart deployment/ecommerce-api
```

Point the domain's A record to the global static IP printed by `deploy.sh`.
Certificate provisioning can take time after DNS is correct.

## Important production additions

1. Stripe or another payment provider; never handle raw card details yourself.
2. User authentication and authorization.
3. Alembic database migrations rather than `create_all`.
4. Reservation/idempotency logic to prevent overselling.
5. Secret Manager with External Secrets or CSI integration.
6. Cloud Armor, rate limiting, audit logging, monitoring, alerting and backups.
7. Separate dev/staging/prod projects and CI/CD with immutable image tags.
