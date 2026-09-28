#!/usr/bin/env bash
# Weekly pipeline routine. Run on Monday after adding new leads to a CSV.
# Usage: scripts/weekly_routine.sh path/to/new_leads.csv source_name
set -euo pipefail

CSV="${1:?path to CSV required}"
SOURCE="${2:-csv}"

leadgen import "$CSV" --source "$SOURCE"
leadgen enrich
leadgen score --min-score 40 --top 40
leadgen qualify --min-score 40 --limit 40
leadgen report
leadgen export "data/pipeline_$(date -u +%Y%m%d).csv"
echo "Pipeline exported. Email the export to yourself as the timestamped commission record."
