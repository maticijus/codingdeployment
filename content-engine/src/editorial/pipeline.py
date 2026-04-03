"""
Editorial Pipeline — orchestrates Curator → Writer.

Can be run standalone via:
    python -m src.editorial.pipeline --topic "..." --domain sibyl
"""
import asyncio
import os
import re
from datetime import datetime

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from src.config import OUTPUT_DIR, DEFAULT_MODEL
from src.editorial.curator import curate, DOMAIN_CONFIG, DOMAINS
from src.editorial.writer import write_brief

console = Console()


def slugify(text: str) -> str:
    """Convert topic to filename-safe slug."""
    slug = re.sub(r'[^\w\s-]', '', text.lower())
    slug = re.sub(r'[-\s]+', '-', slug).strip('-')
    return slug[:60]


async def run_pipeline(
    topic: str,
    domain: str = "general",
    model: str | None = None,
    output: str | None = None,
) -> str:
    """
    Run the full editorial pipeline: Curator → Writer → save.
    Returns the output file path.
    """
    console.print(Panel(
        f"[bold]Topic:[/bold] {topic}\n"
        f"[bold]Domain:[/bold] {domain}\n"
        f"[bold]Model:[/bold] {model or DEFAULT_MODEL}",
        title="Threeglau Content Engine",
        border_style="blue",
    ))

    # Phase 1: Curator — gather context
    console.print("\n[bold cyan]Phase 1: Curator — Signal Collection[/bold cyan]")
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Curating signals...", total=None)
        context_blocks = await curate(topic, domain)
        progress.update(task, completed=True)

    total_chars = sum(len(b) for b in context_blocks)
    console.print(f"  Gathered {len(context_blocks)} context blocks ({total_chars:,} chars)\n")

    # Phase 2: Writer — generate brief
    console.print("[bold cyan]Phase 2: Writer — Brief Generation[/bold cyan]")
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task(
            f"Generating brief via {model or DEFAULT_MODEL}...", total=None
        )
        brief = await write_brief(topic, context_blocks, model)
        progress.update(task, completed=True)

    # Phase 3: Save output
    if output is None:
        slug = slugify(topic)
        date_str = datetime.now().strftime("%Y%m%d")
        output = os.path.join(OUTPUT_DIR, f"{date_str}_{slug}.md")

    os.makedirs(os.path.dirname(output) if os.path.dirname(output) else ".", exist_ok=True)
    with open(output, "w") as f:
        f.write(brief)

    console.print(f"\n[bold green]Brief saved to:[/bold green] {output}")
    console.print(f"[dim]({len(brief):,} chars, ~{len(brief.split()):,} words)[/dim]")
    return output


@click.command()
@click.option("--topic", "-t", required=True, help="Essay topic")
@click.option("--domain", "-d", default="general",
              type=click.Choice(DOMAINS),
              help="Content domain for targeted signal pulls")
@click.option("--model", "-m", default=None,
              help=f"LLM model (default: {DEFAULT_MODEL})")
@click.option("--output", "-o", default=None,
              help="Output file path (default: auto-generated)")
def main(topic: str, domain: str, model: str | None, output: str | None):
    """Run the editorial pipeline: Curator → Writer → output."""
    asyncio.run(run_pipeline(topic, domain, model, output))


if __name__ == "__main__":
    main()
