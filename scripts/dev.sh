#!/usr/bin/env bash
set -u

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_PID=""
FRONTEND_PID=""

cleanup() {
  trap - INT TERM EXIT
  [[ -n "$BACKEND_PID" ]] && kill "$BACKEND_PID" 2>/dev/null || true
  [[ -n "$FRONTEND_PID" ]] && kill "$FRONTEND_PID" 2>/dev/null || true
  wait 2>/dev/null || true
}
trap cleanup INT TERM EXIT

[[ -x "$ROOT_DIR/backend/.venv/bin/python" ]] || { echo "Ошибка: создайте backend/.venv" >&2; exit 1; }
[[ -d "$ROOT_DIR/frontend/node_modules" ]] || { echo "Ошибка: выполните npm install в frontend" >&2; exit 1; }
[[ -f "$ROOT_DIR/backend/.env" ]] || echo "⚠ backend/.env отсутствует — используются defaults"

echo "Frontend: http://localhost:3000"
echo "Backend:  http://127.0.0.1:8000"
echo "Swagger:  http://127.0.0.1:8000/docs"

(cd "$ROOT_DIR/backend" && .venv/bin/python run.py) &
BACKEND_PID=$!
(cd "$ROOT_DIR/frontend" && npm run dev) &
FRONTEND_PID=$!

wait "$BACKEND_PID" "$FRONTEND_PID"
