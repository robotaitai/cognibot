---
name: cognibot-install-or-update
description: Install (or update) the cognibot CLI in an isolated venv under ~/.cognibot.
---

# Install or update cognibot CLI

Goal: get a working `cognibot` command without cloning repos or touching the project venv.

## Do this in the terminal

1) Ensure venv support exists (Jetson/Ubuntu may need it):
- `python3 -m venv --help` should work
- if it fails, install venv support (Ubuntu): `sudo apt-get update && sudo apt-get install -y python3-venv`

2) Install/update into a dedicated venv:
```bash
set -e
COGNIBOT_HOME="$HOME/.cognibot"
python3 -m venv "$COGNIBOT_HOME/venv"
"$COGNIBOT_HOME/venv/bin/pip" install -U pip
"$COGNIBOT_HOME/venv/bin/pip" install -U "git+https://github.com/robotaitai/cognibot.git@main"
"$COGNIBOT_HOME/venv/bin/cognibot" --help

mkdir -p "$HOME/.local/bin"
ln -sf "$HOME/.cognibot/venv/bin/cognibot" "$HOME/.local/bin/cognibot"
echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc" || true