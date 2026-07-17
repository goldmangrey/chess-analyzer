#!/usr/bin/env bash
source "$(dirname "$0")/common.sh" "$@"
ENV_VARS="APP_ENV=production,AUTO_CREATE_SCHEMA=false,DATABASE_HOST=/cloudsql/$CLOUD_SQL_CONNECTION_NAME,DATABASE_NAME=$CLOUD_SQL_DATABASE,DATABASE_USER=$CLOUD_SQL_USER,DB_POOL_SIZE=1,DB_MAX_OVERFLOW=0"
run gcloud run jobs deploy "$MIGRATION_JOB" \
  --project "$GCP_PROJECT_ID" --region "$GCP_REGION" \
  --image "$BACKEND_IMAGE" \
  --service-account "$BACKEND_SERVICE_ACCOUNT_EMAIL" \
  --set-cloudsql-instances "$CLOUD_SQL_CONNECTION_NAME" \
  --set-env-vars "$ENV_VARS" \
  --set-secrets "DATABASE_PASSWORD=DATABASE_PASSWORD:latest" \
  --command alembic --args upgrade,head --tasks 1 --parallelism 1 \
  --max-retries 0 --task-timeout 10m --quiet
