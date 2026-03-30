#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DIR="/mnt/g/MyBot/pickbot"
TARGET_WIN='G:\MyBot\pickbot'

STAGING_FILES=(
  "README.md"
  "USER_GUIDE.md"
  "pickbot.ahk"
  "config.ini"
  "build.ps1"
)

mkdir -p "$TARGET_DIR"
rm -f "$TARGET_DIR/run.ps1"

for file in "${STAGING_FILES[@]}"; do
  install -m 0644 "$REPO_DIR/$file" "$TARGET_DIR/$file"
done

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "${TARGET_WIN}\\build.ps1"

rm -f \
  "$TARGET_DIR/pickbot.ahk" \
  "$TARGET_DIR/build.ps1" \
  "$TARGET_DIR/run.ps1"

printf 'Released final artifacts to %s\n' "$TARGET_DIR"
