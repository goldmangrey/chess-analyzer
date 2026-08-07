#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'EOF'
Usage:
  ./scripts/gcp/production-deploy.sh --preflight
  ./scripts/gcp/production-deploy.sh --apply [--resume-from STEP]
  ./scripts/gcp/production-deploy.sh --help

Production deployment is never started without an explicit mode.
EOF
}

MODE=""
RESUME_FROM=""
while (($#)); do
  case "$1" in
    --preflight|--apply)
      [[ -z "$MODE" ]] || { echo "Choose exactly one mode" >&2; exit 2; }
      MODE="${1#--}"
      ;;
    --resume-from)
      shift
      [[ $# -gt 0 ]] || { echo "--resume-from requires STEP" >&2; exit 2; }
      RESUME_FROM="$1"
      ;;
    --help|-h) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done
[[ -n "$MODE" ]] || { usage >&2; exit 2; }
[[ "$MODE" == apply || -z "$RESUME_FROM" ]] || { echo "--resume-from requires --apply" >&2; exit 2; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# common.sh receives no operator arguments; this orchestrator owns its CLI.
source "$SCRIPT_DIR/common.sh"

STATE_FILE="${DEPLOY_STATE_FILE:-$ROOT_DIR/deploy/.deployment-state}"
STEPS="validate apis service-accounts artifact-registry secrets cloud-sql build-backend migration-job migrations worker tasks-queue backend sync-service scheduler build-frontend frontend cors smoke-test"
REQUIRED_APIS="run.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com sqladmin.googleapis.com secretmanager.googleapis.com cloudtasks.googleapis.com cloudscheduler.googleapis.com iam.googleapis.com iamcredentials.googleapis.com"
REQUIRED_SECRETS="DATABASE_PASSWORD CHESSCOM_USER_AGENT ANALYSIS_WORKER_SHARED_SECRET SCHEDULED_SYNC_SHARED_SECRET"
CURRENT_STEP="preflight"
FAILURES=0
DIRTY=false

result() { printf '%-30s %s\n' "$1" "$2"; }
pass() { result "$1" "OK"; }
fail() { result "$1" "FAIL"; FAILURES=$((FAILURES + 1)); }

require_gcloud_flag() {
  local flag="$1"
  shift
  local help_output
  help_output="$("$@" --help 2>&1)" || return 1
  grep -F -- "$flag" <<< "$help_output" >/dev/null
}

check_cli_contracts() {
  require_gcloud_flag --set-cloudsql-instances gcloud run jobs deploy &&
    require_gcloud_flag --image gcloud run jobs deploy &&
    require_gcloud_flag --set-env-vars gcloud run jobs deploy &&
    require_gcloud_flag --set-secrets gcloud run jobs deploy &&
    require_gcloud_flag --set-cloudsql-instances gcloud run deploy &&
    require_gcloud_flag --image gcloud run deploy &&
    require_gcloud_flag --max-dispatches-per-second gcloud tasks queues create &&
    require_gcloud_flag --max-dispatches-per-second gcloud tasks queues update &&
    require_gcloud_flag --oidc-token-audience gcloud scheduler jobs create http &&
    require_gcloud_flag --oidc-token-audience gcloud scheduler jobs update http &&
    gcloud run jobs execute --help >/dev/null 2>&1 &&
    gcloud builds submit --help >/dev/null 2>&1 &&
    gcloud sql instances create --help >/dev/null 2>&1 &&
    gcloud secrets versions add --help >/dev/null 2>&1
}

check_gcloudignore() {
  local file
  for file in app alembic alembic.ini requirements.txt Dockerfile scripts/start_cloud_run.sh; do
    [[ -e "$ROOT_DIR/backend/$file" ]] || return 1
  done
  for file in Dockerfile package.json package-lock.json next.config.ts tsconfig.json src; do
    [[ -e "$ROOT_DIR/frontend/$file" ]] || return 1
  done
}

run_preflight() {
  local active_project billing_enabled enabled_apis missing account state version edition expected_edition tier database user secret secret_state
  FAILURES=0
  printf '%-30s %s\n' "CHECK" "RESULT"

  if command -v gcloud >/dev/null 2>&1 && account="$(gcloud auth list --filter=status:ACTIVE --format='value(account)' | head -n1)" && [[ -n "$account" ]]; then pass "gcloud auth"; else fail "gcloud auth"; fi
  active_project="$(gcloud config get-value project 2>/dev/null || true)"
  if [[ "$active_project" == "$GCP_PROJECT_ID" ]]; then pass "project"; else fail "project"; fi
  billing_enabled="$(gcloud billing projects describe "$GCP_PROJECT_ID" --format='value(billingEnabled)' 2>/dev/null || true)"
  if [[ "$billing_enabled" == True || "$billing_enabled" == TRUE ]]; then pass "billing"; else fail "billing"; fi

  enabled_apis="$(gcloud services list --enabled --project "$GCP_PROJECT_ID" --format='value(config.name)' 2>/dev/null || true)"
  missing=""
  for api in $REQUIRED_APIS; do printf '%s\n' "$enabled_apis" | grep -Fx "$api" >/dev/null || missing="$missing $api"; done
  if [[ -z "$missing" ]]; then pass "required APIs"; else fail "required APIs"; fi

  missing=""
  for account in "$BACKEND_SERVICE_ACCOUNT_EMAIL" "$WORKER_SERVICE_ACCOUNT_EMAIL" "$TASKS_INVOKER_SERVICE_ACCOUNT_EMAIL" "$SCHEDULER_SERVICE_ACCOUNT_EMAIL"; do
    gcloud iam service-accounts describe "$account" --project "$GCP_PROJECT_ID" >/dev/null 2>&1 || missing="$missing account"
  done
  if [[ -z "$missing" ]]; then pass "service accounts"; else fail "service accounts"; fi

  if gcloud artifacts repositories describe "$ARTIFACT_REPOSITORY" --project "$GCP_PROJECT_ID" --location "$GCP_REGION" >/dev/null 2>&1; then pass "Artifact Registry"; else fail "Artifact Registry"; fi

  state="$(gcloud sql instances describe "$CLOUD_SQL_INSTANCE" --project "$GCP_PROJECT_ID" --format='value(state)' 2>/dev/null || true)"
  version="$(gcloud sql instances describe "$CLOUD_SQL_INSTANCE" --project "$GCP_PROJECT_ID" --format='value(databaseVersion)' 2>/dev/null || true)"
  edition="$(gcloud sql instances describe "$CLOUD_SQL_INSTANCE" --project "$GCP_PROJECT_ID" --format='value(settings.edition)' 2>/dev/null || true)"
  tier="$(gcloud sql instances describe "$CLOUD_SQL_INSTANCE" --project "$GCP_PROJECT_ID" --format='value(settings.tier)' 2>/dev/null || true)"
  expected_edition=ENTERPRISE
  [[ "$CLOUD_SQL_EDITION" == enterprise-plus ]] && expected_edition=ENTERPRISE_PLUS
  if [[ "$state" == RUNNABLE && "$version" == POSTGRES_17 && ( "$edition" == "$expected_edition" || "$edition" == "$CLOUD_SQL_EDITION" ) && "$tier" == "$CLOUD_SQL_TIER" ]]; then pass "Cloud SQL"; else fail "Cloud SQL"; fi
  database="$(gcloud sql databases describe "$CLOUD_SQL_DATABASE" --instance "$CLOUD_SQL_INSTANCE" --project "$GCP_PROJECT_ID" --format='value(name)' 2>/dev/null || true)"
  if [[ "$database" == "$CLOUD_SQL_DATABASE" ]]; then pass "database"; else fail "database"; fi
  user="$(gcloud sql users list --instance "$CLOUD_SQL_INSTANCE" --project "$GCP_PROJECT_ID" --filter="name=$CLOUD_SQL_USER" --format='value(name)' 2>/dev/null || true)"
  if printf '%s\n' "$user" | grep -Fx "$CLOUD_SQL_USER" >/dev/null; then pass "database user"; else fail "database user"; fi

  missing=""
  for secret in $REQUIRED_SECRETS; do
    secret_state="$(gcloud secrets versions describe latest --secret "$secret" --project "$GCP_PROJECT_ID" --format='value(state)' 2>/dev/null || true)"
    [[ "$secret_state" == ENABLED ]] || missing="$missing $secret"
  done
  if [[ -z "$missing" ]]; then pass "secrets"; else fail "secrets"; fi

  if gcloud artifacts docker images describe "$BACKEND_IMAGE" --project "$GCP_PROJECT_ID" >/dev/null 2>&1; then pass "backend image"; else fail "backend image"; fi
  if check_cli_contracts; then pass "CLI flags"; else fail "CLI flags"; fi
  if check_gcloudignore; then pass "build contexts"; else fail "build contexts"; fi

  if git -C "$ROOT_DIR" diff --quiet && git -C "$ROOT_DIR" diff --cached --quiet && [[ -z "$(git -C "$ROOT_DIR" ls-files --others --exclude-standard)" ]]; then
    pass "git working tree"
    DIRTY=false
  else
    result "git working tree" "WARN"
    DIRTY=true
  fi

  if ((FAILURES == 0)); then
    result "deployment plan" "READY"
    echo "PRECHECK PASSED — no resources changed"
    return 0
  fi
  result "deployment plan" "BLOCKED"
  echo "PRECHECK FAILED"
  return 1
}

if [[ "$MODE" == preflight ]]; then
  run_preflight
  exit $?
fi

run_preflight || exit 1
if $DIRTY && [[ "${ALLOW_DIRTY_DEPLOY:-false}" != true ]]; then
  echo "Apply refused: git working tree is dirty. Commit first or explicitly set ALLOW_DIRTY_DEPLOY=true." >&2
  exit 2
fi

if [[ -n "$RESUME_FROM" ]]; then
  case " $STEPS " in *" $RESUME_FROM "*) ;; *) echo "Unknown resume step: $RESUME_FROM" >&2; exit 2;; esac
