#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

# Precedence: current process environment, deploy/gcp.env, safe defaults.
DEPLOY_ENV_NAMES="GCP_PROJECT_ID GCP_REGION ARTIFACT_REPOSITORY BACKEND_SERVICE WORKER_SERVICE SYNC_SERVICE FRONTEND_SERVICE MIGRATION_JOB CLOUD_SQL_INSTANCE CLOUD_SQL_DATABASE CLOUD_SQL_USER CLOUD_SQL_EDITION CLOUD_SQL_TIER CLOUD_SQL_DATABASE_VERSION CLOUD_SQL_STORAGE_SIZE_GB CLOUD_TASKS_QUEUE BACKEND_SERVICE_ACCOUNT WORKER_SERVICE_ACCOUNT TASKS_INVOKER_SERVICE_ACCOUNT SCHEDULER_SERVICE_ACCOUNT SCHEDULER_JOB SCHEDULER_SCHEDULE SCHEDULER_TIME_ZONE EXTRA_FRONTEND_ORIGINS FORCE_REBUILD ROTATE_SECRETS ALLOW_DIRTY_DEPLOY"
for env_name in $DEPLOY_ENV_NAMES; do
  if [[ -n "${!env_name+x}" ]]; then
    explicit_name="CHESS_DEPLOY_EXPLICIT_${env_name}"
    printf -v "$explicit_name" '%s' "${!env_name}"
  fi
done
if [[ -f "$ROOT_DIR/deploy/gcp.env" ]]; then
  set -a
  source "$ROOT_DIR/deploy/gcp.env"
  set +a
fi
for env_name in $DEPLOY_ENV_NAMES; do
  explicit_name="CHESS_DEPLOY_EXPLICIT_${env_name}"
  if [[ -n "${!explicit_name+x}" ]]; then
    printf -v "$env_name" '%s' "${!explicit_name}"
    export "$env_name"
    unset "$explicit_name"
  fi
done
unset env_name explicit_name
APPLY=false
for arg in "$@"; do
  case "$arg" in --apply) APPLY=true;; --help|-h) echo "Usage: $0 [--apply]"; exit 0;; *) echo "Unknown argument: $arg" >&2; exit 2;; esac
done
need() {
  local value="${!1:-}"
  [[ -n "$value" && "$value" != your-* && "$value" != *change-me* && "$value" != *example* ]] || {
    echo "Missing or placeholder $1" >&2
    exit 2
  }
}
defaults() {
  : "${GCP_REGION:=europe-west1}" "${ARTIFACT_REPOSITORY:=chess-ai-teacher}"
  : "${BACKEND_SERVICE:=chess-ai-backend}" "${WORKER_SERVICE:=chess-ai-worker}" "${SYNC_SERVICE:=chess-ai-sync}" "${FRONTEND_SERVICE:=chess-ai-frontend}"
  : "${MIGRATION_JOB:=chess-ai-migrate}" "${CLOUD_SQL_INSTANCE:=chess-ai-postgres}"
  : "${CLOUD_SQL_DATABASE:=chess_ai_teacher}" "${CLOUD_SQL_USER:=chess_app}" "${CLOUD_TASKS_QUEUE:=chess-analysis}"
  : "${CLOUD_SQL_EDITION=enterprise}" "${CLOUD_SQL_TIER=db-f1-micro}"
  : "${CLOUD_SQL_DATABASE_VERSION=POSTGRES_17}" "${CLOUD_SQL_STORAGE_SIZE_GB=10}"
  : "${BACKEND_SERVICE_ACCOUNT:=chess-backend}" "${WORKER_SERVICE_ACCOUNT:=chess-worker}" "${TASKS_INVOKER_SERVICE_ACCOUNT:=chess-tasks-invoker}"
  : "${SCHEDULER_SERVICE_ACCOUNT:=chess-scheduler}" "${SCHEDULER_JOB:=chess-sync}" "${SCHEDULER_SCHEDULE:=* * * * *}" "${SCHEDULER_TIME_ZONE:=Etc/UTC}"
  : "${EXTRA_FRONTEND_ORIGINS:=http://localhost:3000,http://127.0.0.1:3000}"
  export GCP_REGION ARTIFACT_REPOSITORY BACKEND_SERVICE WORKER_SERVICE SYNC_SERVICE FRONTEND_SERVICE MIGRATION_JOB CLOUD_SQL_INSTANCE CLOUD_SQL_DATABASE CLOUD_SQL_USER CLOUD_SQL_EDITION CLOUD_SQL_TIER CLOUD_SQL_DATABASE_VERSION CLOUD_SQL_STORAGE_SIZE_GB CLOUD_TASKS_QUEUE BACKEND_SERVICE_ACCOUNT WORKER_SERVICE_ACCOUNT TASKS_INVOKER_SERVICE_ACCOUNT SCHEDULER_SERVICE_ACCOUNT SCHEDULER_JOB SCHEDULER_SCHEDULE SCHEDULER_TIME_ZONE EXTRA_FRONTEND_ORIGINS
}
run() {
  printf '  '
  printf '%q ' "$@"
  printf '\n'
  if $APPLY; then "$@"; fi
}
defaults
need GCP_PROJECT_ID

GIT_SHA="$(git -C "$ROOT_DIR" rev-parse --short=12 HEAD)"
IMAGE_TAG="$GIT_SHA"
BACKEND_IMAGE="$GCP_REGION-docker.pkg.dev/$GCP_PROJECT_ID/$ARTIFACT_REPOSITORY/backend:$GIT_SHA"
FRONTEND_IMAGE="$GCP_REGION-docker.pkg.dev/$GCP_PROJECT_ID/$ARTIFACT_REPOSITORY/frontend:$GIT_SHA"
CLOUD_SQL_CONNECTION_NAME="$GCP_PROJECT_ID:$GCP_REGION:$CLOUD_SQL_INSTANCE"
BACKEND_SERVICE_ACCOUNT_EMAIL="$BACKEND_SERVICE_ACCOUNT@$GCP_PROJECT_ID.iam.gserviceaccount.com"
WORKER_SERVICE_ACCOUNT_EMAIL="$WORKER_SERVICE_ACCOUNT@$GCP_PROJECT_ID.iam.gserviceaccount.com"
TASKS_INVOKER_SERVICE_ACCOUNT_EMAIL="$TASKS_INVOKER_SERVICE_ACCOUNT@$GCP_PROJECT_ID.iam.gserviceaccount.com"
SCHEDULER_SERVICE_ACCOUNT_EMAIL="$SCHEDULER_SERVICE_ACCOUNT@$GCP_PROJECT_ID.iam.gserviceaccount.com"
export GIT_SHA IMAGE_TAG BACKEND_IMAGE FRONTEND_IMAGE CLOUD_SQL_CONNECTION_NAME
export BACKEND_SERVICE_ACCOUNT_EMAIL WORKER_SERVICE_ACCOUNT_EMAIL TASKS_INVOKER_SERVICE_ACCOUNT_EMAIL SCHEDULER_SERVICE_ACCOUNT_EMAIL
