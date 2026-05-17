#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
PORT="${1:-8080}"
PID_FILE="$ROOT_DIR/.server.pid"
LOG_FILE="$ROOT_DIR/.server.log"

if [[ -f "$ROOT_DIR/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT_DIR/.env"
  set +a
fi

detect_ip() {
  local ip=""
  ip="$(ifconfig en0 2>/dev/null | awk '/inet / {print $2; exit}')"
  if [[ -z "$ip" ]]; then
    ip="$(ifconfig en1 2>/dev/null | awk '/inet / {print $2; exit}')"
  fi
  echo "$ip"
}

print_urls() {
  local ip="$1"
  echo "Local URL: http://127.0.0.1:$PORT/index.html"
  if [[ -n "$ip" ]]; then
    echo "iPad URL:  http://$ip:$PORT/index.html"
  else
    echo "iPad URL:  (IP auto-detect failed. Check with: ifconfig en0)"
  fi
}

print_tts_status() {
  echo "TTS:       Browser SpeechSynthesisUtterance"
}

if [[ -f "$PID_FILE" ]]; then
  OLD_PID="$(cat "$PID_FILE")"
  if kill -0 "$OLD_PID" >/dev/null 2>&1; then
    echo "Server is already running (PID: $OLD_PID)."
    print_urls "$(detect_ip)"
    print_tts_status
    echo "If you want to restart it, run: ./stop-server.sh"
    exit 0
  fi
fi

cd "$ROOT_DIR"
nohup python3 "$ROOT_DIR/server.py" "$PORT" >"$LOG_FILE" 2>&1 &
NEW_PID=$!
echo "$NEW_PID" >"$PID_FILE"

sleep 1
if ! kill -0 "$NEW_PID" >/dev/null 2>&1; then
  echo "Server failed to start."
  rm -f "$PID_FILE"
  if [[ -f "$LOG_FILE" ]]; then
    tail -n 20 "$LOG_FILE"
  fi
  exit 1
fi

echo "Server started."
echo "PID: $NEW_PID"
echo "Port: $PORT"
echo "Log: $LOG_FILE"
print_urls "$(detect_ip)"
print_tts_status
