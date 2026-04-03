"""
Curator Agent — domain routing and context assembly.

The Curator decides which signal sources to pull based on the content domain,
gathers all context concurrently, and assembles it into a structured payload
for the Writer agent.
"""
import asyncio
from datetime import datetime
from typing import Awaitable, Callable

from src.signals.sources.noaa import get_enso_context
from src.signals.sources.usda import get_usda_context
from src.signals.sources.yahoo_finance import get_futures_prices
from src.signals.sources.crop_temps import get_crop_temp_context
from src.signals.sources.web_search import search_current_context


# Domain → description + which signal sources to pull
DOMAIN_CONFIG = {
    "sibyl": {
        "description": "Sybil — global crops pricing (ENSO, USDA, futures, temp thresholds)",
        "pulls": ["enso", "usda_corn", "usda_wheat", "usda_soybeans", "futures_crops", "crop_temps", "web"],
    },
    "alpha-engine": {
        "description": "Alpha Engine — options flow, GEX, institutional signals",
        "pulls": ["web"],
    },
    "argus": {
        "description": "Argus — geopolitical risk, macro regime analysis",
        "pulls": ["web"],
    },
    "philosophy": {
        "description": "Meaning economy, slow content, epistemic commons",
        "pulls": ["web"],
    },
    "general": {
        "description": "General topic — web search only",
        "pulls": ["web"],
    },
}

DOMAINS = list(DOMAIN_CONFIG.keys())


def _build_pull_registry(
    topic: str, domain: str
) -> dict[str, tuple[str, Callable[[], Awaitable[str]]]]:
    """Map pull keys to (display label, async callable)."""
    return {
        "enso": ("ENSO data (NOAA)", get_enso_context),
        "usda_corn": ("USDA corn data", lambda: get_usda_context("corn")),
        "usda_wheat": ("USDA wheat data", lambda: get_usda_context("wheat")),
        "usda_soybeans": ("USDA soybean data", lambda: get_usda_context("soybeans")),
        "futures_crops": ("Crop futures prices", get_futures_prices),
        "crop_temps": ("Crop temperature thresholds & outlook", get_crop_temp_context),
        "web": ("Web context (Grok)", lambda: search_current_context(topic, domain)),
    }


async def curate(topic: str, domain: str) -> list[str]:
    """
    Pull all relevant signal sources concurrently for a given topic + domain.
    Returns ordered list of context blocks (strings) ready for the Writer.
    """
    config = DOMAIN_CONFIG.get(domain, DOMAIN_CONFIG["general"])
    pulls = config["pulls"]
    registry = _build_pull_registry(topic, domain)

    # Build (key, label, coro) for each requested pull
    tasks = [(key, *registry[key]) for key in pulls if key in registry]

    # Fire all pulls concurrently
    results = await asyncio.gather(
        *(fn() for _, _, fn in tasks), return_exceptions=True
    )

    context_blocks = []
    for (key, label, _), result in zip(tasks, results):
        if isinstance(result, Exception):
            context_blocks.append(f"[{label} failed: {result}]")
        else:
            context_blocks.append(result)

    # Prepend metadata
    metadata = [
        f"Data gathered: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
        f"Topic: {topic}",
        f"Domain: {domain} — {config['description']}",
    ]
    return metadata + context_blocks
