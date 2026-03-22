"""SQLAlchemy models for storing debates, rounds, and market signals."""

from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Session, relationship, sessionmaker


class Base(DeclarativeBase):
    pass


class Debate(Base):
    """A full debate session between the three investor agents."""

    __tablename__ = "debates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    topic = Column(Text, nullable=False)
    market_context = Column(Text, nullable=True)
    status = Column(
        Enum("in_progress", "consensus_reached", "no_consensus", name="debate_status"),
        default="in_progress",
    )
    consensus_summary = Column(Text, nullable=True)
    total_rounds = Column(Integer, default=0)
    max_rounds = Column(Integer, default=10)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime, nullable=True)

    rounds = relationship("DebateRound", back_populates="debate", order_by="DebateRound.round_number")
    signals = relationship("MarketSignal", back_populates="debate")


class DebateRound(Base):
    """A single round of debate containing statements from each agent."""

    __tablename__ = "debate_rounds"

    id = Column(Integer, primary_key=True, autoincrement=True)
    debate_id = Column(Integer, ForeignKey("debates.id"), nullable=False)
    round_number = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    debate = relationship("Debate", back_populates="rounds")
    statements = relationship("AgentStatement", back_populates="round", order_by="AgentStatement.id")


class AgentStatement(Base):
    """An individual statement made by one agent in a debate round."""

    __tablename__ = "agent_statements"

    id = Column(Integer, primary_key=True, autoincrement=True)
    round_id = Column(Integer, ForeignKey("debate_rounds.id"), nullable=False)
    agent_name = Column(String(50), nullable=False)  # buffett, lynch, druckenmiller
    statement = Column(Text, nullable=False)
    position = Column(String(20), nullable=True)  # bullish, bearish, neutral, hold
    confidence = Column(Float, nullable=True)  # 0.0 to 1.0
    reasoning_tags = Column(Text, nullable=True)  # comma-separated tags
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    round = relationship("DebateRound", back_populates="statements")


class MarketSignal(Base):
    """Market data signals ingested for a debate."""

    __tablename__ = "market_signals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    debate_id = Column(Integer, ForeignKey("debates.id"), nullable=False)
    source = Column(String(100), nullable=False)  # e.g., "uw_api", "alpha_engine_2"
    signal_type = Column(String(50), nullable=False)  # e.g., "price", "sentiment", "macro"
    ticker = Column(String(20), nullable=True)
    data = Column(Text, nullable=False)  # JSON string of signal payload
    fetched_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    debate = relationship("Debate", back_populates="signals")


def get_engine(db_url: str = "sqlite:///debates.db"):
    """Create and return a database engine."""
    return create_engine(db_url, echo=False)


def init_db(db_url: str = "sqlite:///debates.db") -> sessionmaker:
    """Initialize the database and return a session factory."""
    engine = get_engine(db_url)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)
