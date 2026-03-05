# Phase 4: Production Monitoring & Usage Dashboard

**Target**: Health checks, usage analytics, admin dashboard
**Effort**: ~6-8 hours
**Duration**: Week 4
**Coverage Goal**: Maintain 60-75% overall coverage

---

## Overview

Phase 4 focuses on **production monitoring and observability**:
- `/health` endpoint for system health checks
- `/admin/usage` dashboard for analytics (protected)
- Usage tracking (API calls, costs, errors)
- Performance monitoring
- Alert integration

---

## 4.1 Health Check Endpoint

### API: `GET /health`

```json
{
  "status": "ok",
  "timestamp": "2026-03-03T16:30:00Z",
  "version": "7.2",
  "services": {
    "api": { "status": "ok", "response_time_ms": 5 },
    "database": { "status": "ok", "indicators": 422, "latest_period": "2026-01-31" },
    "anthropic": { "status": "ok", "last_call": "2026-03-03T16:29:00Z" },
    "cache": { "status": "ok", "items": 47 }
  },
  "data_freshness": {
    "age_days": 1,
    "threshold_days": 30,
    "status": "green"  # green, yellow, red
  }
}
```

### Implementation: `app/routes/health.py`

```python
from fastapi import APIRouter, Response
from datetime import datetime, timedelta
import duckdb

router = APIRouter()

@router.get("/health")
def health_check():
    """System health check endpoint."""

    # Check API response time
    start = time.time()
    api_health = {"status": "ok", "response_time_ms": 0}
    api_health["response_time_ms"] = round((time.time() - start) * 1000)

    # Check database
    db_health = {"status": "error", "error": None, "indicators": 0, "latest_period": None}
    try:
        conn = duckdb.connect(CAE_DB_PATH, read_only=True)
        count = conn.execute("SELECT COUNT(*) FROM indicators").fetchall()[0][0]
        latest = conn.execute("SELECT MAX(period) FROM indicators").fetchall()[0][0]
        db_health = {"status": "ok", "indicators": count, "latest_period": str(latest)}
        conn.close()
    except Exception as e:
        db_health["error"] = str(e)

    # Check Anthropic API
    anthropic_health = {"status": "ok", "last_call": None}
    try:
        # Check if API key is valid and recent
        # This is a lightweight check, not an actual API call
        last_call = load_anthropic_last_call()
        if last_call:
            age = (datetime.now() - last_call).seconds / 60
            if age > 60:  # More than 1 hour old
                anthropic_health["status"] = "warning"
            anthropic_health["last_call"] = last_call.isoformat()
    except Exception as e:
        anthropic_health["status"] = "error"

    # Check cache
    cache_health = {"status": "ok", "items": len(cache.keys())}

    # Data freshness
    freshness_status = "green"
    age_days = 0
    if db_health["status"] == "ok" and db_health["latest_period"]:
        try:
            latest_date = datetime.strptime(str(db_health["latest_period"]), "%Y-%m").date()
            age_days = (datetime.now().date() - latest_date).days
            if age_days > 30:
                freshness_status = "red"
            elif age_days > 14:
                freshness_status = "yellow"
        except:
            pass

    # Overall status
    all_ok = all(s["status"] == "ok" for s in [
        api_health, db_health, anthropic_health, cache_health
    ])
    overall_status = "ok" if all_ok else "warning"

    return {
        "status": overall_status,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "version": "7.2",
        "services": {
            "api": api_health,
            "database": db_health,
            "anthropic": anthropic_health,
            "cache": cache_health
        },
        "data_freshness": {
            "age_days": age_days,
            "threshold_days": 30,
            "status": freshness_status
        }
    }
```

---

## 4.2 Admin Usage Dashboard

### API: `GET /admin/usage` (Protected)

Requires authentication (Authelia/OAuth)

