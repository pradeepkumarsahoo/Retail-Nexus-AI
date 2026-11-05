#!/usr/bin/env bash
# Author: Pradeep Sahoo — Retail Nexus AI
# Regenerate synthetic data, wipe DB, reload. Safe to re-run.
set -euo pipefail
cd "$(dirname "$0")/.."
cd backend
python -m app.data.generate --seed 42
python -m app.data.load
echo "DB reset and reloaded."
