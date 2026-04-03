#!/usr/bin/env python3
"""
Content Brief Generator — Threeglau Intelligence
Usage: python brief.py "your topic here" [--domain sibyl|alpha-engine|argus|philosophy] [--model deepseek-reasoner|deepseek-chat] [-o output_path]
"""
import asyncio
import os
import re
import sys
from datetime import datetime
from typing import Callable, Awaitable

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from config import OUTPUT_DIR, DEFAULT_MODEL
from data_sources.noaa import get_enso_context
from data_sources.usda import get_usda_context
from data_sources.yahoo_finance import get_futures_prices
from data_sources.web_search import search_current_context
from data_sources.crop_temps import get_crop_temp_context
from llm.deepseek import generate_brief
from llm.prompts import build_system_prompt, build_user_prompt

console = Console()


# Registry mapping pull keys to (label, async callable)
def _build_pull_registry(
    topic: str, domain: str
) -> dict[str, tuple[str, Callable[[], Awaitable[str]]]]:
    return {
        "enso": ("Pulling ENSO data from NOAA...", get_enso_context),
        "usda_corn": ("Pulling USDA corn data...", lambda: get_usda_context("corn")),
        "usda_wheat": ("Pulling USDA wheat data...", lambda: get_usda_context("wheat")),
        "usda_soybeans": ("Pulling USDA soybean data...", lambda: get_usda_context("soybeans")),
        "futures_crops": ("Pulling crop futures prices...", get_futures_prices),
        "crop_temps": ("Pulling crop temperature thresholds & outlook...", get_crop_temp_context),
        "web": ("Searching web for current context (Grok)...", lambda: search_current_context(topic, domain)),
    }


# Domain-specific data pull configurations
DOMAIN_DATA_PULLS = {
    "sibyl": {
        "description": "Sybil — global crops pricing (ENSO, USDA, futures, temp thresholds)",
        "pulls": ["enso", "usda_corn", "usda_wheat", "usda_soybeans", "futures_crops", "crop_temps", "web"],
    },
    "alpha-engine": {
        "description": "Options flow, GEX, institutional signals",
        "pulls": ["web"],
    },
    "argus": {
        "description": "Geopolitical risk, macro regime analysis",
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


async def gather_context(topic: str, domain: str) -> list[str]:
    """Pull all relevant data sources concurrently based on domain."""
    config = DOMAIN_DATA_PULLS.get(domain, DOMAIN_DATA_PULLS["general"])
    pulls = config["pulls"]
    registry = _build_pull_registry(topic, domain)

    # Build list of (key, label, coro) for requested pulls
    tasks = [(key, *registry[key]) for key in pulls if key in registry]

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task_ids = {key: progress.add_task(label, total=None) for key, label, _ in tasks}
        results = await asyncio.gather(*(fn() for _, _, fn in tasks), return_exceptions=True)

        context_blocks = []
        for (key, _, _), result in zip(tasks, results):
            progress.update(task_ids[key], completed=True)
            if isinstance(result, Exception):
                context_blocks.append(f"[{key} failed: {result}]")
            else:
                context_blocks.append(result)

    # Prepend metadata
    metadata = [
        f"Data gathered: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
        f"Topic: {topic}",
        f"Domain: {domain} — {config['description']}",
    ]
    return metadata + context_blocks


def slugify(text: str) -> str:
    """Convert topic to filename-safe slug."""
    slug = re.sub(r'[^\w\s-]', '', text.lower())
    slug = re.sub(r'[-\s]+', '-', slug).strip('-')
    return slug[:60]


@click.command()
@click.argument("topic")
@click.option("--domain", "-d", default="general",
              type=click.Choice(list(DOMAIN_DATA_PULLS.keys())),
              help="Content domain for targeted data pulls")
@click.option("--model", "-m", default=None,
              help=f"LLM model (default: {DEFAULT_MODEL})")
@click.option("--output", "-o", default=None,
              help="Output file path (default: auto-generated)")
def main(topic: str, domain: str, model: str | None, output: str | None):
    """Generate a Threeglau-style essay prep brief from a topic."""

    console.print(Panel(
        f"[bold]Topic:[/bold] {topic}\n"
        f"[bold]Domain:[/bold] {domain}\n"
        f"[bold]Model:[/bold] {model or DEFAULT_MODEL}",
        title="Content Brief Generator",
        border_style="blue",
    ))

    # 1. Gather context
    console.print("\n[bold cyan]Phase 1: Data Collection[/bold cyan]")
    context_blocks = asyncio.run(gather_context(topic, domain))

    # Show what we got
    total_chars = sum(len(b) for b in context_blocks)
    console.print(f"  Gathered {len(context_blocks)} context blocks ({total_chars:,} chars)\n")

    # 2. Generate brief
    console.print("[bold cyan]Phase 2: Brief Generation (LLM)[/bold cyan]")
    system_prompt = build_system_prompt()
    user_prompt = build_user_prompt(topic, context_blocks)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task(
            f"Generating brief via {model or DEFAULT_MODEL}...", total=None
        )
        brief = asyncio.run(generate_brief(system_prompt, user_prompt, model))
        progress.update(task, completed=True)

    # 3. Save output
    if output is None:
        slug = slugify(topic)
        date_str = datetime.now().strftime("%Y%m%d")
        output = os.path.join(OUTPUT_DIR, f"{date_str}_{slug}.md")

    os.makedirs(os.path.dirname(output) if os.path.dirname(output) else ".", exist_ok=True)
    with open(output, "w") as f:
        f.write(brief)

    console.print(f"\n[bold green]Brief saved to:[/bold green] {output}")
    console.print(f"[dim]({len(brief):,} chars, ~{len(brief.split()):,} words)[/dim]")


if __name__ == "__main__":
    main()
