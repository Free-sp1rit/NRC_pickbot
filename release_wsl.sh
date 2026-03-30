#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DIR="/mnt/g/MyBot/pickbot"

FILES=(
  "README.md"
  "pickbot.ahk"
  "config.ini"
  "run.ps1"
)

mkdir -p "$TARGET_DIR"

for file in "${FILES[@]}"; do
  install -m 0644 "$REPO_DIR/$file" "$TARGET_DIR/$file"
done

printf 'Released files to %s\n' "$TARGET_DIR"
