#!/usr/bin/env bash
source "$(dirname "$0")/common.sh" "$@"
need SYNC_SERVICE_URL
JOB_URI="$(gcloud scheduler jobs describe "$SCHEDULER_JOB" --project "$GCP_PROJECT_ID" --location "$GCP_REGION" --format='value(httpTarget.uri)' 2>/dev/null || true)"
JOB_ACCOUNT="$(gcloud scheduler jobs describe "$SCHEDULER_JOB" --project "$GCP_PROJECT_ID" --location "$GCP_REGION" --format='value(httpTarget.oidcToken.serviceAccountEmail)' 2>/dev/null || true)"
[[ "$JOB_URI" == "$SYNC_SERVICE_URL/internal/sync/chess-com" ]] || { echo "Scheduler target mismatch" >&2; exit 1; }
[[ "$JOB_ACCOUNT" == "$SCHEDULER_SERVICE_ACCOUNT@$GCP_PROJECT_ID.iam.gserviceaccount.com" ]] || { echo "Scheduler OIDC account mismatch" >&2; exit 1; }
echo "Scheduler configuration is consistent. No job was invoked."
if $APPLY; then
  gcloud scheduler jobs run "$SCHEDULER_JOB" --project "$GCP_PROJECT_ID" --location "$GCP_REGION"
  echo "Invocation requested. Check job status and sync service logs; no secret was printed."
fi
