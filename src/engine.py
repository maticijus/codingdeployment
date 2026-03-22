"""Debate engine — orchestrates rounds between three investor agents until consensus."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from src.agents.base import AgentResponse, DebaterAgent
from src.db.models import AgentStatement, Debate, DebateRound, MarketSignal, init_db
from src.market.signals import MarketSignalData, SignalAggregator


class ConsensusChecker:
    """Determines whether the three agents have reached consensus."""

    @staticmethod
    def check(statements: list[AgentResponse], threshold: float = 0.7) -> tuple[bool, str | None]:
        """Check if agents have reached consensus.

        Consensus is reached when:
        1. All agents share the same position (bullish/bearish/neutral/hold), OR
        2. At least 2 agents agree AND their average confidence exceeds the threshold.

        Returns:
            (reached, summary) — summary is None if no consensus.
        """
        positions = [s.position.lower() for s in statements]
        confidences = [s.confidence for s in statements]

        # Unanimous agreement
        if len(set(positions)) == 1:
            avg_conf = sum(confidences) / len(confidences)
            return True, (
                f"Unanimous {positions[0]} consensus (avg confidence: {avg_conf:.0%}). "
                f"All three agents agree."
            )

        # Supermajority (2 of 3 agree) with high confidence
        for pos in set(positions):
            agreers = [i for i, p in enumerate(positions) if p == pos]
            if len(agreers) >= 2:
                avg_conf = sum(confidences[i] for i in agreers) / len(agreers)
                if avg_conf >= threshold:
                    dissenter_idx = [i for i in range(3) if i not in agreers][0]
                    return True, (
                        f"Supermajority {pos} consensus (2/3 agents, avg confidence: {avg_conf:.0%}). "
                        f"Dissenter ({statements[dissenter_idx].position}) acknowledged."
                    )

        return False, None


class DebateEngine:
    """Orchestrates multi-round debates between three investor agents.

    The engine runs rounds until consensus is reached or max_rounds is hit.
    All debate data is persisted to the database.
    """

    def __init__(
        self,
        agents: list[DebaterAgent],
        signal_aggregator: SignalAggregator | None = None,
        db_url: str = "sqlite:///debates.db",
        max_rounds: int = 10,
        consensus_threshold: float = 0.7,
    ):
        if len(agents) != 3:
            raise ValueError("Exactly 3 debater agents are required.")

        self.agents = agents
        self.signal_aggregator = signal_aggregator or SignalAggregator()
        self.session_factory = init_db(db_url)
        self.max_rounds = max_rounds
        self.consensus_checker = ConsensusChecker()
        self.consensus_threshold = consensus_threshold

    async def run_debate(
        self,
        topic: str,
        tickers: list[str] | None = None,
        on_round: callable | None = None,
    ) -> Debate:
        """Run a full debate session.

        Args:
            topic: The investment thesis or question to debate.
            tickers: Optional list of tickers to fetch market signals for.
            on_round: Optional callback(round_number, statements) for live output.

        Returns:
            The completed Debate ORM object.
        """
        session: Session = self.session_factory()

        # Fetch market signals
        signals = await self.signal_aggregator.gather(tickers)
        market_context = SignalAggregator.format_for_debate(signals)

        # Create debate record
        debate = Debate(
            topic=topic,
            market_context=market_context if signals else None,
            max_rounds=self.max_rounds,
        )
        session.add(debate)
        session.commit()

        # Persist market signals
        for sig in signals:
            db_signal = MarketSignal(
                debate_id=debate.id,
                source=sig.source,
                signal_type=sig.signal_type,
                ticker=sig.ticker,
                data=json.dumps(sig.data, default=str),
            )
            session.add(db_signal)
        session.commit()

        # Debate loop
        debate_history: list[dict] = []

        for round_num in range(1, self.max_rounds + 1):
            db_round = DebateRound(debate_id=debate.id, round_number=round_num)
            session.add(db_round)
            session.commit()

            round_statements: list[AgentResponse] = []

            for agent in self.agents:
                response = agent.respond(
                    topic=topic,
                    debate_history=debate_history,
                    market_context=market_context if signals else None,
                )

                round_statements.append(response)

                # Persist statement
                db_statement = AgentStatement(
                    round_id=db_round.id,
                    agent_name=agent.name,
                    statement=response.statement,
                    position=response.position,
                    confidence=response.confidence,
                    reasoning_tags=",".join(response.reasoning_tags),
                )
                session.add(db_statement)

                # Add to history for next agent/round
                debate_history.append({
                    "agent": agent.name,
                    "statement": response.statement,
                    "position": response.position,
                    "confidence": response.confidence,
                    "round": round_num,
                })

            session.commit()
            debate.total_rounds = round_num

            # Callback for live display
            if on_round:
                on_round(round_num, round_statements)

            # Check consensus
            reached, summary = self.consensus_checker.check(
                round_statements, self.consensus_threshold
            )
            if reached:
                debate.status = "consensus_reached"
                debate.consensus_summary = summary
                debate.completed_at = datetime.now(timezone.utc)
                session.commit()
                session.close()
                return debate

        # Max rounds reached without consensus
        debate.status = "no_consensus"
        debate.completed_at = datetime.now(timezone.utc)
        session.commit()
        session.close()
        return debate

    def get_debate(self, debate_id: int) -> Debate | None:
        """Retrieve a debate by ID."""
        session = self.session_factory()
        debate = session.query(Debate).filter_by(id=debate_id).first()
        session.close()
        return debate

    def list_debates(self, limit: int = 20) -> list[Debate]:
        """List recent debates."""
        session = self.session_factory()
        debates = session.query(Debate).order_by(Debate.created_at.desc()).limit(limit).all()
        session.close()
        return debates
