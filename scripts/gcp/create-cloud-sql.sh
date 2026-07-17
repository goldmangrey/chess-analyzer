#!/usr/bin/env bash
source "$(dirname "$0")/common.sh" "$@"
if ! gcloud sql instances describe "$CLOUD_SQL_INSTANCE" --project "$GCP_PROJECT_ID" >/dev/null 2>&1; then run gcloud sql instances create "$CLOUD_SQL_INSTANCE" --project "$GCP_PROJECT_ID" --region "$GCP_REGION" --database-version POSTGRES_17 --tier db-f1-micro --storage-size 10 --storage-type SSD --storage-auto-increase --backup-start-time 02:00; fi
if gcloud sql databases describe "$CLOUD_SQL_DATABASE" --instance "$CLOUD_SQL_INSTANCE" --project "$GCP_PROJECT_ID" >/dev/null 2>&1; then echo "Database exists"; else run gcloud sql databases create "$CLOUD_SQL_DATABASE" --instance "$CLOUD_SQL_INSTANCE" --project "$GCP_PROJECT_ID"; fi
if $APPLY; then
  [[ -n "${DATABASE_PASSWORD:-}" ]] || { echo "DATABASE_PASSWORD environment value required" >&2; exit 2; }
  if gcloud sql users list --instance "$CLOUD_SQL_INSTANCE" --project "$GCP_PROJECT_ID" --filter="name=$CLOUD_SQL_USER" --format='value(name)' | grep -qx "$CLOUD_SQL_USER"; then
    gcloud sql users set-password "$CLOUD_SQL_USER" --instance "$CLOUD_SQL_INSTANCE" --project "$GCP_PROJECT_ID" --password "$DATABASE_PASSWORD" >/dev/null
  else
    gcloud sql users create "$CLOUD_SQL_USER" --instance "$CLOUD_SQL_INSTANCE" --project "$GCP_PROJECT_ID" --password "$DATABASE_PASSWORD" >/dev/null
  fi
  gcloud sql instances describe "$CLOUD_SQL_INSTANCE" --project "$GCP_PROJECT_ID" --format='value(connectionName)'
else echo "Would create/update database user (password hidden)"; fi
