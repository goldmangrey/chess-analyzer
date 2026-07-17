#!/usr/bin/env bash
source "$(dirname "$0")/common.sh" "$@"

case "$CLOUD_SQL_EDITION" in
  enterprise|enterprise-plus) ;;
  *) echo "CLOUD_SQL_EDITION must be enterprise or enterprise-plus" >&2; exit 2 ;;
esac
for setting_name in CLOUD_SQL_TIER CLOUD_SQL_DATABASE_VERSION CLOUD_SQL_STORAGE_SIZE_GB; do
  setting_value="${!setting_name:-}"
  [[ -n "$setting_value" && "$setting_value" != your-* ]] || {
    echo "$setting_name must be configured and must not be a placeholder" >&2
    exit 2
  }
done
unset setting_name setting_value
[[ "$CLOUD_SQL_DATABASE_VERSION" == "POSTGRES_17" ]] || {
  echo "CLOUD_SQL_DATABASE_VERSION must be POSTGRES_17" >&2
  exit 2
}
[[ "$CLOUD_SQL_STORAGE_SIZE_GB" =~ ^[0-9]+$ ]] || {
  echo "CLOUD_SQL_STORAGE_SIZE_GB must be a positive integer" >&2
  exit 2
}
(( CLOUD_SQL_STORAGE_SIZE_GB > 0 )) || {
  echo "CLOUD_SQL_STORAGE_SIZE_GB must be greater than zero" >&2
  exit 2
}
if [[ "$CLOUD_SQL_TIER" == "db-f1-micro" && "$CLOUD_SQL_EDITION" != "enterprise" ]]; then
  echo "db-f1-micro is available only with CLOUD_SQL_EDITION=enterprise" >&2
  exit 2
fi

if ! gcloud sql instances describe "$CLOUD_SQL_INSTANCE" \
  --project "$GCP_PROJECT_ID" >/dev/null 2>&1; then
  run gcloud sql instances create "$CLOUD_SQL_INSTANCE" \
    --project "$GCP_PROJECT_ID" \
    --region "$GCP_REGION" \
    --database-version "$CLOUD_SQL_DATABASE_VERSION" \
    --edition "$CLOUD_SQL_EDITION" \
    --tier "$CLOUD_SQL_TIER" \
    --storage-size "$CLOUD_SQL_STORAGE_SIZE_GB" \
    --storage-type SSD \
    --storage-auto-increase \
    --backup-start-time 02:00
fi

if gcloud sql databases describe "$CLOUD_SQL_DATABASE" \
  --instance "$CLOUD_SQL_INSTANCE" \
  --project "$GCP_PROJECT_ID" >/dev/null 2>&1; then
  echo "Database exists"
else
  run gcloud sql databases create "$CLOUD_SQL_DATABASE" \
    --instance "$CLOUD_SQL_INSTANCE" \
    --project "$GCP_PROJECT_ID"
fi

if $APPLY; then
  if gcloud sql users list \
    --instance "$CLOUD_SQL_INSTANCE" \
    --project "$GCP_PROJECT_ID" \
    --filter="name=$CLOUD_SQL_USER" \
    --format='value(name)' | grep -qx "$CLOUD_SQL_USER"; then
    echo "Database user exists; password unchanged"
  else
    [[ -n "${DATABASE_PASSWORD:-}" ]] || {
      echo "DATABASE_PASSWORD environment value required to create database user" >&2
      exit 2
    }
    gcloud sql users create "$CLOUD_SQL_USER" \
      --instance "$CLOUD_SQL_INSTANCE" \
      --project "$GCP_PROJECT_ID" \
      --password "$DATABASE_PASSWORD" >/dev/null
  fi

  gcloud sql instances describe "$CLOUD_SQL_INSTANCE" \
    --project "$GCP_PROJECT_ID" \
    --format='value(connectionName)'
else
  echo "Would create missing database user; existing password remains unchanged"
fi
