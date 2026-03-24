# VC Pulse — Threeglau VC Trend Tracker

A lean dashboard that aggregates venture capital funding trends, top deals, and sector heatmaps from public data sources.

## Stack

- **Backend**: FastAPI + SQLite + httpx
- **Frontend**: Vanilla HTML/JS + Chart.js
- **Ingestion**: RSS feeds (TechCrunch, PitchBook, a16z, First Round Review), web scraping (CB Insights), APIs (Hacker News Algolia, GitHub)

## Quick Start

```bash
cd /home/ubuntu/vcpulse
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Initialize database
python -c "from db import init_db; init_db()"

# Run first ingestion
python ingest.py

# Start server
uvicorn app:app --host 127.0.0.1 --port 8003
```

## Deployment

### systemd Service

```bash
sudo cp deploy/vcpulse.service /etc/systemd/system/
sudo cp deploy/vcpulse-ingest.service /etc/systemd/system/
sudo cp deploy/vcpulse-ingest.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now vcpulse.service
sudo systemctl enable --now vcpulse-ingest.timer
```

### nginx

Add `deploy/nginx-vcpulse.conf` to your nginx sites configuration.

## API Endpoints

| Endpoint | Description |
|---|---|
| `GET /api/health` | Uptime check |
| `GET /api/stats?days=30` | Key metrics |
| `GET /api/deals?days=30&sector=ai` | Recent deals |
| `GET /api/deals/top?days=30&limit=10` | Largest rounds |
| `GET /api/sectors/heatmap?days=30` | Sector distribution |
| `GET /api/articles?days=14&source=a16z` | VC thesis articles |
| `GET /api/trends/weekly` | Week-over-week sector trends |

## Data Sources

TechCrunch Venture RSS, PitchBook News RSS, CB Insights Research, a16z Blog, First Round Review, Hacker News (Algolia), GitHub Trending

---

Powered by **Threeglau s.r.o.**
