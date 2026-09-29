#!/usr/bin/env bash
# Weekly pipeline: source new triggers, enrich, score, qualify, research the top
# leads, list what is due, and export the commission record.
# Usage: scripts/weekly_pipeline.sh [days_back] [dossier_count]
set -euo pipefail

DAYS="${1:-7}"
DOSSIERS="${2:-5}"

leadgen watch --days "$DAYS"
leadgen enrich
leadgen score --min-score 40 --top 40
leadgen qualify --min-score 40 --limit 40
if [ -n "${ANTHROPIC_API_KEY:-}${ANTHROPIC_AUTH_TOKEN:-}" ]; then
  leadgen dossier --min-score 55 --limit "$DOSSIERS"
else
  echo "no API key: skipping dossiers (set ANTHROPIC_API_KEY to enable)"
fi
leadgen due
leadgen report
leadgen export "data/pipeline_$(date -u +%Y%m%d).csv"
echo "Pipeline exported. Email the export to yourself and the partner as the timestamped commission record."
