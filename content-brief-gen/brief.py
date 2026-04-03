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

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from config import OUTPUT_DIR, DEFAULT_MODEL
from data_sources.noaa import get_enso_context
from data_sources.usda import get_usda_context
from data_sources.yahoo_finance import get_futures_prices, FUTURES_MAP
from data_sources.web_search import search_current_context
from llm.deepseek import generate_brief
from llm.prompts import build_system_prompt, build_user_prompt

console = Console()

# Domain-specific data pull configurations
DOMAIN_DATA_PULLS = {
    "sibyl": {
        "description": "Crop commodity prediction (ENSO, NDVI, USDA)",
        "pulls": ["enso", "usda_corn", "usda_wheat", "usda_soybeans", "futures_crops", "web"],
    },
    "alpha-engine": {
        "description": "Options flow, GEX, institutional signals",
        "pulls": ["web"],  # Alpha Engine data is internal, web search for market context
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
    """Pull all relevant data sources based on domain."""
    config = DOMAIN_DATA_PULLS.get(domain, DOMAIN_DATA_PULLS["general"])
    pulls = config["pulls"]
    context_blocks = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:

        if "enso" in pulls:
            task = progress.add_task("Pulling ENSO data from NOAA...", total=None)
            result = await get_enso_context()
            context_blocks.append(result)
            progress.update(task, completed=True)

        if "usda_corn" in pulls:
            task = progress.add_task("Pulling USDA corn data...", total=None)
            result = await get_usda_context("corn")
            context_blocks.append(result)
            progress.update(task, completed=True)

        if "usda_wheat" in pulls:
            task = progress.add_task("Pulling USDA wheat data...", total=None)
            result = await get_usda_context("wheat")
            context_blocks.append(result)
            progress.update(task, completed=True)

        if "usda_soybeans" in pulls:
            task = progress.add_task("Pulling USDA soybean data...", total=None)
            result = await get_usda_context("soybeans")
            context_blocks.append(result)
            progress.update(task, completed=True)

        if "futures_crops" in pulls:
            task = progress.add_task("Pulling crop futures prices...", total=None)
            result = await get_futures_prices()
            context_blocks.append(result)
            progress.update(task, completed=True)

        if "web" in pulls:
            task = progress.add_task("Searching web for current context (Grok)...", total=None)
            result = await search_current_context(topic, domain)
            context_blocks.append(result)
            progress.update(task, completed=True)

    # Add metadata
    context_blocks.insert(0, f"Data gathered: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    context_blocks.insert(1, f"Topic: {topic}")
    context_blocks.insert(2, f"Domain: {domain} — {config['description']}")

    return context_blocks


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
