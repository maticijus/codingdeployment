"""GitHub Trending repositories ingestion."""

import logging
from datetime import datetime, timedelta
from sqlite3 import Connection

import httpx

from ingestion import classify_sector

logger = logging.getLogger(__name__)

API_URL = "https://api.github.com/search/repositories"


async def ingest(conn: Connection):
    """Fetch trending GitHub repositories from the past week."""
    logger.info("Ingesting GitHub trending repositories")

    since_date = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d")

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                API_URL,
                params={
                    "q": f"created:>{since_date}",
                    "sort": "stars",
                    "order": "desc",
                    "per_page": 25,
                },
                headers={"Accept": "application/vnd.github.v3+json", "User-Agent": "VCPulse/1.0"},
            )
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        logger.error(f"Failed to fetch GitHub trending: {e}")
        return

    count = 0
    for repo in data.get("items", []):
        name = repo.get("full_name", "")
        description = repo.get("description", "") or ""
        stars = repo.get("stargazers_count", 0)
        url = repo.get("html_url", "")
        language = repo.get("language", "")
        created = repo.get("created_at", "")

        pub_dt = None
        if created:
            try:
                pub_dt = datetime.fromisoformat(created.replace("Z", "+00:00")).isoformat()
            except Exception:
                pass

        combined = f"{name} {description} {language}"
        sector = classify_sector(combined)
        topics = repo.get("topics", [])
        tags_list = []
        if sector:
            tags_list.append(sector)
        if language:
            tags_list.append(language)
        tags_list.extend(topics[:3])
        tags = ", ".join(tags_list[:5])

        summary = f"★ {stars} | {language or 'N/A'} | {description[:200]}"

        conn.execute(
            """INSERT OR IGNORE INTO articles
               (title, summary, source, source_url, tags, published_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (f"[GitHub Trending] {name}", summary, "github", url, tags, pub_dt),
        )
        count += 1

    conn.commit()
    logger.info(f"GitHub Trending: ingested {count} repositories")
