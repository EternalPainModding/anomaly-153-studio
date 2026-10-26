#!/usr/bin/env bash
set -euo pipefail
STUDIO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$STUDIO_DIR"

PORT="${ANOMALY_STUDIO_PORT:-8780}"
echo "[Anomaly Studio v0.1.0-alpha] Starting backend server on http://127.0.0.1:${PORT} ..."

# Kill any existing server on this port
fuser -k "${PORT}/tcp" >/dev/null 2>&1 || true

setsid nohup python3 "$STUDIO_DIR/backend/server.py" --port "$PORT" > "$STUDIO_DIR/.studio_cache/server.log" 2>&1 &
SERVER_PID=$!
echo "$SERVER_PID" > "$STUDIO_DIR/.studio_cache/server.pid"

for i in $(seq 1 30); do
    if curl -fsS "http://127.0.0.1:${PORT}/api/settings" >/dev/null 2>&1; then
        echo "[Anomaly Studio v0.1.0-alpha] Server ready (PID ${SERVER_PID})."
        break
    fi
    sleep 0.3
done

if command -v xdg-open >/dev/null 2>&1 && [ -n "${DISPLAY:-}" ]; then
    xdg-open "http://127.0.0.1:${PORT}" >/dev/null 2>&1 || true
fi
