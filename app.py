"""FastAPI application for VC Pulse dashboard."""

import statistics
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from db import init_db, get_db
from models import (
    Deal, Article, SectorHeatmapEntry, WeeklyTrend,
    HealthResponse, StatsResponse,
)

app = FastAPI(title="VC Pulse", version="1.0.0")

STATIC_DIR = Path(__file__).parent / "static"


@app.on_event("startup")
def startup():
    init_db()


# --- API Endpoints ---

@app.get("/api/health", response_model=HealthResponse)
def health():
    with get_db() as conn:
        deals_count = conn.execute("SELECT COUNT(*) FROM deals").fetchone()[0]
        articles_count = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
    return HealthResponse(
        status="ok",
        timestamp=datetime.utcnow(),
        deals_count=deals_count,
        articles_count=articles_count,
    )


@app.get("/api/stats", response_model=StatsResponse)
def get_stats(days: int = Query(30, ge=1, le=365)):
    with get_db() as conn:
        total = conn.execute(
            "SELECT COUNT(*) FROM deals WHERE published_at >= datetime('now', ?)",
            (f"-{days} days",),
        ).fetchone()[0]

        amounts = conn.execute(
            "SELECT amount_usd FROM deals WHERE published_at >= datetime('now', ?) AND amount_usd IS NOT NULL AND amount_usd > 0",
            (f"-{days} days",),
        ).fetchall()
        median = None
        if amounts:
            sorted_amounts = sorted(r[0] for r in amounts)
            median = statistics.median(sorted_amounts)

        hottest = conn.execute(
            """SELECT sector, COUNT(*) as cnt FROM deals
               WHERE published_at >= datetime('now', ?) AND sector IS NOT NULL
               GROUP BY sector ORDER BY cnt DESC LIMIT 1""",
            (f"-{days} days",),
        ).fetchone()

        largest = conn.execute(
            """SELECT amount_usd, company FROM deals
               WHERE published_at >= datetime('now', ?) AND amount_usd IS NOT NULL
               ORDER BY amount_usd DESC LIMIT 1""",
            (f"-{days} days",),
        ).fetchone()

    return StatsResponse(
        total_deals=total,
        median_round_size=median,
        hottest_sector=hottest[0] if hottest else None,
        hottest_sector_count=hottest[1] if hottest else 0,
        largest_round=largest[0] if largest else None,
        largest_round_company=largest[1] if largest else None,
    )


@app.get("/api/deals")
def get_deals(
    days: int = Query(30, ge=1, le=365),
    sector: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    with get_db() as conn:
        query = "SELECT * FROM deals WHERE published_at >= datetime('now', ?)"
        params: list = [f"-{days} days"]

        if sector:
            query += " AND LOWER(sector) = LOWER(?)"
            params.append(sector)

        query += " ORDER BY published_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        rows = conn.execute(query, params).fetchall()

    return [dict(r) for r in rows]


@app.get("/api/deals/top")
def get_top_deals(
    days: int = Query(30, ge=1, le=365),
    limit: int = Query(10, ge=1, le=50),
):
    with get_db() as conn:
        rows = conn.execute(
            """SELECT * FROM deals
               WHERE published_at >= datetime('now', ?) AND amount_usd IS NOT NULL
               ORDER BY amount_usd DESC LIMIT ?""",
            (f"-{days} days", limit),
        ).fetchall()

    return [dict(r) for r in rows]


@app.get("/api/sectors/heatmap")
def get_sector_heatmap(days: int = Query(30, ge=1, le=365)):
    with get_db() as conn:
        rows = conn.execute(
            """SELECT sector, COUNT(*) as deal_count,
                      AVG(amount_usd) as avg_round_size,
                      SUM(amount_usd) as total_volume
               FROM deals
               WHERE published_at >= datetime('now', ?) AND sector IS NOT NULL
               GROUP BY sector
               ORDER BY deal_count DESC""",
            (f"-{days} days",),
        ).fetchall()

    return [
        SectorHeatmapEntry(
            sector=r["sector"],
            deal_count=r["deal_count"],
            avg_round_size=r["avg_round_size"],
            total_volume=r["total_volume"],
        )
        for r in rows
    ]


@app.get("/api/articles")
def get_articles(
    days: int = Query(14, ge=1, le=365),
    source: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
):
    with get_db() as conn:
        query = "SELECT * FROM articles WHERE published_at >= datetime('now', ?)"
        params: list = [f"-{days} days"]

        if source:
            query += " AND LOWER(source) = LOWER(?)"
            params.append(source)

        query += " ORDER BY published_at DESC LIMIT ?"
        params.append(limit)

        rows = conn.execute(query, params).fetchall()

    return [dict(r) for r in rows]


@app.get("/api/trends/weekly")
def get_weekly_trends():
    with get_db() as conn:
        rows = conn.execute(
            """SELECT sector, week_start, mention_count, avg_round_size
               FROM sector_signals
               WHERE week_start >= date('now', '-8 weeks')
               ORDER BY sector, week_start"""
        ).fetchall()

    # Group by sector
    sectors: dict[str, list[dict]] = {}
    for r in rows:
        sector = r["sector"]
        if sector not in sectors:
            sectors[sector] = []
        sectors[sector].append({
            "week": r["week_start"],
            "mentions": r["mention_count"],
            "avg_round_size": r["avg_round_size"],
        })

    # Return top sectors by total mentions
    results = []
    for sector, weeks in sorted(sectors.items(), key=lambda x: sum(w["mentions"] for w in x[1]), reverse=True)[:8]:
        results.append(WeeklyTrend(sector=sector, weeks=weeks))

    return results


# --- Static Files ---

@app.get("/")
def serve_index():
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
