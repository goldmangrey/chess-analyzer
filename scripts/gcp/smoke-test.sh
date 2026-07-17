#!/usr/bin/env bash
source "$(dirname "$0")/common.sh" "$@"
need BACKEND_URL; need FRONTEND_URL
run curl --fail --silent --show-error "$BACKEND_URL/health"
run curl --fail --silent --show-error "$BACKEND_URL/api/system/status"
run curl --fail --silent --show-error "$BACKEND_URL/api/settings"
run curl --fail --silent --show-error "$FRONTEND_URL/"
run curl --fail --silent --show-error -X OPTIONS "$BACKEND_URL/api/settings" -H "Origin: $FRONTEND_URL" -H "Access-Control-Request-Method: GET"
if $APPLY; then code="$(curl -sS -o /dev/null -w '%{http_code}' -X POST "$WORKER_URL/internal/tasks/analyze-game" -H 'Content-Type: application/json' -d '{"game_id":1,"schema_version":1}')"; [[ "$code" == 401 || "$code" == 403 ]] || { echo "Worker unauthenticated check returned $code" >&2; exit 1; }; fi
