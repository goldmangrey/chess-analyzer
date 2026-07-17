#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
[[ -f "$ROOT_DIR/deploy/gcp.env" ]] && set -a && source "$ROOT_DIR/deploy/gcp.env" && set +a
APPLY=false
for arg in "$@"; do
  case "$arg" in --apply) APPLY=true;; --help|-h) echo "Usage: $0 [--apply]"; exit 0;; *) echo "Unknown argument: $arg" >&2; exit 2;; esac
done
need() { [[ -n "${!1:-}" && "${!1}" != your-* ]] || { echo "Missing $1" >&2; exit 2; }; }
defaults() {
  : "${GCP_REGION:=europe-west1}" "${ARTIFACT_REPOSITORY:=chess-ai-teacher}"
  : "${BACKEND_SERVICE:=chess-ai-backend}" "${WORKER_SERVICE:=chess-ai-worker}" "${FRONTEND_SERVICE:=chess-ai-frontend}"
  : "${MIGRATION_JOB:=chess-ai-migrate}" "${CLOUD_SQL_INSTANCE:=chess-ai-postgres}"
  : "${CLOUD_SQL_DATABASE:=chess_ai_teacher}" "${CLOUD_SQL_USER:=chess_app}" "${CLOUD_TASKS_QUEUE:=chess-analysis}"
  : "${BACKEND_SERVICE_ACCOUNT:=chess-backend}" "${WORKER_SERVICE_ACCOUNT:=chess-worker}" "${TASKS_INVOKER_SERVICE_ACCOUNT:=chess-tasks-invoker}"
  export GCP_REGION ARTIFACT_REPOSITORY BACKEND_SERVICE WORKER_SERVICE FRONTEND_SERVICE MIGRATION_JOB CLOUD_SQL_INSTANCE CLOUD_SQL_DATABASE CLOUD_SQL_USER CLOUD_TASKS_QUEUE BACKEND_SERVICE_ACCOUNT WORKER_SERVICE_ACCOUNT TASKS_INVOKER_SERVICE_ACCOUNT
}
run() { printf '  '; printf '%q ' "$@"; printf '\n'; $APPLY && "$@"; }
defaults
need GCP_PROJECT_ID
