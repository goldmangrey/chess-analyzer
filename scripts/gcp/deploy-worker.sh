#!/usr/bin/env bash
source "$(dirname "$0")/common.sh" "$@"
need IMAGE_TAG
CONNECTION_NAME="$GCP_PROJECT_ID:$GCP_REGION:$CLOUD_SQL_INSTANCE"
INVOKER="$TASKS_INVOKER_SERVICE_ACCOUNT@$GCP_PROJECT_ID.iam.gserviceaccount.com"
WORKER_URL_VALUE="${WORKER_URL:-https://placeholder.invalid}"
ENV_VARS="APP_ENV=production,AUTO_CREATE_SCHEMA=false,ANALYSIS_QUEUE_BACKEND=cloud_tasks,GCP_PROJECT_ID=$GCP_PROJECT_ID,GCP_REGION=$GCP_REGION,CLOUD_TASKS_QUEUE=$CLOUD_TASKS_QUEUE,ANALYSIS_WORKER_URL=$WORKER_URL_VALUE,CLOUD_TASKS_SERVICE_ACCOUNT_EMAIL=$INVOKER,DATABASE_HOST=/cloudsql/$CONNECTION_NAME,DATABASE_NAME=$CLOUD_SQL_DATABASE,DATABASE_USER=$CLOUD_SQL_USER,DB_POOL_SIZE=2,DB_MAX_OVERFLOW=1,STOCKFISH_PATH=/usr/games/stockfish"
run gcloud run deploy "$WORKER_SERVICE" --project "$GCP_PROJECT_ID" --region "$GCP_REGION" --image "$IMAGE_TAG" --service-account "$WORKER_SERVICE_ACCOUNT@$GCP_PROJECT_ID.iam.gserviceaccount.com" --add-cloudsql-instances "$CONNECTION_NAME" --set-env-vars "$ENV_VARS" --set-secrets "DATABASE_PASSWORD=DATABASE_PASSWORD:latest,CHESSCOM_USER_AGENT=CHESSCOM_USER_AGENT:latest,ANALYSIS_WORKER_SHARED_SECRET=ANALYSIS_WORKER_SHARED_SECRET:latest" --port 8080 --timeout 1800 --concurrency 1 --cpu "${BACKEND_CPU:-1}" --memory "${BACKEND_MEMORY:-2Gi}" --min-instances 0 --max-instances "${BACKEND_MAX_INSTANCES:-2}" --no-allow-unauthenticated
run gcloud run services add-iam-policy-binding "$WORKER_SERVICE" --project "$GCP_PROJECT_ID" --region "$GCP_REGION" --member "serviceAccount:$INVOKER" --role roles/run.invoker
if $APPLY; then
  ACTUAL_WORKER_URL="$(gcloud run services describe "$WORKER_SERVICE" --project "$GCP_PROJECT_ID" --region "$GCP_REGION" --format='value(status.url)')"
  gcloud run services update "$WORKER_SERVICE" --project "$GCP_PROJECT_ID" --region "$GCP_REGION" --update-env-vars "ANALYSIS_WORKER_URL=$ACTUAL_WORKER_URL" >/dev/null
  echo "WORKER_URL=$ACTUAL_WORKER_URL"
fi