```json
{
  "period": "2026-03-03",
  "api_calls": {
    "total": 1247,
    "by_endpoint": {
      "/api/painel": 320,
      "/api/painel-headline": 180,
      "/api/painel-analysis": 150,
      "/api/explore": 400,
      "/api/compare": 197
    },
    "by_language": {
      "pt": 800,
      "en": 200,
      "fr": 150,
      "es": 80,
      "cv": 17
    }
  },
  "costs": {
    "anthropic_usd": 2.34,
    "by_lens": {
      "pcp": 0.28,
      "cae": 0.26,
      "be": 0.25,
      "ps": 0.24,
      "ad": 0.23,
      "neutro": 0.22
    }
  },
  "errors": {
    "total": 3,
    "by_endpoint": {
      "/api/painel": 1,
      "/api/explore": 2
    },
    "error_rate_percent": 0.24
  },
  "performance": {
    "avg_response_time_ms": 120,
    "p95_response_time_ms": 450,
    "p99_response_time_ms": 1200,
    "endpoints": [
      { "path": "/api/painel", "avg_ms": 85, "p95_ms": 200 },
      { "path": "/api/painel-headline", "avg_ms": 2300, "p95_ms": 4500 },
      { "path": "/api/explore", "avg_ms": 150, "p95_ms": 600 }
    ]
  },
  "data_freshness": {
    "latest_period": "2026-01-31",
    "age_days": 1,
    "indicators_updated": 245,
    "sources": {
      "INE": { "latest": "2026-01-31", "age_days": 1 },
      "Eurostat": { "latest": "2025-12-15", "age_days": 48 },
      "DGEG": { "latest": "2026-03-03", "age_days": 0 },
      "REN": { "latest": "2026-02-28", "age_days": 3 }
    }
  }
}
```

### Implementation: `app/routes/admin.py`

```python
from fastapi import APIRouter, Depends, HTTPException
from app.analytics import get_analytics_db

router = APIRouter(prefix="/admin")

@router.get("/usage")
def get_usage_stats(user=Depends(get_current_user)):
    """Get usage statistics and costs (protected)."""

    if not user or not user.is_admin:
        raise HTTPException(status_code=403, detail="Unauthorized")

    # Get today's data
    today = datetime.now().date().isoformat()

    db = get_analytics_db()

    # API calls by endpoint
    calls_by_endpoint = db.execute("""
        SELECT path, COUNT(*) as count
        FROM api_calls
        WHERE DATE(timestamp) = ?
        GROUP BY path
        ORDER BY count DESC
    """, [today]).fetchall()

    # Calls by language
    calls_by_lang = db.execute("""
        SELECT language, COUNT(*) as count
        FROM api_calls
        WHERE DATE(timestamp) = ? AND language IS NOT NULL
        GROUP BY language
        ORDER BY count DESC
    """, [today]).fetchall()

    # Anthropic costs (from usage logs)
    costs = db.execute("""
        SELECT
            SUM(input_tokens * 0.003 + output_tokens * 0.009) as total_usd
        FROM anthropic_calls
        WHERE DATE(timestamp) = ?
    """, [today]).fetchall()[0][0] or 0

    # Errors
    errors = db.execute("""
        SELECT path, COUNT(*) as count
        FROM api_calls
        WHERE DATE(timestamp) = ? AND status >= 400
        GROUP BY path
    """, [today]).fetchall()

    total_calls = sum(count for _, count in calls_by_endpoint)

    return {
        "period": today,
        "api_calls": {
            "total": total_calls,
            "by_endpoint": {path: count for path, count in calls_by_endpoint},
            "by_language": {lang: count for lang, count in calls_by_lang}
        },
        "costs": {
            "anthropic_usd": round(costs, 2)
        },
        "errors": {
            "total": sum(count for _, count in errors),
            "by_endpoint": {path: count for path, count in errors},
            "error_rate_percent": round(
                (sum(count for _, count in errors) / total_calls * 100) if total_calls > 0 else 0,
                2
            )
        }
    }
```

---

## 4.3 Analytics Database Schema

### Tables

```sql
-- API call logs
CREATE TABLE api_calls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    path TEXT NOT NULL,
    method TEXT NOT NULL,
    status INTEGER NOT NULL,
    response_time_ms INTEGER NOT NULL,
    language TEXT,
    lens TEXT,
    user_id TEXT,
    ip_address TEXT
);

-- Anthropic API usage
CREATE TABLE anthropic_calls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    endpoint TEXT NOT NULL,
    model TEXT NOT NULL,
    lens TEXT NOT NULL,
    input_tokens INTEGER NOT NULL,
    output_tokens INTEGER NOT NULL,
    cost_usd FLOAT NOT NULL
);

-- Indicator data updates
CREATE TABLE indicator_updates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    source TEXT NOT NULL,
    indicators_updated INTEGER NOT NULL,
    latest_period TEXT NOT NULL,
    status TEXT NOT NULL
);
```

