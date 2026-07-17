#!/usr/bin/env bash
source "$(dirname "$0")/common.sh" "$@"
if gcloud artifacts repositories describe "$ARTIFACT_REPOSITORY" --project "$GCP_PROJECT_ID" --location "$GCP_REGION" >/dev/null 2>&1; then echo "Artifact Registry exists"; else run gcloud artifacts repositories create "$ARTIFACT_REPOSITORY" --project "$GCP_PROJECT_ID" --location "$GCP_REGION" --repository-format docker --description "Chess AI Teacher images"; fi
