"""TechCrunch Venture RSS feed ingestion."""

import logging
from datetime import datetime
from sqlite3 import Connection

import feedparser
import httpx

from ingestion import classify_sector, parse_amount, parse_round_type

logger = logging.getLogger(__name__)

FEED_URL = "https://techcrunch.com/category/venture/feed/"


async def ingest(conn: Connection):
    """Fetch and parse TechCrunch venture RSS feed."""
    logger.info("Ingesting TechCrunch RSS feed")
    try:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            resp = await client.get(FEED_URL, headers={"User-Agent": "VCPulse/1.0"})
            resp.raise_for_status()
    except Exception as e:
        logger.error(f"Failed to fetch TechCrunch feed: {e}")
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
        amount = parse_amount(combined_text)
        round_type = parse_round_type(combined_text)

        # If it looks like a deal (has amount or round type), store as deal
        if amount or round_type:
            # Try to extract company name from title (before "raises", "secures", etc.)
            company = title.split(" raises")[0].split(" secures")[0].split(" closes")[0].split(" gets")[0].strip()
            if len(company) > 100:
                company = company[:100]
            conn.execute(
                """INSERT OR IGNORE INTO deals
                   (company, round_type, amount_usd, sector, lead_investors, source, source_url, published_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (company, round_type, amount, sector, None, "techcrunch", link, pub_dt),
            )
            count += 1

        # Always store as article
        tags = sector or ""
        conn.execute(
            """INSERT OR IGNORE INTO articles
               (title, summary, source, source_url, tags, published_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (title, summary[:500] if summary else None, "techcrunch", link, tags, pub_dt),
        )

    conn.commit()
    logger.info(f"TechCrunch: ingested {count} deals, {len(feed.entries)} articles")
