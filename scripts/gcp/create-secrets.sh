#!/usr/bin/env bash
source "$(dirname "$0")/common.sh" "$@"
for name in DATABASE_PASSWORD CHESSCOM_USER_AGENT ANALYSIS_WORKER_SHARED_SECRET; do
  if ! gcloud secrets describe "$name" --project "$GCP_PROJECT_ID" >/dev/null 2>&1; then run gcloud secrets create "$name" --project "$GCP_PROJECT_ID" --replication-policy automatic; fi
  for account in "$BACKEND_SERVICE_ACCOUNT" "$WORKER_SERVICE_ACCOUNT"; do run gcloud secrets add-iam-policy-binding "$name" --project "$GCP_PROJECT_ID" --member "serviceAccount:$account@$GCP_PROJECT_ID.iam.gserviceaccount.com" --role roles/secretmanager.secretAccessor; done
  if $APPLY; then
    [[ -n "${!name:-}" ]] || { echo "$name must be supplied through environment" >&2; exit 2; }
    printf '%s' "${!name}" | gcloud secrets versions add "$name" --project "$GCP_PROJECT_ID" --data-file=- >/dev/null
    echo "Added a new version to $name"
  else echo "Would add a secret version to $name from environment (value hidden)"; fi
done
