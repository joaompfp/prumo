#!/bin/sh
set -e

DATA_DIR="/data"
SEED_DIR="/app/seed_data"

# Ensure data dir exists
mkdir -p "$DATA_DIR"

# Initialize site.json if missing
if [ ! -f "$DATA_DIR/site.json" ]; then
    echo "Initializing default site.json..."
    cp "$SEED_DIR/site.json" "$DATA_DIR/site.json"
fi

# Initialize ideologies dir if missing
if [ ! -d "$DATA_DIR/ideologies" ]; then
    echo "Initializing default ideologies..."
    cp -r "$SEED_DIR/ideologies" "$DATA_DIR/ideologies"
fi

# Initialize duckdb placeholder if no db exists
if [ ! -f "$DATA_DIR/cae-data.duckdb" ] && [ ! -f "$DATA_DIR/cae-data.db" ]; then
    echo "No DuckDB found at $DATA_DIR/cae-data.duckdb."
    echo "Copying placeholder instructions..."
    cp "$SEED_DIR/README-DB.txt" "$DATA_DIR/README-DB.txt"
fi

# Schedule nightly collect + audit at 03:00 (if crond available)
if command -v crond >/dev/null 2>&1 || command -v cron >/dev/null 2>&1; then
    echo "0 3 * * * cd /app && python scripts/collect_scheduled.py >> /data/collect-cron.log 2>&1 && python scripts/audit_nightly.py >> /data/audit-cron.log 2>&1" | crontab -
    crond 2>/dev/null || cron 2>/dev/null || true
    echo "Nightly collect + audit scheduled at 03:00"
fi

# Start the application
exec "$@"
