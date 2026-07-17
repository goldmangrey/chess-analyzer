#!/usr/bin/env bash
source "$(dirname "$0")/common.sh" "$@"
run gcloud scheduler jobs run "$SCHEDULER_JOB" --project "$GCP_PROJECT_ID" --location "$GCP_REGION"
echo "Inspect status: gcloud scheduler jobs describe $SCHEDULER_JOB --location $GCP_REGION --project $GCP_PROJECT_ID"
echo "Inspect logs:  gcloud run services logs read $SYNC_SERVICE --region $GCP_REGION --project $GCP_PROJECT_ID"
echo "Then inspect GET /api/settings for last_sync_status and timestamps."
