#!/usr/bin/env bash
source "$(dirname "$0")/common.sh" "$@"
need FRONTEND_IMAGE_TAG
run gcloud run deploy "$FRONTEND_SERVICE" --project "$GCP_PROJECT_ID" --region "$GCP_REGION" --image "$FRONTEND_IMAGE_TAG" --port 8080 --cpu 1 --memory "${FRONTEND_MEMORY:-512Mi}" --concurrency 80 --min-instances 0 --max-instances 2 --allow-unauthenticated
if $APPLY; then echo "FRONTEND_URL=$(gcloud run services describe "$FRONTEND_SERVICE" --project "$GCP_PROJECT_ID" --region "$GCP_REGION" --format='value(status.url)')"; fi
