"""Pydantic models for API responses."""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class Deal(BaseModel):
    id: int
    company: str
    round_type: Optional[str] = None
    amount_usd: Optional[float] = None
    sector: Optional[str] = None
    lead_investors: Optional[str] = None
    source: Optional[str] = None
    source_url: Optional[str] = None
    published_at: Optional[datetime] = None


class Article(BaseModel):
    id: int
    title: str
    summary: Optional[str] = None
    source: Optional[str] = None
    source_url: Optional[str] = None
    tags: Optional[str] = None
    published_at: Optional[datetime] = None


class SectorHeatmapEntry(BaseModel):
    sector: str
    deal_count: int
    avg_round_size: Optional[float] = None
    total_volume: Optional[float] = None


class WeeklyTrend(BaseModel):
    sector: str
    weeks: list[dict]


class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
    deals_count: int
    articles_count: int


class StatsResponse(BaseModel):
    total_deals: int
    median_round_size: Optional[float] = None
    hottest_sector: Optional[str] = None
    hottest_sector_count: int = 0
    largest_round: Optional[float] = None
    largest_round_company: Optional[str] = None
