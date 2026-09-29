#!/usr/bin/env bash
# Install a Monday 07:00 cron job that runs the weekly pipeline and emails the report.
# Usage: scripts/install_cron.sh   (run from the repo root, after `pip install -e .` and filling .env)
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
LOG_DIR="$REPO/data/logs"
mkdir -p "$LOG_DIR"
LINE="0 7 * * 1 cd $REPO && set -a && . ./.env && set +a && scripts/weekly_pipeline.sh 7 5 >> $LOG_DIR/weekly_\$(date +\%Y\%m\%d).log 2>&1"

if crontab -l 2>/dev/null | grep -Fq "scripts/weekly_pipeline.sh"; then
  echo "cron job already installed:"
  crontab -l | grep -F "scripts/weekly_pipeline.sh"
  exit 0
fi
( crontab -l 2>/dev/null; echo "$LINE" ) | crontab -
echo "installed: $LINE"
echo "The pipeline runs every Monday at 07:00 local time; logs land in $LOG_DIR."
