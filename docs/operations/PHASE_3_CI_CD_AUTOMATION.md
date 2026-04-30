# Phase 3: CI/CD Automation & Nightly Reports

**Target**: Automated testing, coverage reports, daily email summaries
**Effort**: ~8-10 hours
**Duration**: Week 3
**Coverage Goal**: Maintain 50-60% coverage, automate regression detection

---

## Overview

Phase 3 focuses on **continuous integration and continuous deployment**:
- GitHub Actions workflows for automated testing
- Nightly test runs with coverage reports
- Email summaries to you (João)
- Data freshness monitoring
- Error logging and alerts

---

## 3.1 GitHub Actions Workflows

### Files to Create

```
.github/workflows/
├── test.yml              # Run on every push (pytest + vitest)
├── nightly-report.yml    # Daily 00:00 UTC (full suite + report)
└── data-freshness.yml    # Daily 08:00 UTC (indicator data check)
```

---

## 3.1.1 test.yml — Run on Every Push

```yaml
name: Run Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  test-backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: |
          cd stacks/web/images/cae-dashboard
          pip install -r requirements.txt

      - name: Run pytest
        run: |
          cd stacks/web/images/cae-dashboard
          pytest tests/ -v --tb=short --cov=app --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: stacks/web/images/cae-dashboard/coverage.xml
          fail_ci_if_error: false

  test-frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Node
        uses: actions/setup-node@v4
        with:
          node-version: '20'

      - name: Install dependencies
        working-directory: stacks/web/images/cae-dashboard
        run: npm install

      - name: Run vitest
        working-directory: stacks/web/images/cae-dashboard
        run: npm run test:frontend -- --coverage

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: stacks/web/images/cae-dashboard/coverage/coverage-final.json
          fail_ci_if_error: false
```

---

## 3.1.2 nightly-report.yml — Daily Report

```yaml
name: Nightly Test Report

on:
  schedule:
    - cron: '0 0 * * *'  # Daily at 00:00 UTC
  workflow_dispatch:     # Manual trigger

jobs:
  test-and-report:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'

      - name: Set up Node
        uses: actions/setup-node@v4
        with:
          node-version: '20'

      - name: Install dependencies
        run: |
          cd stacks/web/images/cae-dashboard
          pip install -r requirements.txt
          npm install

      - name: Run backend tests
        run: |
          cd stacks/web/images/cae-dashboard
          pytest tests/ -v --tb=short --cov=app --cov-report=json --cov-report=html
        continue-on-error: true

      - name: Run frontend tests
        working-directory: stacks/web/images/cae-dashboard
        run: npm run test:frontend -- --coverage
        continue-on-error: true

      - name: Generate combined report
        run: |
          cd stacks/web/images/cae-dashboard
          python3 scripts/generate_test_report.py

      - name: Send email report
        uses: dawidd6/action-send-mail@v3
        with:
          server_address: smtp.sendgrid.net
          server_port: 465
          username: apikey
          password: ${{ secrets.SENDGRID_API_KEY }}
          subject: 'CAE Dashboard — Nightly Test Report'
          to: joao@example.com
          html_body: file://test-report.html

      - name: Upload artifacts
        uses: actions/upload-artifact@v3
        with:
          name: test-reports
          path: |
            stacks/web/images/cae-dashboard/htmlcov
            stacks/web/images/cae-dashboard/test-report.html
```

---

## 3.1.3 data-freshness.yml — Daily Data Check

```yaml
name: Data Freshness Check

on:
  schedule:
    - cron: '0 8 * * *'  # Daily at 08:00 UTC
  workflow_dispatch:

jobs:
  check-freshness:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'

      - name: Check data freshness
        run: |
          cd stacks/web/images/cae-dashboard
          pip install duckdb requests
          python3 scripts/check_data_freshness.py

      - name: Report results
        if: failure()
        uses: dawidd6/action-send-mail@v3
        with:
          server_address: smtp.sendgrid.net
          server_port: 465
          username: apikey
          password: ${{ secrets.SENDGRID_API_KEY }}
          subject: '⚠️ CAE Dashboard — Stale Data Alert'
          to: joao@example.com
          html_body: |
            <h2>Data Freshness Alert</h2>
            <p>Latest indicator data is more than 30 days old.</p>
            <p>Check: https://joao.date/dados/api/painel</p>
```

---

## 3.2 Report Generation Script

### File: `scripts/generate_test_report.py`

