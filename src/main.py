"""CLI entry point for the investor agent debater."""

from __future__ import annotations

import argparse
import asyncio
import os
import sys

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.agents import BuffettAgent, DruckenmillerAgent, LynchAgent
from src.agents.base import AgentResponse
from src.engine import DebateEngine
from src.market.signals import (
    AlphaEngine2Provider,
    ManualSignalProvider,
    SignalAggregator,
    UWApiProvider,
)


console = Console()


def print_round(round_num: int, statements: list[AgentResponse]):
    """Pretty-print a debate round."""
    console.rule(f"[bold cyan]Round {round_num}[/bold cyan]")

    agent_names = ["BUFFETT", "LYNCH", "DRUCKENMILLER"]
    colors = ["green", "yellow", "red"]

    for i, (name, color, stmt) in enumerate(zip(agent_names, colors, statements)):
        position_emoji = {
            "bullish": "[bold green]BULLISH[/bold green]",
            "bearish": "[bold red]BEARISH[/bold red]",
            "neutral": "[bold yellow]NEUTRAL[/bold yellow]",
            "hold": "[bold blue]HOLD[/bold blue]",
        }.get(stmt.position.lower(), stmt.position)

        panel = Panel(
            f"{stmt.statement}\n\n"
            f"Position: {position_emoji} | "
            f"Confidence: {stmt.confidence:.0%} | "
            f"Tags: {', '.join(stmt.reasoning_tags)}",
            title=f"[bold {color}]{name}[/bold {color}]",
            border_style=color,
        )
        console.print(panel)


def build_signal_aggregator(
    uw_key: str | None = None,
    alpha_url: str | None = None,
    alpha_key: str | None = None,
    manual_context: str | None = None,
) -> SignalAggregator:
    """Build a signal aggregator from available configs."""
    aggregator = SignalAggregator()

    if uw_key:
        aggregator.add_provider(UWApiProvider(api_key=uw_key))

    if alpha_url:
        aggregator.add_provider(AlphaEngine2Provider(base_url=alpha_url, api_key=alpha_key))

    if manual_context:
        aggregator.add_provider(ManualSignalProvider(raw_data=manual_context))

    return aggregator


async def run(args: argparse.Namespace):
    """Run the debate."""
    # R1 config
    api_key = args.api_key or os.environ.get("R1_API_KEY", "")
    base_url = args.base_url or os.environ.get(
        "R1_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3"
    )
    model = args.model or os.environ.get("R1_MODEL", "ep-20250611114928-bp7sf")

    # Create agents
    buffett = BuffettAgent(api_key=api_key, base_url=base_url, model=model)
    lynch = LynchAgent(api_key=api_key, base_url=base_url, model=model)
    druck = DruckenmillerAgent(api_key=api_key, base_url=base_url, model=model)

    # Market signals
    aggregator = build_signal_aggregator(
        uw_key=args.uw_key or os.environ.get("UW_API_KEY"),
        alpha_url=args.alpha_url or os.environ.get("ALPHA_ENGINE_URL"),
        alpha_key=args.alpha_key or os.environ.get("ALPHA_ENGINE_KEY"),
        manual_context=args.market_context,
    )

    # Engine
    engine = DebateEngine(
        agents=[buffett, lynch, druck],
        signal_aggregator=aggregator,
        db_url=args.db_url,
        max_rounds=args.max_rounds,
        consensus_threshold=args.consensus_threshold,
    )

    tickers = [t.strip() for t in args.tickers.split(",")] if args.tickers else None

    console.print(
        Panel(
            f"[bold]Topic:[/bold] {args.topic}\n"
            f"[bold]Tickers:[/bold] {tickers or 'None'}\n"
            f"[bold]Max Rounds:[/bold] {args.max_rounds}\n"
            f"[bold]Model:[/bold] {model}\n"
            f"[bold]Consensus Threshold:[/bold] {args.consensus_threshold:.0%}",
            title="[bold magenta]Investor Agent Debater[/bold magenta]",
            border_style="magenta",
        )
    )

    debate = await engine.run_debate(
        topic=args.topic,
        tickers=tickers,
        on_round=print_round,
    )

    # Final result
    console.print()
    if debate.status == "consensus_reached":
        console.print(
            Panel(
                f"[bold green]CONSENSUS REACHED[/bold green] in {debate.total_rounds} rounds\n\n"
                f"{debate.consensus_summary}",
                title="[bold]Result[/bold]",
                border_style="green",
            )
        )
    else:
        console.print(
            Panel(
                f"[bold red]NO CONSENSUS[/bold red] after {debate.total_rounds} rounds.\n"
                "The agents could not agree on a position within the round limit.",
                title="[bold]Result[/bold]",
                border_style="red",
            )
        )

    console.print(f"\nDebate ID: {debate.id} (stored in {args.db_url})")


def main():
    parser = argparse.ArgumentParser(
        description="Investor Agent Debater — Buffett, Lynch, Druckenmiller debate investment theses"
    )
    parser.add_argument("topic", help="The investment thesis or question to debate")
    parser.add_argument("--tickers", help="Comma-separated list of tickers for market signals")
    parser.add_argument("--max-rounds", type=int, default=10, help="Maximum debate rounds (default: 10)")
    parser.add_argument("--consensus-threshold", type=float, default=0.7, help="Confidence threshold for supermajority consensus (default: 0.7)")
    parser.add_argument("--db-url", default="sqlite:///debates.db", help="Database URL (default: sqlite:///debates.db)")

    # Model config
    parser.add_argument("--api-key", help="Bytedance R1 API key (or set R1_API_KEY env var)")
    parser.add_argument("--base-url", help="R1 API base URL (or set R1_BASE_URL env var)")
    parser.add_argument("--model", help="R1 model name (or set R1_MODEL env var)")

    # Market signal config
    parser.add_argument("--uw-key", help="Unusual Whales API key (or set UW_API_KEY env var)")
    parser.add_argument("--alpha-url", help="Alpha Engine 2.0 base URL (or set ALPHA_ENGINE_URL env var)")
    parser.add_argument("--alpha-key", help="Alpha Engine 2.0 API key (or set ALPHA_ENGINE_KEY env var)")
    parser.add_argument("--market-context", help="Manual market context string to inject")

    args = parser.parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
