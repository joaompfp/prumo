#!/usr/bin/env python3
"""Watch the audit process and send Telegram notification when done."""
import json
import os
import time
import urllib.request
import urllib.parse

PID = 871291
RESULTS_FILE = "/tmp/prumo-audit-results.json"
LOG_FILE = "/tmp/prumo-audit.log"
TOKEN = json.load(open("/home/joao/docker/stacks/ai/appdata/openclaw/config/openclaw.json"))["channels"]["telegram"]["botToken"]
CHAT_ID = "993089095"


def send_telegram(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = urllib.parse.urlencode({
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "Markdown",
    }).encode()
    try:
        with urllib.request.urlopen(url, data) as r:
            return json.load(r)["ok"]
    except Exception as e:
        print(f"Telegram error: {e}")
        return False


def is_running(pid):
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def get_progress():
    """Read last few lines of log to show progress."""
    try:
        with open(LOG_FILE) as f:
            lines = f.readlines()
        # Find last progress line
        for line in reversed(lines):
            if "Progress:" in line or "PHASE" in line or "COMPLETE" in line:
                return line.strip()
        return lines[-1].strip() if lines else "No log yet"
    except Exception:
        return "Log not available"


# Send progress updates every 30 minutes
last_update = time.time()
UPDATE_INTERVAL = 1800  # 30 min

print(f"Watching PID {PID}...")

while is_running(PID):
    time.sleep(30)
    now = time.time()
    if now - last_update >= UPDATE_INTERVAL:
        progress = get_progress()
        send_telegram(f"📊 *Prumo Audit* — em curso\n`{progress}`")
        last_update = now

# Process finished — send results
time.sleep(2)  # Let file writes flush

try:
    with open(RESULTS_FILE) as f:
        results = json.load(f)

    summary = results.get("summary", {})
    ind = summary.get("individual", {})
    combos = summary.get("combos", {})
    failures = summary.get("failures", [])

    msg = (
        "✅ *Prumo Audit — CONCLUÍDO*\n\n"
        f"*Indicadores individuais:*\n"
        f"  Total: {ind.get('total', '?')}\n"
        f"  ✅ OK: {ind.get('ok', '?')}\n"
        f"  ⚠️ Chart only (sem IA): {ind.get('chart_only', '?')}\n"
        f"  ❌ Falha: {ind.get('fail', '?')}\n"
        f"  💥 Erro: {ind.get('error', '?')}\n\n"
        f"*Combinações:*\n"
        f"  Total: {combos.get('total', '?')}\n"
        f"  ✅ OK: {combos.get('ok', '?')}\n"
        f"  ❌ Falha: {combos.get('fail', '?')}\n"
    )

    if failures:
        msg += f"\n*Falhas ({len(failures)}):*\n"
        for f_item in failures[:15]:  # Telegram msg limit
            msg += f"  • `{f_item['key']}`: {f_item['status']}\n"
        if len(failures) > 15:
            msg += f"  ... e mais {len(failures) - 15}\n"

    msg += f"\n📁 Resultados: `{RESULTS_FILE}`\n📸 Screenshots: `/tmp/prumo-audit-screenshots/`"

    send_telegram(msg)
    print("Final notification sent!")

except Exception as e:
    send_telegram(f"⚠️ *Prumo Audit* — processo terminou mas erro ao ler resultados: `{e}`")
    print(f"Error reading results: {e}")
