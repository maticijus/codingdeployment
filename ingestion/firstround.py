"""First Round Review RSS feed ingestion."""

import logging
from datetime import datetime
from sqlite3 import Connection

import feedparser
import httpx

from ingestion import classify_sector

logger = logging.getLogger(__name__)

FEED_URL = "https://review.firstround.com/feed.xml"


async def ingest(conn: Connection):
    """Fetch and parse First Round Review RSS feed."""
    logger.info("Ingesting First Round Review RSS feed")
    try:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            resp = await client.get(FEED_URL, headers={"User-Agent": "VCPulse/1.0"})
            resp.raise_for_status()
    except Exception as e:
        logger.error(f"Failed to fetch First Round Review feed: {e}")
        return

    feed = feedparser.parse(resp.text)
    count = 0

    for entry in feed.entries:
        title = entry.get("title", "")
        summary = entry.get("summary", "")
        link = entry.get("link", "")
        published = entry.get("published_parsed")

        pub_dt = None
        if published:
            try:
                pub_dt = datetime(*published[:6]).isoformat()
            except Exception:
                pass

        combined_text = f"{title} {summary}"
        sector = classify_sector(combined_text)
        tags_list = []
        if sector:
            tags_list.append(sector)
        for tag in entry.get("tags", []):
            term = tag.get("term", "")
            if term and len(term) < 50:
                tags_list.append(term)

        tags = ", ".join(tags_list[:5]) if tags_list else None

        conn.execute(
            """INSERT OR IGNORE INTO articles
               (title, summary, source, source_url, tags, published_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (title, summary[:500] if summary else None, "firstround", link, tags, pub_dt),
        )
        count += 1

    conn.commit()
    logger.info(f"First Round Review: ingested {count} articles")
