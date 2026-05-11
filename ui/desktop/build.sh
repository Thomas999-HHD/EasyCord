#!/usr/bin/env bash
# EasyCord desktop build (macOS/Linux — produces a binary, not .exe)
set -euo pipefail
cd "$(dirname "$0")"

echo "[1/3] Creating venv..."
[ -d .venv ] || python3 -m venv .venv
source .venv/bin/activate

echo "[2/3] Installing deps..."
python -m pip install --upgrade pip >/dev/null
python -m pip install -r requirements.txt

echo "[3/3] Building..."
pyinstaller --clean --noconfirm easycord.spec

echo "Done. Output: dist/EasyCord"
