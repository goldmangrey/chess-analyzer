#!/usr/bin/env bash
set -u

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
failures=0

ok() { printf '✓ %s\n' "$1"; }
warn() { printf '⚠ %s\n' "$1"; }
fail() { printf '✗ %s\n' "$1"; failures=$((failures + 1)); }
has() { command -v "$1" >/dev/null 2>&1; }
port_open() { lsof -nP -iTCP:"$1" -sTCP:LISTEN >/dev/null 2>&1; }

has python3 && ok "Python найден" || fail "Python 3 не найден"
has node && ok "Node.js найден" || fail "Node.js не найден"
has npm && ok "npm найден" || fail "npm не найден"
[[ -x "$ROOT_DIR/backend/.venv/bin/python" ]] && ok "Backend venv найден" || fail "Backend venv отсутствует"
[[ -d "$ROOT_DIR/frontend/node_modules" ]] && ok "Frontend dependencies найдены" || fail "frontend/node_modules отсутствует"
[[ -f "$ROOT_DIR/backend/.env" ]] && ok "backend/.env найден" || warn "backend/.env отсутствует; будут использованы defaults"
[[ -f "$ROOT_DIR/frontend/.env.local" ]] && ok "frontend/.env.local найден" || warn "frontend/.env.local отсутствует; будет использован fallback API URL"

if [[ -f "$ROOT_DIR/frontend/.env.local" ]]; then
  api_base_url="$(sed -n 's/^NEXT_PUBLIC_API_BASE_URL=//p' "$ROOT_DIR/frontend/.env.local" | tail -n 1 | tr -d '\r')"
  api_base_without_slashes="$(printf '%s' "$api_base_url" | sed 's:/*$::')"
  if [[ "$api_base_without_slashes" == */api ]]; then
    warn "NEXT_PUBLIC_API_BASE_URL должен быть origin без /api: $api_base_url"
  fi
fi

database_url="sqlite:///./data/chess.db"
app_env="development"
auto_create_schema="true"
if [[ -f "$ROOT_DIR/backend/.env" ]]; then
  configured_database_url="$(sed -n 's/^DATABASE_URL=//p' "$ROOT_DIR/backend/.env" | tail -n 1 | tr -d '\r')"
  configured_app_env="$(sed -n 's/^APP_ENV=//p' "$ROOT_DIR/backend/.env" | tail -n 1 | tr -d '\r')"
  configured_auto_create="$(sed -n 's/^AUTO_CREATE_SCHEMA=//p' "$ROOT_DIR/backend/.env" | tail -n 1 | tr -d '\r')"
  [[ -n "$configured_database_url" ]] && database_url="$configured_database_url"
  [[ -n "$configured_app_env" ]] && app_env="$configured_app_env"
  [[ -n "$configured_auto_create" ]] && auto_create_schema="$configured_auto_create"
fi
case "$database_url" in
  postgres://*|postgresql://*|postgresql+psycopg://*)
    "$ROOT_DIR/backend/.venv/bin/python" -c 'import psycopg' >/dev/null 2>&1 && ok "PostgreSQL driver psycopg найден" || fail "PostgreSQL driver psycopg отсутствует"
    safe_database="$(PYTHONPATH="$ROOT_DIR/backend" DATABASE_URL="$database_url" "$ROOT_DIR/backend/.venv/bin/python" -c 'import os; from app.database_url import safe_database_description; print(safe_database_description(os.environ["DATABASE_URL"]))' 2>/dev/null)"
    [[ -n "$safe_database" ]] && ok "Database: $safe_database"
    [[ "$(printf '%s' "$auto_create_schema" | tr '[:upper:]' '[:lower:]')" == "true" ]] && warn "Для PostgreSQL установите AUTO_CREATE_SCHEMA=false"
    ;;
  sqlite:* )
    [[ -d "$ROOT_DIR/backend/data" ]] && ok "SQLite directory найден" || warn "backend/data будет создан перед первым локальным запуском"
    ;;
  * ) fail "Неподдерживаемый DATABASE_URL" ;;
esac
if [[ "$(printf '%s' "$app_env" | tr '[:upper:]' '[:lower:]')" == "production" && "$(printf '%s' "$auto_create_schema" | tr '[:upper:]' '[:lower:]')" == "true" ]]; then
  warn "Production environment не должен использовать AUTO_CREATE_SCHEMA=true"
fi

stockfish_path=""
if [[ -f "$ROOT_DIR/backend/.env" ]]; then
  stockfish_path="$(sed -n 's/^STOCKFISH_PATH=//p' "$ROOT_DIR/backend/.env" | tail -n 1)"
fi
[[ -z "$stockfish_path" ]] && stockfish_path="/opt/homebrew/bin/stockfish"
if [[ "$stockfish_path" != /* ]]; then stockfish_path="$ROOT_DIR/backend/$stockfish_path"; fi
[[ -x "$stockfish_path" ]] && ok "Stockfish найден: $stockfish_path" || warn "Stockfish не найден или не executable: $stockfish_path"

port_open 8000 && warn "Backend port 8000 уже занят" || ok "Backend port 8000 свободен"
port_open 3000 && warn "Frontend port 3000 уже занят" || ok "Frontend port 3000 свободен"

exit "$failures"
