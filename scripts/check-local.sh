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
