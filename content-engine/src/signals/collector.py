"""
Signal Collector — polls all signal sources and returns normalized context.

This is the standalone entry point for signal collection, usable by cron
or by the editorial pipeline's Curator agent.

    python -m src.signals.collector --domain sibyl --topic "corn futures"
"""
import asyncio

import click

from src.editorial.curator import curate, DOMAINS


@click.command()
@click.option("--topic", "-t", required=True, help="Topic to gather signals for")
@click.option("--domain", "-d", default="general",
              type=click.Choice(DOMAINS),
              help="Signal domain")
def main(topic: str, domain: str):
    """Collect signals for a topic and print to stdout."""
    blocks = asyncio.run(curate(topic, domain))
    print("\n\n---\n\n".join(blocks))


if __name__ == "__main__":
    main()
