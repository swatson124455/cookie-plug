#!/usr/bin/env bash
# Weekly pipeline: source new triggers, enrich, score, qualify, research the top
# leads, list what is due, and export the commission record.
# Usage: scripts/weekly_pipeline.sh [days_back] [dossier_count]
set -euo pipefail

DAYS="${1:-7}"
DOSSIERS="${2:-5}"

leadgen watch --days "$DAYS"
if [ -n "${NETLIFY_AUTH_TOKEN:-}" ] && [ -n "${NETLIFY_SITE_ID:-}" ]; then
  # GNU date first, BSD/macOS date as the fallback.
  SINCE="$(date -u -d "$DAYS days ago" +%Y-%m-%d 2>/dev/null || date -u -v-"$DAYS"d +%Y-%m-%d)"
  leadgen import-form --netlify --since "$SINCE" || echo "website form import failed (see above); continuing"
else
  echo "no NETLIFY_AUTH_TOKEN or NETLIFY_SITE_ID: skipping website form import"
fi
if [ -n "${ANTHROPIC_API_KEY:-}${ANTHROPIC_AUTH_TOKEN:-}" ]; then
  leadgen discover cookie bakery pet_treat
  leadgen websites --min-score 35 --limit 25
fi
leadgen enrich
leadgen score --min-score 35 --top 40
leadgen qualify --min-score 35 --limit 40
if [ -n "${ANTHROPIC_API_KEY:-}${ANTHROPIC_AUTH_TOKEN:-}" ]; then
  leadgen dossier --min-score 50 --limit "$DOSSIERS"
else
  echo "no API key: skipping dossiers (set ANTHROPIC_API_KEY to enable)"
fi
leadgen due
leadgen export "data/pipeline_$(date -u +%Y%m%d).csv"
leadgen weekly-report --days "$DAYS" --email || true
echo "Pipeline done. The export in data/ is the timestamped commission record."
