#!/usr/bin/env bash
source "$(dirname "$0")/common.sh" "$@"
for account in "$BACKEND_SERVICE_ACCOUNT" "$WORKER_SERVICE_ACCOUNT" "$TASKS_INVOKER_SERVICE_ACCOUNT" "$SCHEDULER_SERVICE_ACCOUNT"; do
  if gcloud iam service-accounts describe "$account@$GCP_PROJECT_ID.iam.gserviceaccount.com" --project "$GCP_PROJECT_ID" >/dev/null 2>&1; then echo "$account exists"; else run gcloud iam service-accounts create "$account" --project "$GCP_PROJECT_ID" --display-name "$account"; fi
done
for role in roles/cloudsql.client roles/cloudtasks.enqueuer; do run gcloud projects add-iam-policy-binding "$GCP_PROJECT_ID" --member "serviceAccount:$BACKEND_SERVICE_ACCOUNT@$GCP_PROJECT_ID.iam.gserviceaccount.com" --role "$role"; done
run gcloud projects add-iam-policy-binding "$GCP_PROJECT_ID" --member "serviceAccount:$WORKER_SERVICE_ACCOUNT@$GCP_PROJECT_ID.iam.gserviceaccount.com" --role roles/cloudsql.client
PROJECT_NUMBER="$(gcloud projects describe "$GCP_PROJECT_ID" --format='value(projectNumber)' 2>/dev/null || true)"
[[ -n "$PROJECT_NUMBER" ]] && run gcloud iam service-accounts add-iam-policy-binding "$TASKS_INVOKER_SERVICE_ACCOUNT@$GCP_PROJECT_ID.iam.gserviceaccount.com" --project "$GCP_PROJECT_ID" --member "serviceAccount:service-$PROJECT_NUMBER@gcp-sa-cloudtasks.iam.gserviceaccount.com" --role roles/iam.serviceAccountTokenCreator
[[ -n "$PROJECT_NUMBER" ]] && run gcloud iam service-accounts add-iam-policy-binding "$SCHEDULER_SERVICE_ACCOUNT@$GCP_PROJECT_ID.iam.gserviceaccount.com" --project "$GCP_PROJECT_ID" --member "serviceAccount:service-$PROJECT_NUMBER@gcp-sa-cloudscheduler.iam.gserviceaccount.com" --role roles/iam.serviceAccountTokenCreator
echo "roles/run.invoker is granted on the private worker by deploy-worker.sh"
echo "Scheduler roles/run.invoker is granted only on the private sync service"
echo "Secret accessor is granted per secret by create-secrets.sh"
