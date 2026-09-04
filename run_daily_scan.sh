#!/bin/bash
# Daily Buy-on-Dip Scanner Runner Script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

echo "[$(date)] Starting Automated Buy-on-Dip Stock Scan..."
/opt/homebrew/bin/uv run python buy_on_dip_notifier.py >> daily_scan.log 2>&1
echo "[$(date)] Scan completed."
