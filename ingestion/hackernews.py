"""Hacker News (Algolia API) ingestion for VC/funding stories."""

import logging
from datetime import datetime
from sqlite3 import Connection

import httpx

from ingestion import classify_sector, parse_amount, parse_round_type

logger = logging.getLogger(__name__)

API_URL = "http://hn.algolia.com/api/v1/search"
QUERIES = ["funding round", "series a", "series b", "raises million", "venture capital"]


async def ingest(conn: Connection):
    """Fetch VC/funding stories from Hacker News via Algolia API."""
    logger.info("Ingesting Hacker News funding stories")
    seen_ids = set()

    async with httpx.AsyncClient(timeout=30) as client:
        for query in QUERIES:
            try:
                resp = await client.get(
                    API_URL,
                    params={"query": query, "tags": "story", "hitsPerPage": 20},
                )
                resp.raise_for_status()
                data = resp.json()
            except Exception as e:
                logger.error(f"Failed to fetch HN query '{query}': {e}")
                continue

            for hit in data.get("hits", []):
                obj_id = hit.get("objectID")
                if obj_id in seen_ids:
                    continue
                seen_ids.add(obj_id)

                title = hit.get("title", "")
                url = hit.get("url", "")
                points = hit.get("points", 0)
                created = hit.get("created_at", "")

                pub_dt = None
                if created:
                    try:
                        pub_dt = datetime.fromisoformat(created.replace("Z", "+00:00")).isoformat()
                    except Exception:
                        pass

                combined_text = title
                sector = classify_sector(combined_text)
                amount = parse_amount(combined_text)
                round_type = parse_round_type(combined_text)

                hn_url = f"https://news.ycombinator.com/item?id={obj_id}"

                # Store as deal if it has funding info
                if amount or round_type:
                    company = title.split(" raises")[0].split(" secures")[0].split(" closes")[0].strip()
                    if len(company) > 100:
                        company = company[:100]
                    conn.execute(
                        """INSERT OR IGNORE INTO deals
                           (company, round_type, amount_usd, sector, lead_investors, source, source_url, published_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                        (company, round_type, amount, sector, None, "hackernews", url or hn_url, pub_dt),
                    )

                # Store as article
                conn.execute(
                    """INSERT OR IGNORE INTO articles
                       (title, summary, source, source_url, tags, published_at)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (title, f"HN points: {points}", "hackernews", url or hn_url, sector, pub_dt),
                )

    conn.commit()
    logger.info(f"Hacker News: processed {len(seen_ids)} stories")
