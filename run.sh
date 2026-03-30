#!/usr/bin/env zsh
set -eu

export PYTHONUNBUFFERED=1
export HOST="${HOST:-127.0.0.1}"
export PORT="${PORT:-8000}"
export MAX_WS_MESSAGE_BYTES="${MAX_WS_MESSAGE_BYTES:-4000000}"

uvicorn app.main:app \
  --reload \
  --host "${HOST}" \
  --port "${PORT}" \
  --ws-max-size "${MAX_WS_MESSAGE_BYTES}"
