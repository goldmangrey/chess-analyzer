#!/usr/bin/env bash
source "$(dirname "$0")/common.sh" "$@"
command -v gcloud >/dev/null || { echo "gcloud is not installed" >&2; exit 1; }
ACCOUNT="$(gcloud auth list --filter=status:ACTIVE --format='value(account)' | head -n1)"
[[ -n "$ACCOUNT" ]] || { echo "No active gcloud account" >&2; exit 1; }
[[ "$GCP_PROJECT_ID" != your-* ]] || { echo "Replace placeholder project ID" >&2; exit 1; }
[[ "$GCP_REGION" =~ ^[a-z]+-[a-z]+[0-9]$ ]] || { echo "Invalid region" >&2; exit 1; }
for secret in DATABASE_PASSWORD CHESSCOM_USER_AGENT ANALYSIS_WORKER_SHARED_SECRET; do gcloud secrets describe "$secret" --project "$GCP_PROJECT_ID" >/dev/null 2>&1 && echo "✓ secret $secret exists" || echo "⚠ secret $secret is not created"; done
echo "Account: $ACCOUNT"; echo "Project: $GCP_PROJECT_ID"; echo "Region: $GCP_REGION"
echo "Git SHA: $(git -C "$ROOT_DIR" rev-parse --short=12 HEAD)"
git -C "$ROOT_DIR" diff --quiet || echo "⚠ working tree has uncommitted changes"