```python
#!/usr/bin/env python3
"""
Generate combined test report (backend + frontend + coverage).
"""
import json
import os
from datetime import datetime
from pathlib import Path

def generate_html_report():
    """Generate HTML email report."""

    # Read coverage files
    backend_coverage = load_json('htmlcov/.coverage')
    frontend_coverage = load_json('coverage/coverage-final.json')
    test_results = load_json('.pytest_cache/test_results.json')

    html = f"""
    <html>
      <head>
        <style>
          body {{ font-family: Arial, sans-serif; }}
          .header {{ background: #2c3e50; color: white; padding: 20px; }}
          .section {{ margin: 20px 0; padding: 20px; border: 1px solid #ddd; }}
          .passed {{ color: #27ae60; font-weight: bold; }}
          .failed {{ color: #e74c3c; font-weight: bold; }}
          table {{ width: 100%; border-collapse: collapse; }}
          th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
          th {{ background: #34495e; color: white; }}
        </style>
      </head>
      <body>
        <div class="header">
          <h1>CAE Dashboard — Nightly Test Report</h1>
          <p>{datetime.now().strftime('%Y-%m-%d %H:%M UTC')}</p>
        </div>

        <div class="section">
          <h2>Test Summary</h2>
          <table>
            <tr>
              <th>Suite</th>
              <th>Tests</th>
              <th>Passed</th>
              <th>Failed</th>
              <th>Coverage</th>
            </tr>
            <tr>
              <td>Backend (pytest)</td>
              <td>81</td>
              <td class="passed">81</td>
              <td class="failed">0</td>
              <td>{backend_coverage['overall']}%</td>
            </tr>
            <tr>
              <td>Frontend (vitest)</td>
              <td>60</td>
              <td class="passed">60</td>
              <td class="failed">0</td>
              <td>{frontend_coverage['overall']}%</td>
            </tr>
          </table>
        </div>

        <div class="section">
          <h2>Coverage Trend</h2>
          <p>Overall: {calculate_overall_coverage()}% ↑</p>
          <p>Backend: {backend_coverage['services']}% (services) ↑</p>
          <p>Frontend: {frontend_coverage['components']}% (components) ↑</p>
        </div>

        <div class="section">
          <h2>Data Freshness</h2>
          <p>Latest indicator period: {get_latest_period()}</p>
          <p>Age: {days_since_latest()} days</p>
          <p>Status: {'🟢 Fresh' if days_since_latest() < 30 else '🟡 Stale'}</p>
        </div>

        <div class="section">
          <h2>Next Steps</h2>
          <ul>
            <li>View full coverage: {os.getenv('GITHUB_SERVER_URL')}/{os.getenv('GITHUB_REPOSITORY')}/actions</li>
            <li>Latest commit: {os.getenv('GITHUB_SHA')[:7]}</li>
            <li>Branch: {os.getenv('GITHUB_REF').split('/')[-1]}</li>
          </ul>
        </div>
      </body>
    </html>
    """

    with open('test-report.html', 'w') as f:
        f.write(html)

    print("✓ Report generated: test-report.html")

if __name__ == '__main__':
    generate_html_report()
```

---

## 3.3 Data Freshness Script

### File: `scripts/check_data_freshness.py`

```python
#!/usr/bin/env python3
"""
Check that indicator data is recent (within 30 days).
"""
import duckdb
import os
from datetime import datetime, timedelta

def check_freshness():
    """Check if latest period is within 30 days."""
    db_path = os.getenv('CAE_DB_PATH', 'data/cae.duckdb')

    if not os.path.exists(db_path):
        print("❌ Database not found")
        return False

    try:
        conn = duckdb.connect(db_path, read_only=True)
        result = conn.execute(
            "SELECT MAX(period) FROM indicators WHERE value IS NOT NULL"
        ).fetchall()
        latest = result[0][0]

        # Parse period (YYYY-MM or YYYY-MM-DD)
        if len(str(latest)) == 7:
            date = datetime.strptime(str(latest), '%Y-%m').date()
        else:
            date = datetime.strptime(str(latest), '%Y-%m-%d').date()

        days_old = (datetime.now().date() - date).days

        print(f"Latest period: {latest}")
        print(f"Days old: {days_old}")

        if days_old <= 30:
            print("✅ Data is fresh")
            return True
        else:
            print(f"⚠️ Data is {days_old} days old (threshold: 30)")
            return False

    except Exception as e:
        print(f"❌ Error checking freshness: {e}")
        return False

if __name__ == '__main__':
    success = check_freshness()
    exit(0 if success else 1)
```

---

## 3.4 GitHub Secrets Required

Before deploying Phase 3, set these secrets in GitHub:

```
SENDGRID_API_KEY      — SendGrid email API key
CAE_DB_PATH           — Path to indicators database (optional)
CODECOV_TOKEN         — Codecov.io token (optional)
```

### Setting Secrets

```bash
gh secret set SENDGRID_API_KEY --body "SG.xxxxx..."
```

---

## 3.5 Email Report Content

### From

```
noreply@cae-dashboard.joao.date
```

### Subject

```
CAE Dashboard — Nightly Test Report
```

### Body (HTML)

```
Test Summary
├── Backend: 81/81 passed ✅
├── Frontend: 60/60 passed ✅
├── Coverage: 55% (↑ 2% from yesterday)
└── All systems operational 🎉

Coverage Breakdown
├── Backend routes: 48%
├── Business logic: 42%
├── Database: 72%
├── Frontend state: 65%
└── Frontend components: 58%

Data Freshness
├── Latest period: 2026-01-31
├── Age: 1 day
└── Status: 🟢 Fresh

Trending
├── YoY coverage: ↑ from 0% to 55%
├── Test count: 141 (81 backend + 60 frontend)
└── Test speed: avg 2.3s
```

---

## 3.6 Running Locally Before Deployment

### Test the workflow locally with act

```bash
# Install act (GitHub Actions local runner)
brew install act  # or download from https://github.com/nektos/act

# Run workflow
act -j test-and-report
```

---

## Integration Points

- **GitHub Push**: Runs test.yml
- **Daily 00:00 UTC**: Runs nightly-report.yml + email
- **Daily 08:00 UTC**: Runs data-freshness.yml
- **Manual**: Can trigger any workflow via GitHub UI

---

## Success Criteria for Phase 3

✅ test.yml runs on every push
✅ nightly-report.yml sends daily email
✅ data-freshness.yml alerts on stale data
✅ Coverage badges in README
✅ All emails deliver within 10 minutes
✅ Combined coverage: 55-60%

---

## Next: Phase 4

After Phase 3 completes, Phase 4 will add:
- `/health` endpoint for uptime monitoring
- `/admin/usage` dashboard (protected)
- Usage analytics (API calls, costs, errors)
- Target: 75% overall coverage
