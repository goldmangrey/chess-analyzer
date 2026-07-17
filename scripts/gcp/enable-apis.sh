#!/usr/bin/env bash
source "$(dirname "$0")/common.sh" "$@"
echo "Google APIs (Cloud Scheduler intentionally excluded)"
run gcloud services enable --project "$GCP_PROJECT_ID" run.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com sqladmin.googleapis.com secretmanager.googleapis.com cloudtasks.googleapis.com iam.googleapis.com iamcredentials.googleapis.com
