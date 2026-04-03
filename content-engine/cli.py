#!/usr/bin/env python3
"""
Threeglau Content Engine — CLI entry point.

Usage:
    # Essay brief (full pipeline)
    python cli.py brief "ENSO cycles and crop commodity prediction" --domain sibyl

    # Just collect signals (no LLM)
    python cli.py signals "corn futures outlook" --domain sibyl

    # Override model
    python cli.py brief "building a multi-agent trading system" --domain alpha-engine --model deepseek-chat

    # Output to specific file
    python cli.py brief "the meaning economy" --domain philosophy -o ~/briefs/meaning.md
"""
import asyncio

import click
from rich.console import Console

from src.config import DEFAULT_MODEL
from src.editorial.curator import curate, DOMAINS
from src.editorial.pipeline import run_pipeline

console = Console()


@click.group()
def cli():
    """Threeglau Content Engine — signal collection + editorial pipeline."""
    pass


@cli.command()
@click.argument("topic")
@click.option("--domain", "-d", default="general",
              type=click.Choice(DOMAINS),
              help="Content domain for targeted signal pulls")
@click.option("--model", "-m", default=None,
              help=f"LLM model (default: {DEFAULT_MODEL})")
@click.option("--output", "-o", default=None,
              help="Output file path (default: auto-generated)")
def brief(topic: str, domain: str, model: str | None, output: str | None):
    """Generate a Threeglau-style essay prep brief."""
    asyncio.run(run_pipeline(topic, domain, model, output))


@cli.command()
@click.argument("topic")
@click.option("--domain", "-d", default="general",
              type=click.Choice(DOMAINS),
              help="Signal domain")
def signals(topic: str, domain: str):
    """Collect signals only (no LLM generation)."""
    blocks = asyncio.run(curate(topic, domain))
    total_chars = sum(len(b) for b in blocks)
    console.print(f"[bold green]Collected {len(blocks)} blocks ({total_chars:,} chars)[/bold green]\n")
    console.print("\n\n---\n\n".join(blocks))


if __name__ == "__main__":
    cli()
