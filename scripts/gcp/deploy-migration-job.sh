#!/usr/bin/env bash
source "$(dirname "$0")/common.sh" "$@"
need IMAGE_TAG
CONNECTION_NAME="$GCP_PROJECT_ID:$GCP_REGION:$CLOUD_SQL_INSTANCE"
ENV_VARS="APP_ENV=production,AUTO_CREATE_SCHEMA=false,ANALYSIS_QUEUE_BACKEND=cloud_tasks,GCP_PROJECT_ID=$GCP_PROJECT_ID,GCP_REGION=$GCP_REGION,CLOUD_TASKS_QUEUE=$CLOUD_TASKS_QUEUE,ANALYSIS_WORKER_URL=${WORKER_URL:-https://placeholder.invalid},CLOUD_TASKS_SERVICE_ACCOUNT_EMAIL=$TASKS_INVOKER_SERVICE_ACCOUNT@$GCP_PROJECT_ID.iam.gserviceaccount.com,DATABASE_HOST=/cloudsql/$CONNECTION_NAME,DATABASE_NAME=$CLOUD_SQL_DATABASE,DATABASE_USER=$CLOUD_SQL_USER,STOCKFISH_PATH=/usr/games/stockfish"
run gcloud run jobs deploy "$MIGRATION_JOB" --project "$GCP_PROJECT_ID" --region "$GCP_REGION" --image "$IMAGE_TAG" --service-account "$BACKEND_SERVICE_ACCOUNT@$GCP_PROJECT_ID.iam.gserviceaccount.com" --add-cloudsql-instances "$CONNECTION_NAME" --set-env-vars "$ENV_VARS" --set-secrets "DATABASE_PASSWORD=DATABASE_PASSWORD:latest,CHESSCOM_USER_AGENT=CHESSCOM_USER_AGENT:latest,ANALYSIS_WORKER_SHARED_SECRET=ANALYSIS_WORKER_SHARED_SECRET:latest" --command alembic --args upgrade,head --tasks 1 --parallelism 1 --max-retries 0 --task-timeout 10m
