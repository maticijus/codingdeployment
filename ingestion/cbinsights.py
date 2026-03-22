"""CB Insights blog/newsletter scraping."""

import logging
from datetime import datetime
from sqlite3 import Connection

import httpx
from bs4 import BeautifulSoup

from ingestion import classify_sector

logger = logging.getLogger(__name__)

BLOG_URL = "https://www.cbinsights.com/research/"


async def ingest(conn: Connection):
    """Scrape CB Insights research blog for trend articles."""
    logger.info("Ingesting CB Insights blog")
    try:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            resp = await client.get(BLOG_URL, headers={"User-Agent": "VCPulse/1.0"})
            resp.raise_for_status()
    except Exception as e:
        logger.error(f"Failed to fetch CB Insights blog: {e}")
        return

    soup = BeautifulSoup(resp.text, "lxml")
    count = 0

    # Look for article elements — CB Insights uses various selectors
    articles = soup.select("article, .post-item, .research-item, .card")
    if not articles:
        # Fallback: look for links with research-like patterns
        articles = soup.select("a[href*='/research/']")

    for item in articles[:30]:
        # Extract title
        title_el = item.select_one("h2, h3, h4, .title, .headline")
        if title_el:
            title = title_el.get_text(strip=True)
        elif item.name == "a":
            title = item.get_text(strip=True)
        else:
            continue

        if not title or len(title) < 10:
            continue

        # Extract link
        link_el = item.select_one("a[href]") if item.name != "a" else item
        link = link_el.get("href", "") if link_el else ""
        if link and not link.startswith("http"):
            link = f"https://www.cbinsights.com{link}"

        # Extract summary
        summary_el = item.select_one("p, .excerpt, .summary, .description")
        summary = summary_el.get_text(strip=True) if summary_el else None

        sector = classify_sector(f"{title} {summary or ''}")
        tags = sector if sector else None

        conn.execute(
            """INSERT OR IGNORE INTO articles
               (title, summary, source, source_url, tags, published_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (title, summary[:500] if summary else None, "cbinsights", link, tags, datetime.utcnow().isoformat()),
        )
        count += 1

    conn.commit()
    logger.info(f"CB Insights: ingested {count} articles")
