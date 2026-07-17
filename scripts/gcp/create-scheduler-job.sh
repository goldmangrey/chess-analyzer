#!/usr/bin/env bash
source "$(dirname "$0")/common.sh" "$@"
need SYNC_SERVICE_URL
TARGET="$SYNC_SERVICE_URL/internal/sync/chess-com"
OIDC_ACCOUNT="$SCHEDULER_SERVICE_ACCOUNT_EMAIL"
if gcloud scheduler jobs describe "$SCHEDULER_JOB" --project "$GCP_PROJECT_ID" --location "$GCP_REGION" >/dev/null 2>&1; then verb=update; else verb=create; fi
if $APPLY; then
  SECRET="${SCHEDULED_SYNC_SHARED_SECRET:-$(gcloud secrets versions access latest --secret SCHEDULED_SYNC_SHARED_SECRET --project "$GCP_PROJECT_ID")}"
  [[ -n "$SECRET" ]] || { echo "Scheduled sync secret is empty" >&2; exit 2; }
  FLAGS_FILE="$(mktemp "${TMPDIR:-/tmp}/chess-scheduler-flags.XXXXXX")"
  chmod 600 "$FLAGS_FILE"
  trap 'rm -f "$FLAGS_FILE"' EXIT
  SCHEDULER_HEADER_SECRET="$SECRET" python3 -c 'import json, os, sys; json.dump({"--headers": {"Content-Type": "application/json", "X-Scheduled-Sync-Secret": os.environ["SCHEDULER_HEADER_SECRET"]}}, open(sys.argv[1], "w"))' "$FLAGS_FILE"
  gcloud scheduler jobs "$verb" http "$SCHEDULER_JOB" --project "$GCP_PROJECT_ID" --location "$GCP_REGION" --schedule "$SCHEDULER_SCHEDULE" --time-zone "$SCHEDULER_TIME_ZONE" --uri "$TARGET" --http-method POST --oidc-service-account-email "$OIDC_ACCOUNT" --oidc-token-audience "$SYNC_SERVICE_URL" --flags-file="$FLAGS_FILE" --message-body '{"schema_version":1}' --attempt-deadline 300s --max-retry-attempts 3 --min-backoff 30s --max-backoff 300s --max-doublings 3 >/dev/null
  rm -f "$FLAGS_FILE"
  trap - EXIT
  unset SECRET
  echo "Scheduler job $verb completed (secret hidden)"
else
  echo "Would $verb Scheduler job $SCHEDULER_JOB"
  echo "  schedule=$SCHEDULER_SCHEDULE timezone=$SCHEDULER_TIME_ZONE"
  echo "  target=$TARGET audience=$SYNC_SERVICE_URL oidc=$OIDC_ACCOUNT"
  echo "  header X-Scheduled-Sync-Secret=<hidden> body={\"schema_version\":1}"
fi
