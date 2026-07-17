#!/usr/bin/env bash
source "$(dirname "$0")/common.sh" "$@"
GIT_SHA="${GIT_SHA:-$(git -C "$ROOT_DIR" rev-parse --short=12 HEAD)}"
REGISTRY="$GCP_REGION-docker.pkg.dev/$GCP_PROJECT_ID/$ARTIFACT_REPOSITORY"
run gcloud builds submit "$ROOT_DIR/backend" --project "$GCP_PROJECT_ID" --tag "$REGISTRY/backend:$GIT_SHA"
if [[ -n "${BACKEND_URL:-}" ]]; then run gcloud builds submit "$ROOT_DIR" --project "$GCP_PROJECT_ID" --config "$ROOT_DIR/deploy/cloudbuild-frontend.yaml" --substitutions "_IMAGE=$REGISTRY/frontend:$GIT_SHA,_BACKEND_URL=$BACKEND_URL,_SERVER_SYNC_ENABLED=${SERVER_SYNC_ENABLED:-true}"; else echo "BACKEND_URL absent: frontend image intentionally skipped"; fi
echo "GIT_SHA=$GIT_SHA"
