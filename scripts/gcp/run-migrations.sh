#!/usr/bin/env bash
source "$(dirname "$0")/common.sh" "$@"
run gcloud run jobs execute "$MIGRATION_JOB" --project "$GCP_PROJECT_ID" --region "$GCP_REGION" --wait