### Indexing

```sql
CREATE INDEX idx_api_calls_timestamp ON api_calls(timestamp);
CREATE INDEX idx_api_calls_path ON api_calls(path);
CREATE INDEX idx_anthropic_timestamp ON anthropic_calls(timestamp);
CREATE INDEX idx_anthropic_lens ON anthropic_calls(lens);
```

---

## 4.4 Monitoring Integrations

### Uptime Monitoring

Use Uptime Kuma (already deployed) to monitor:

```
GET /health → checks every 30 seconds
Failure alert if status != "ok" for >5 minutes
```

### Error Alerts

Integrate with error tracking:

```python
# Sentry integration (optional)
import sentry_sdk

sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    traces_sample_rate=0.1,
    environment="production"
)
```

### Slack Notifications

```python
# Send alerts to Slack on critical errors
def send_slack_alert(message):
    webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    requests.post(webhook_url, json={"text": message})
```

---

## 4.5 Dashboard UI

### HTML Template: `admin/usage.html`

```html
<!DOCTYPE html>
<html>
<head>
  <title>CAE Dashboard — Admin Usage</title>
  <style>
    body { font-family: Arial; margin: 20px; }
    .card { border: 1px solid #ddd; padding: 20px; margin: 10px 0; }
    .metric { font-size: 28px; font-weight: bold; }
    .label { font-size: 12px; color: #666; }
    .chart { height: 300px; margin: 20px 0; }
  </style>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body>
  <h1>CAE Dashboard — Usage Dashboard</h1>

  <div class="card">
    <div class="metric" id="total-calls">-</div>
    <div class="label">API Calls (Last 24h)</div>
  </div>

  <div class="card">
    <div class="metric" id="total-cost">-</div>
    <div class="label">Anthropic Cost (USD)</div>
  </div>

  <div class="card">
    <div id="chart-endpoints" class="chart"></div>
  </div>

  <div class="card">
    <div id="chart-languages" class="chart"></div>
  </div>

  <script>
    fetch('/admin/usage')
      .then(r => r.json())
      .then(data => {
        document.getElementById('total-calls').textContent = data.api_calls.total;
        document.getElementById('total-cost').textContent = '$' + data.costs.anthropic_usd;

        // Chart: API calls by endpoint
        new Chart(document.getElementById('chart-endpoints'), {
          type: 'bar',
          data: {
            labels: Object.keys(data.api_calls.by_endpoint),
            datasets: [{
              label: 'API Calls',
              data: Object.values(data.api_calls.by_endpoint)
            }]
          }
        });

        // Chart: API calls by language
        new Chart(document.getElementById('chart-languages'), {
          type: 'pie',
          data: {
            labels: Object.keys(data.api_calls.by_language),
            datasets: [{
              data: Object.values(data.api_calls.by_language)
            }]
          }
        });
      });
  </script>
</body>
</html>
```

---

## 4.6 Success Criteria for Phase 4

✅ `/health` endpoint returns system status
✅ `/admin/usage` dashboard shows analytics
✅ Database tracks API calls and costs
✅ Error alerts configured
✅ Uptime monitoring active
✅ Performance metrics dashboard
✅ Combined coverage: 70-75%

---

## Final Coverage Summary

After all 4 phases:

| Component | Phase 1 | Phase 2 | Phase 3 | Phase 4 | Target |
|-----------|---------|---------|---------|---------|--------|
| Backend routes | 45% | 45% | 48% | 50% | 90% |
| Business logic | 40% | 40% | 42% | 45% | 85% |
| Database | 70% | 70% | 72% | 75% | 95% |
| Frontend state | 0% | 65% | 68% | 70% | 70% |
| Frontend components | 0% | 58% | 60% | 62% | 60% |
| **Overall** | **20%** | **43%** | **50%** | **60-75%** | **75%** |

---

## Post-Phase 4

- Monitor daily with Uptime Kuma
- Track costs via `/admin/usage`
- Automate nightly reports
- Gather team feedback
- Plan Phase 5+ features:
  - Advanced analytics (usage trends, cost forecasting)
  - Custom dashboards
  - Alerts and SLO management
  - Integration with other services
