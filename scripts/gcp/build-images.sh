#!/usr/bin/env bash
source "$(dirname "$0")/common.sh" "$@"
case "${BUILD_TARGET:-backend}" in
  backend)
    if [[ "${FORCE_REBUILD:-false}" != true ]] && gcloud artifacts docker images describe "$BACKEND_IMAGE" --project "$GCP_PROJECT_ID" >/dev/null 2>&1; then
      echo "Backend image already exists; build skipped"
    else
      run gcloud builds submit "$ROOT_DIR/backend" --project "$GCP_PROJECT_ID" --tag "$BACKEND_IMAGE"
    fi
    ;;
  frontend)
    need BACKEND_URL
    if [[ "${FORCE_REBUILD:-false}" != true ]] && gcloud artifacts docker images describe "$FRONTEND_IMAGE" --project "$GCP_PROJECT_ID" >/dev/null 2>&1; then
      echo "Frontend image already exists; build skipped"
    else
      run gcloud builds submit "$ROOT_DIR" --project "$GCP_PROJECT_ID" --config "$ROOT_DIR/deploy/cloudbuild-frontend.yaml" --substitutions "_IMAGE=$FRONTEND_IMAGE,_BACKEND_URL=$BACKEND_URL,_SERVER_SYNC_ENABLED=true"
    fi
    ;;
  *) echo "BUILD_TARGET must be backend or frontend" >&2; exit 2 ;;
esac
