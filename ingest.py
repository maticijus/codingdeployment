"""Main ingestion orchestrator — runs all data source modules."""

import asyncio
import logging
import sys
from datetime import datetime

from db import init_db, get_db, update_sector_signals
from ingestion import techcrunch, pitchbook, cbinsights, a16z, firstround, hackernews, github_trending

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("vcpulse.ingest")

SOURCES = [
    ("TechCrunch", techcrunch.ingest),
    ("PitchBook", pitchbook.ingest),
    ("CB Insights", cbinsights.ingest),
    ("a16z", a16z.ingest),
    ("First Round", firstround.ingest),
    ("Hacker News", hackernews.ingest),
    ("GitHub Trending", github_trending.ingest),
]


async def run_all():
    """Run all ingestion sources, each isolated so one failure doesn't stop others."""
    init_db()
    logger.info("Starting VC Pulse ingestion run")
    start = datetime.utcnow()

    with get_db() as conn:
        for name, ingest_fn in SOURCES:
            try:
                await ingest_fn(conn)
            except Exception as e:
                logger.error(f"Source '{name}' failed: {e}", exc_info=True)

        # Rebuild sector signals after all sources are ingested
        try:
            update_sector_signals(conn)
            logger.info("Sector signals updated")
        except Exception as e:
            logger.error(f"Failed to update sector signals: {e}", exc_info=True)

    elapsed = (datetime.utcnow() - start).total_seconds()
    logger.info(f"Ingestion complete in {elapsed:.1f}s")


if __name__ == "__main__":
    asyncio.run(run_all())
