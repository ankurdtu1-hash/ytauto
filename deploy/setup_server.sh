#!/usr/bin/env bash
# One-time setup on a fresh Ubuntu 24.04 server. Run from the project folder:  bash deploy/setup_server.sh
set -euo pipefail
cd "$(dirname "$0")/.."

sudo apt-get update
sudo apt-get install -y python3-venv ffmpeg fonts-noto-core fonts-noto-ui-core
sudo timedatectl set-timezone Asia/Kolkata

python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt

mkdir -p logs output data assets/music
for f in .env token.json; do
  [ -f "$f" ] || echo "WARNING: $f is missing - copy it to $(pwd)/$f"
done

# Install the schedule (replaces any previous ytauto lines).
DIR="$(pwd)"
( crontab -l 2>/dev/null | grep -v ytauto || true
  sed "s#__DIR__#${DIR}#g" deploy/crontab.txt ) | crontab -
echo "Schedule installed:"
crontab -l
