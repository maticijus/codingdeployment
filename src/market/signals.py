"""Market signal ingestion from UW APIs, Alpha Engine 2.0, and other sources."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone

import httpx


@dataclass
class MarketSignalData:
    """A single market signal data point."""

    source: str
    signal_type: str
    ticker: str | None
    data: dict
    fetched_at: datetime


class MarketSignalProvider:
    """Base class for market signal providers."""

    source_name: str = "generic"

    async def fetch(self, tickers: list[str] | None = None) -> list[MarketSignalData]:
        raise NotImplementedError


class UWApiProvider(MarketSignalProvider):
    """Fetch signals from UW (Unusual Whales) API or similar endpoints."""

    source_name = "uw_api"

    def __init__(self, base_url: str = "https://api.unusualwhales.com", api_key: str | None = None):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or "PLACEHOLDER_UW_KEY"

    async def fetch(self, tickers: list[str] | None = None) -> list[MarketSignalData]:
        """Fetch flow and sentiment data from UW API."""
        signals = []
        headers = {"Authorization": f"Bearer {self.api_key}"}

        async with httpx.AsyncClient(timeout=30) as client:
            # Options flow
            try:
                resp = await client.get(
                    f"{self.base_url}/api/stock/flow",
                    headers=headers,
                    params={"limit": 20},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    signals.append(MarketSignalData(
                        source=self.source_name,
                        signal_type="options_flow",
                        ticker=None,
                        data=data,
                        fetched_at=datetime.now(timezone.utc),
                    ))
            except httpx.HTTPError:
                pass  # Signal unavailable — degrade gracefully

            # Per-ticker sentiment
            for ticker in (tickers or []):
                try:
                    resp = await client.get(
                        f"{self.base_url}/api/stock/{ticker}/sentiment",
                        headers=headers,
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        signals.append(MarketSignalData(
                            source=self.source_name,
                            signal_type="sentiment",
                            ticker=ticker,
                            data=data,
                            fetched_at=datetime.now(timezone.utc),
                        ))
                except httpx.HTTPError:
                    pass

        return signals


class AlphaEngine2Provider(MarketSignalProvider):
    """Fetch signals from Alpha Engine 2.0 internal API."""

    source_name = "alpha_engine_2"

    def __init__(self, base_url: str = "http://localhost:8080", api_key: str | None = None):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    async def fetch(self, tickers: list[str] | None = None) -> list[MarketSignalData]:
        """Fetch alpha signals — macro, factor exposure, momentum, etc."""
        signals = []
        headers = {}
        if self.api_key:
            headers["X-API-Key"] = self.api_key

        async with httpx.AsyncClient(timeout=30) as client:
            # Macro regime
            try:
                resp = await client.get(f"{self.base_url}/v2/macro/regime", headers=headers)
                if resp.status_code == 200:
                    signals.append(MarketSignalData(
                        source=self.source_name,
                        signal_type="macro_regime",
                        ticker=None,
                        data=resp.json(),
                        fetched_at=datetime.now(timezone.utc),
                    ))
            except httpx.HTTPError:
                pass

            # Factor scores per ticker
            for ticker in (tickers or []):
                try:
                    resp = await client.get(
                        f"{self.base_url}/v2/factors/{ticker}",
                        headers=headers,
                    )
                    if resp.status_code == 200:
                        signals.append(MarketSignalData(
                            source=self.source_name,
                            signal_type="factor_scores",
                            ticker=ticker,
                            data=resp.json(),
                            fetched_at=datetime.now(timezone.utc),
                        ))
                except httpx.HTTPError:
                    pass

            # Momentum / liquidity
            try:
                resp = await client.get(
                    f"{self.base_url}/v2/signals/momentum",
                    headers=headers,
                    params={"tickers": ",".join(tickers)} if tickers else {},
                )
                if resp.status_code == 200:
                    signals.append(MarketSignalData(
                        source=self.source_name,
                        signal_type="momentum",
                        ticker=None,
                        data=resp.json(),
                        fetched_at=datetime.now(timezone.utc),
                    ))
            except httpx.HTTPError:
                pass

        return signals


class ManualSignalProvider(MarketSignalProvider):
    """Allows manually injecting market context as raw text/JSON."""

    source_name = "manual"

    def __init__(self, raw_data: str | dict | None = None):
        self.raw_data = raw_data

    async def fetch(self, tickers: list[str] | None = None) -> list[MarketSignalData]:
        if not self.raw_data:
            return []
        data = self.raw_data if isinstance(self.raw_data, dict) else {"raw": self.raw_data}
        return [
            MarketSignalData(
                source=self.source_name,
                signal_type="manual",
                ticker=None,
                data=data,
                fetched_at=datetime.now(timezone.utc),
            )
        ]


class SignalAggregator:
    """Aggregates signals from multiple providers and formats them for the debate."""

    def __init__(self, providers: list[MarketSignalProvider] | None = None):
        self.providers = providers or []

    def add_provider(self, provider: MarketSignalProvider):
        self.providers.append(provider)

    async def gather(self, tickers: list[str] | None = None) -> list[MarketSignalData]:
        """Fetch signals from all registered providers."""
        all_signals = []
        for provider in self.providers:
            try:
                signals = await provider.fetch(tickers)
                all_signals.extend(signals)
            except Exception:
                pass  # Individual provider failure shouldn't block debate
        return all_signals

    @staticmethod
    def format_for_debate(signals: list[MarketSignalData]) -> str:
        """Format aggregated signals into a text block for agent consumption."""
        if not signals:
            return "No market signals available."

        sections = []
        for sig in signals:
            header = f"[{sig.source.upper()} | {sig.signal_type}]"
            if sig.ticker:
                header += f" Ticker: {sig.ticker}"
            body = json.dumps(sig.data, indent=2, default=str)
            sections.append(f"{header}\n{body}")

        return "\n\n".join(sections)
