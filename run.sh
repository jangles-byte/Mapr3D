#!/usr/bin/env bash
# Mapr3D launcher — starts the backend (FastAPI) and frontend (Vite) together.
# Installs dependencies on first run. Ctrl+C stops both.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_PORT="${MAPR3D_BACKEND_PORT:-8000}"
FRONTEND_PORT="${MAPR3D_FRONTEND_PORT:-5173}"

command -v uv  >/dev/null 2>&1 || { echo "error: 'uv' not found (https://docs.astral.sh/uv/)"; exit 1; }
command -v npm >/dev/null 2>&1 || { echo "error: 'npm' not found (install Node.js)"; exit 1; }

echo "Mapr3D — starting up"
echo "  root: $ROOT"

if [ ! -d "$ROOT/backend/.venv" ]; then
  echo "→ Installing backend dependencies (uv sync)…"
  (cd "$ROOT/backend" && uv sync)
fi
if [ ! -d "$ROOT/frontend/node_modules" ]; then
  echo "→ Installing frontend dependencies (npm install)…"
  (cd "$ROOT/frontend" && npm install)
fi

pids=()
cleanup() {
  echo ""
  echo "Shutting down…"
  if [ "${#pids[@]}" -gt 0 ]; then
    for pid in "${pids[@]}"; do
      kill "$pid" 2>/dev/null || true
    done
  fi
  wait 2>/dev/null || true
}
trap cleanup INT TERM EXIT

echo "→ Backend   http://localhost:${BACKEND_PORT}  (API docs at /docs)"
(cd "$ROOT/backend" && exec uv run uvicorn mapr3d.main:app --port "$BACKEND_PORT" --reload) &
pids+=($!)

echo "→ Frontend  http://localhost:${FRONTEND_PORT}"
(cd "$ROOT/frontend" && exec npm run dev -- --port "$FRONTEND_PORT") &
pids+=($!)

echo ""
echo "Mapr3D is running → open http://localhost:${FRONTEND_PORT}"
echo "Press Ctrl+C to stop both servers."
wait
