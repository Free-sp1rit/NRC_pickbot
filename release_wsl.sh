#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DIR="/mnt/g/MyBot/pickbot"
TARGET_WIN='G:\MyBot\pickbot'

cleanup_release_temp() {
  rm -f \
    "$TARGET_DIR/pickbot.py" \
    "$TARGET_DIR/requirements.txt" \
    "$TARGET_DIR/build.ps1"
  rm -rf \
    "$TARGET_DIR/.venv-build" \
    "$TARGET_DIR/build" \
    "$TARGET_DIR/dist" \
    "$TARGET_DIR/templates"
}

trap cleanup_release_temp EXIT

install -m 0644 "$REPO_DIR/pickbot.py" "$TARGET_DIR/pickbot.py"
install -m 0644 "$REPO_DIR/requirements.txt" "$TARGET_DIR/requirements.txt"
install -m 0644 "$REPO_DIR/config.json" "$TARGET_DIR/config.json"
install -m 0644 "$REPO_DIR/README.md" "$TARGET_DIR/README.md"
install -m 0644 "$REPO_DIR/USER_GUIDE.md" "$TARGET_DIR/USER_GUIDE.md"
install -m 0644 "$REPO_DIR/build.ps1" "$TARGET_DIR/build.ps1"

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "${TARGET_WIN}\\build.ps1"

if [ -f "$TARGET_DIR/dist/pickbot.exe" ]; then
  mv -f "$TARGET_DIR/dist/pickbot.exe" "$TARGET_DIR/pickbot.exe"
fi

printf 'Released final artifacts to %s\n' "$TARGET_DIR"
