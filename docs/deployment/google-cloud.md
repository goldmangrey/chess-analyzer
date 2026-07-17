# Google Cloud deployment

This deployment creates paid Google Cloud resources. Every provisioning script
is a dry-run unless `--apply` is supplied. Review the printed commands first.

## Architecture and identities

- `chess-ai-frontend`: public Cloud Run Next.js service;
- `chess-ai-backend`: public product API;
- `chess-ai-worker`: private Cloud Run service using the backend image;
- `chess-analysis`: Cloud Tasks queue sending OIDC requests to the worker;
- `chess-ai-postgres`: Cloud SQL PostgreSQL 17 instance;
- `chess-ai-migrate`: single-task Cloud Run migration job.

The backend runtime account has `roles/cloudsql.client`,
`roles/secretmanager.secretAccessor`, and `roles/cloudtasks.enqueuer`. The worker
has only Cloud SQL Client and Secret Accessor. The tasks-invoker account receives
`roles/run.invoker` on the worker. The Cloud Tasks service agent receives
`roles/iam.serviceAccountTokenCreator` on that invoker identity. No JSON keys,
Owner, or Editor roles are created.

The public API URL is baked into the frontend image through
`NEXT_PUBLIC_API_BASE_URL`; rebuild the image whenever that URL changes.

## Prerequisites

1. Create or select a GCP project and enable billing manually.
2. Install `gcloud`, then run `gcloud auth login` and optionally
   `gcloud auth application-default login`.
3. Copy and edit deployment configuration:

```bash
cp deploy/gcp.env.example deploy/gcp.env
${EDITOR:-vi} deploy/gcp.env
source deploy/gcp.env
```

Never place passwords in `deploy/gcp.env`. Scripts read secret values from the
current process environment and do not print them.

## Manual provisioning

Run each command without `--apply` first, then repeat it with `--apply` after
review. The Cloud SQL command creates a billable instance.

```bash
./scripts/gcp/check-config.sh
./scripts/gcp/enable-apis.sh --apply
./scripts/gcp/create-service-accounts.sh --apply
./scripts/gcp/create-artifact-registry.sh --apply

export DATABASE_PASSWORD='replace-me'
export CHESSCOM_USER_AGENT='ChessAITeacher/1.0 (contact: you@example.com)'
export ANALYSIS_WORKER_SHARED_SECRET='long-random-value'
./scripts/gcp/create-secrets.sh --apply
./scripts/gcp/create-cloud-sql.sh --apply
```

Cloud SQL keeps a public endpoint for the managed Cloud SQL attachment, but no
authorized network such as `0.0.0.0/0` is added. Cloud Run connects through
`--add-cloudsql-instances` and the Unix socket
`/cloudsql/PROJECT:REGION:INSTANCE`. The default `db-f1-micro`, single-zone
configuration is intended for a low-cost pet project. Storage auto-increase and
backups are enabled; regional HA costs more and is not enabled by default.

Build the backend with an immutable Git SHA tag:

```bash
export GIT_SHA="$(git rev-parse --short=12 HEAD)"
export REGISTRY="$GCP_REGION-docker.pkg.dev/$GCP_PROJECT_ID/$ARTIFACT_REPOSITORY"
export IMAGE_TAG="$REGISTRY/backend:$GIT_SHA"
./scripts/gcp/build-images.sh --apply
```

Apply migrations before deploying a new backend revision:

```bash
./scripts/gcp/deploy-migration-job.sh --apply
./scripts/gcp/run-migrations.sh --apply
```

Deploy the private worker, grant its narrowly scoped invoker role, and capture
its URL:

```bash
./scripts/gcp/deploy-worker.sh --apply
export WORKER_URL="$(gcloud run services describe "$WORKER_SERVICE" \
  --project "$GCP_PROJECT_ID" --region "$GCP_REGION" \
  --format='value(status.url)')"
./scripts/gcp/create-cloud-tasks-queue.sh --apply
```

The queue uses 1 dispatch/second, concurrency 1, 5 attempts, and exponential
backoff from 10 to 300 seconds. The application never creates the queue.

Deploy the public backend with a temporary local CORS origin:

```bash
export FRONTEND_ORIGINS=http://localhost:3000
./scripts/gcp/deploy-backend.sh --apply
export BACKEND_URL="$(gcloud run services describe "$BACKEND_SERVICE" \
  --project "$GCP_PROJECT_ID" --region "$GCP_REGION" \
  --format='value(status.url)')"
```

Build and deploy the frontend, then replace the temporary CORS origin:

```bash
./scripts/gcp/build-images.sh --apply
export FRONTEND_IMAGE_TAG="$REGISTRY/frontend:$GIT_SHA"
./scripts/gcp/deploy-frontend.sh --apply
export FRONTEND_URL="$(gcloud run services describe "$FRONTEND_SERVICE" \
  --project "$GCP_PROJECT_ID" --region "$GCP_REGION" \
  --format='value(status.url)')"
export FRONTEND_ORIGINS="$FRONTEND_URL"
./scripts/gcp/deploy-backend.sh --apply
./scripts/gcp/smoke-test.sh --apply
```

The smoke test checks health, diagnostics, settings, frontend HTML, CORS, and
that an unauthenticated worker request is rejected. It never starts sync or
Stockfish analysis.

`deploy-all.sh` orchestrates the same order. It remains a dry-run without
`--apply`:

```bash
./scripts/gcp/deploy-all.sh
./scripts/gcp/deploy-all.sh --apply
```

## Database and secrets

Production containers receive `DATABASE_PASSWORD`, `CHESSCOM_USER_AGENT`, and
`ANALYSIS_WORKER_SHARED_SECRET` from Secret Manager. Non-secret DB components
are regular environment variables. If `DATABASE_URL` is explicitly set it has
priority; otherwise the backend creates this URL internally, with encoded
credentials:

```text
postgresql+psycopg://USER:PASSWORD@/DATABASE?host=/cloudsql/CONNECTION_NAME
```

Production uses `DB_POOL_SIZE=2` and `DB_MAX_OVERFLOW=1`. The approximate upper
bound is `instances × (pool_size + max_overflow)`, plus the short-lived migration
job connection.

## Cleanup

Cleanup is deliberately manual. Export or back up data first. Deleting Cloud SQL
permanently destroys the production database.

```bash
gcloud run services delete "$FRONTEND_SERVICE" --region "$GCP_REGION"
gcloud run services delete "$BACKEND_SERVICE" --region "$GCP_REGION"
gcloud run services delete "$WORKER_SERVICE" --region "$GCP_REGION"
gcloud run jobs delete "$MIGRATION_JOB" --region "$GCP_REGION"
gcloud tasks queues delete "$CLOUD_TASKS_QUEUE" --location "$GCP_REGION"
# DANGER: permanent database deletion
gcloud sql instances delete "$CLOUD_SQL_INSTANCE"
gcloud artifacts repositories delete "$ARTIFACT_REPOSITORY" --location "$GCP_REGION"
```

Delete secrets and service accounts only after confirming that no other service
uses them. Cloud Scheduler and server-side automatic sync are intentionally not
part of this stage; sync remains manual/client-driven.