fi

mkdir -p "$(dirname "$STATE_FILE")"
touch "$STATE_FILE"

completed() { grep -Fx "$GIT_SHA $1" "$STATE_FILE" >/dev/null 2>&1; }
mark_completed() { printf '%s %s\n' "$GIT_SHA" "$1" >> "$STATE_FILE"; }
service_url() { gcloud run services describe "$1" --project "$GCP_PROJECT_ID" --region "$GCP_REGION" --format='value(status.url)'; }
require_https_url() { [[ "$1" == https://* && "$1" != *example* ]]; }

WORKER_URL="$(service_url "$WORKER_SERVICE" 2>/dev/null || true)"
BACKEND_URL="$(service_url "$BACKEND_SERVICE" 2>/dev/null || true)"
SYNC_SERVICE_URL="$(service_url "$SYNC_SERVICE" 2>/dev/null || true)"
FRONTEND_URL="$(service_url "$FRONTEND_SERVICE" 2>/dev/null || true)"
export WORKER_URL BACKEND_URL SYNC_SERVICE_URL FRONTEND_URL

on_error() {
  local code=$?
  echo "Deployment failed at step: $CURRENT_STEP" >&2
  echo "Inspect the named resource with gcloud describe/logs commands; secrets were not printed." >&2
  echo "Resume:" >&2
  echo "./scripts/gcp/production-deploy.sh --apply --resume-from $CURRENT_STEP" >&2
  exit "$code"
}
trap on_error ERR

do_step() {
  local step="$1"
  shift
  if [[ -n "$RESUME_FROM" && "$RESUME_FROM" != "$step" ]]; then
    echo "SKIP before resume: $step"
    return 0
  fi
  if [[ "$RESUME_FROM" == "$step" ]]; then RESUME_FROM=""; fi
  if completed "$step"; then echo "SKIP completed: $step"; return 0; fi
  CURRENT_STEP="$step"
  echo
  echo "==> $step"
  "$@"
  mark_completed "$step"
}

step_validate() { :; }
step_apis() { "$SCRIPT_DIR/enable-apis.sh" --apply; }
step_service_accounts() { "$SCRIPT_DIR/create-service-accounts.sh" --apply; }
step_artifact_registry() { "$SCRIPT_DIR/create-artifact-registry.sh" --apply; }
step_secrets() { "$SCRIPT_DIR/create-secrets.sh" --apply; }
step_cloud_sql() { "$SCRIPT_DIR/create-cloud-sql.sh" --apply; }
step_build_backend() { BUILD_TARGET=backend "$SCRIPT_DIR/build-images.sh" --apply; }
step_migration_job() { "$SCRIPT_DIR/deploy-migration-job.sh" --apply; }
step_migrations() {
  if ! "$SCRIPT_DIR/run-migrations.sh" --apply; then
    gcloud run jobs logs read "$MIGRATION_JOB" --project "$GCP_PROJECT_ID" --region "$GCP_REGION" --limit 50 2>/dev/null || true
    return 1
  fi
}
step_worker() {
  "$SCRIPT_DIR/deploy-worker.sh" --apply
  WORKER_URL="$(service_url "$WORKER_SERVICE")"
  require_https_url "$WORKER_URL"
  export WORKER_URL
}
step_tasks_queue() { "$SCRIPT_DIR/create-cloud-tasks-queue.sh" --apply; }
step_backend() {
  require_https_url "$WORKER_URL"
  "$SCRIPT_DIR/deploy-backend.sh" --apply
  BACKEND_URL="$(service_url "$BACKEND_SERVICE")"
  require_https_url "$BACKEND_URL"
  export BACKEND_URL
  curl --fail --silent --show-error "$BACKEND_URL/health" >/dev/null
  curl --fail --silent --show-error "$BACKEND_URL/api/system/status" >/dev/null
}
step_sync_service() {
  "$SCRIPT_DIR/deploy-sync-service.sh" --apply
  SYNC_SERVICE_URL="$(service_url "$SYNC_SERVICE")"
  require_https_url "$SYNC_SERVICE_URL"
  export SYNC_SERVICE_URL
}
step_scheduler() { "$SCRIPT_DIR/create-scheduler-job.sh" --apply; }
step_build_frontend() { BUILD_TARGET=frontend BACKEND_URL="$BACKEND_URL" "$SCRIPT_DIR/build-images.sh" --apply; }
step_frontend() {
  "$SCRIPT_DIR/deploy-frontend.sh" --apply
  FRONTEND_URL="$(service_url "$FRONTEND_SERVICE")"
  require_https_url "$FRONTEND_URL"
  export FRONTEND_URL
}
step_cors() { FRONTEND_ORIGINS="$FRONTEND_URL,$EXTRA_FRONTEND_ORIGINS" "$SCRIPT_DIR/deploy-backend.sh" --apply; }
step_smoke_test() { "$SCRIPT_DIR/smoke-test.sh" --apply; }

do_step validate step_validate
do_step apis step_apis
do_step service-accounts step_service_accounts
do_step artifact-registry step_artifact_registry
do_step secrets step_secrets
do_step cloud-sql step_cloud_sql
do_step build-backend step_build_backend
do_step migration-job step_migration_job
do_step migrations step_migrations
do_step worker step_worker
do_step tasks-queue step_tasks_queue
do_step backend step_backend
do_step sync-service step_sync_service
do_step scheduler step_scheduler
do_step build-frontend step_build_frontend
do_step frontend step_frontend
do_step cors step_cors
do_step smoke-test step_smoke_test

trap - ERR
echo "Production deployment completed. State: deploy/.deployment-state"
