#!/usr/bin/env bash
source "$(dirname "$0")/common.sh" "$@"
step() {
  echo
  echo "==> $1"
  shift
  if $APPLY; then "$@" --apply; else "$@"; fi
}
step "Validate configuration" "$ROOT_DIR/scripts/gcp/check-config.sh"
step "Enable APIs" "$ROOT_DIR/scripts/gcp/enable-apis.sh"
step "Create service accounts" "$ROOT_DIR/scripts/gcp/create-service-accounts.sh"
step "Create Artifact Registry" "$ROOT_DIR/scripts/gcp/create-artifact-registry.sh"
step "Create Cloud SQL" "$ROOT_DIR/scripts/gcp/create-cloud-sql.sh"
step "Validate/create secrets" "$ROOT_DIR/scripts/gcp/create-secrets.sh"
GIT_SHA="${GIT_SHA:-$(git -C "$ROOT_DIR" rev-parse --short=12 HEAD)}"; REGISTRY="$GCP_REGION-docker.pkg.dev/$GCP_PROJECT_ID/$ARTIFACT_REPOSITORY"; export IMAGE_TAG="$REGISTRY/backend:$GIT_SHA"
step "Build backend" "$ROOT_DIR/scripts/gcp/build-images.sh"
step "Deploy migration job" "$ROOT_DIR/scripts/gcp/deploy-migration-job.sh"
step "Run migrations" "$ROOT_DIR/scripts/gcp/run-migrations.sh"
step "Deploy private worker" "$ROOT_DIR/scripts/gcp/deploy-worker.sh"
if $APPLY; then export WORKER_URL="$(gcloud run services describe "$WORKER_SERVICE" --project "$GCP_PROJECT_ID" --region "$GCP_REGION" --format='value(status.url)')"; fi
$APPLY || export WORKER_URL=https://worker.invalid
step "Create Cloud Tasks queue" "$ROOT_DIR/scripts/gcp/create-cloud-tasks-queue.sh"
step "Deploy public backend" "$ROOT_DIR/scripts/gcp/deploy-backend.sh"
step "Deploy private scheduled-sync service" "$ROOT_DIR/scripts/gcp/deploy-sync-service.sh"
if $APPLY; then export SYNC_SERVICE_URL="$(gcloud run services describe "$SYNC_SERVICE" --project "$GCP_PROJECT_ID" --region "$GCP_REGION" --format='value(status.url)')"; else export SYNC_SERVICE_URL=https://sync.invalid; fi
step "Create Cloud Scheduler job" "$ROOT_DIR/scripts/gcp/create-scheduler-job.sh"
if $APPLY; then export BACKEND_URL="$(gcloud run services describe "$BACKEND_SERVICE" --project "$GCP_PROJECT_ID" --region "$GCP_REGION" --format='value(status.url)')"; export SERVER_SYNC_ENABLED=true; "$ROOT_DIR/scripts/gcp/build-images.sh" --apply; export FRONTEND_IMAGE_TAG="$REGISTRY/frontend:$GIT_SHA"; "$ROOT_DIR/scripts/gcp/deploy-frontend.sh" --apply; export FRONTEND_URL="$(gcloud run services describe "$FRONTEND_SERVICE" --project "$GCP_PROJECT_ID" --region "$GCP_REGION" --format='value(status.url)')"; export FRONTEND_ORIGINS="$FRONTEND_URL,$EXTRA_FRONTEND_ORIGINS"; "$ROOT_DIR/scripts/gcp/deploy-backend.sh" --apply; "$ROOT_DIR/scripts/gcp/smoke-test.sh" --apply; else echo "Dry-run: frontend build/deploy, final CORS update and smoke tests require URLs produced by applied steps."; fi
echo "Scheduled sync is provisioned but never invoked by this orchestrator. Use run-scheduler-now.sh --apply for an explicit test."
