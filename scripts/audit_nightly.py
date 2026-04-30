#!/usr/bin/env python3
"""
audit_nightly.py — Nightly data quality audit for Prumo.

Runs all quality checks and appends results to /data/audit-log.jsonl.
Sends Telegram alert on critical errors.

Usage:
  python scripts/audit_nightly.py              # run audit
  python scripts/audit_nightly.py --history    # print last 7 audit summaries

Scheduled via cron in entrypoint.sh: 03:00 daily.
"""
import json
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

# Add parent dir to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

AUDIT_LOG = os.environ.get("AUDIT_LOG_PATH", "/data/audit-log.jsonl")
RETENTION_DAYS = 90


def run_audit():
    """Run all quality checks and return the report."""
    # Must set DB path before importing app modules
    os.environ.setdefault("CAE_DB_PATH", "/data/cae-data.duckdb")

    from app.services.quality import run_quality_checks
    return run_quality_checks()


def append_log(report: dict):
    """Append audit result to JSONL log with retention."""
    entry = {
        "ts": datetime.utcnow().isoformat() + "Z",
        "summary": report["summary"],
        "errors": [i for checks in report["checks"].values() for i in checks if i["severity"] == "error"],
    }
    with open(AUDIT_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    # Trim old entries (keep last RETENTION_DAYS)
    _trim_log()


def _trim_log():
    """Remove entries older than RETENTION_DAYS."""
    if not os.path.exists(AUDIT_LOG):
        return
    cutoff = (datetime.utcnow() - timedelta(days=RETENTION_DAYS)).isoformat()
    lines = Path(AUDIT_LOG).read_text(encoding="utf-8").strip().split("\n")
    kept = [l for l in lines if l.strip() and json.loads(l).get("ts", "") >= cutoff]
    Path(AUDIT_LOG).write_text("\n".join(kept) + "\n" if kept else "", encoding="utf-8")


def send_telegram_alert(report: dict):
    """Send Telegram alert if there are critical errors."""
    errors = report["summary"]["errors"]
    if errors == 0:
        return

    # Read bot token from environment (injected by dc-jarbas-up via SOPS).
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")

    if not token or not chat_id:
        # Try reading from openclaw.json
        try:
            oc_path = "/data/openclaw.json"
            if os.path.exists(oc_path):
                oc = json.loads(Path(oc_path).read_text())
                token = token or oc.get("channels", {}).get("telegram", {}).get("botToken", "")
                chat_id = chat_id or oc.get("channels", {}).get("telegram", {}).get("chatId", "")
        except Exception:
            pass

    if not token or not chat_id:
        print("[audit] No Telegram credentials — skipping alert", flush=True)
        return

    warnings = report["summary"]["warnings"]
    msg = (
        f"⚠️ *Prumo Data Audit*\n"
        f"Errors: {errors} | Warnings: {warnings}\n"
    )
    # Add first 5 error details
    error_items = [i for checks in report["checks"].values() for i in checks if i["severity"] == "error"]
    for item in error_items[:5]:
        msg += f"• `{item['source']}/{item['indicator']}`: {item['msg']}\n"
    if len(error_items) > 5:
        msg += f"• ...and {len(error_items) - 5} more\n"

    try:
        import urllib.request
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        data = json.dumps({"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"}).encode()
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=10)
        print(f"[audit] Telegram alert sent ({errors} errors)", flush=True)
    except Exception as e:
        print(f"[audit] Telegram alert failed: {e}", flush=True)


def show_history():
    """Print last 7 audit summaries."""
    if not os.path.exists(AUDIT_LOG):
        print("No audit log found.")
        return
    lines = Path(AUDIT_LOG).read_text(encoding="utf-8").strip().split("\n")
    for line in lines[-7:]:
        if not line.strip():
            continue
        entry = json.loads(line)
        s = entry["summary"]
        print(f"  {entry['ts']}  OK={s['ok']}  errors={s['errors']}  warnings={s['warnings']}")


if __name__ == "__main__":
    if "--history" in sys.argv:
        show_history()
        sys.exit(0)

    print(f"[audit] Starting nightly audit at {datetime.utcnow().isoformat()}Z", flush=True)
    t0 = time.time()
    report = run_audit()
    elapsed = time.time() - t0

    s = report["summary"]
    print(
        f"[audit] Done in {elapsed:.1f}s — "
        f"OK={s['ok']}  errors={s['errors']}  warnings={s['warnings']}  info={s['info']}",
        flush=True,
    )

    append_log(report)
    send_telegram_alert(report)
