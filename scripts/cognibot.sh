#!/usr/bin/env bash
set -euo pipefail

COGNIBOT_HOME="${COGNIBOT_HOME:-$HOME/.cognibot}"
PY="${COGNIBOT_PYTHON:-python3}"
VENV="$COGNIBOT_HOME/venv"
BIN="$VENV/bin/cognibot"

if [ ! -x "$BIN" ]; then
  mkdir -p "$COGNIBOT_HOME"
  "$PY" -m venv "$VENV"
  "$VENV/bin/pip" install -U pip --quiet

  # Option A (PyPI, when published):
  # "$VENV/bin/pip" install -U cognibot

  # Option B (GitHub main):
  "$VENV/bin/pip" install -U "git+https://github.com/robotaitai/cognibot.git@main"
fi

exec "$BIN" "$@"
