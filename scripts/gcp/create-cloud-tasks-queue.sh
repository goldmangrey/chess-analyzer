#!/usr/bin/env bash
source "$(dirname "$0")/common.sh" "$@"
if gcloud tasks queues describe "$CLOUD_TASKS_QUEUE" --project "$GCP_PROJECT_ID" --location "$GCP_REGION" >/dev/null 2>&1; then verb=update; else verb=create; fi
run gcloud tasks queues "$verb" "$CLOUD_TASKS_QUEUE" --project "$GCP_PROJECT_ID" --location "$GCP_REGION" --max-dispatches-per-second 1 --max-concurrent-dispatches 1 --max-attempts 5 --min-backoff 10s --max-backoff 300s --max-retry-duration 3600s
