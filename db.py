"""SQLite database connection and helpers."""

import sqlite3
import os
from contextlib import contextmanager
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vcpulse.db")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


@contextmanager
def get_db():
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS deals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company TEXT NOT NULL,
                round_type TEXT,
                amount_usd REAL,
                sector TEXT,
                lead_investors TEXT,
                source TEXT,
                source_url TEXT,
                published_at DATETIME,
                ingested_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(company, published_at, source)
            );

            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                summary TEXT,
                source TEXT,
                source_url TEXT,
                tags TEXT,
                published_at DATETIME,
                ingested_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(title, source)
            );

            CREATE TABLE IF NOT EXISTS sector_signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sector TEXT NOT NULL,
                mention_count INTEGER DEFAULT 1,
                avg_round_size REAL,
                week_start DATE,
                UNIQUE(sector, week_start)
            );

            CREATE INDEX IF NOT EXISTS idx_deals_published ON deals(published_at);
            CREATE INDEX IF NOT EXISTS idx_deals_sector ON deals(sector);
            CREATE INDEX IF NOT EXISTS idx_articles_published ON articles(published_at);
            CREATE INDEX IF NOT EXISTS idx_sector_signals_week ON sector_signals(week_start);
        """)


def insert_deal(conn: sqlite3.Connection, deal: dict):
    conn.execute(
        """INSERT OR IGNORE INTO deals
           (company, round_type, amount_usd, sector, lead_investors, source, source_url, published_at)
           VALUES (:company, :round_type, :amount_usd, :sector, :lead_investors, :source, :source_url, :published_at)""",
        deal,
    )


def insert_article(conn: sqlite3.Connection, article: dict):
    conn.execute(
        """INSERT OR IGNORE INTO articles
           (title, summary, source, source_url, tags, published_at)
           VALUES (:title, :summary, :source, :source_url, :tags, :published_at)""",
        article,
    )


def update_sector_signals(conn: sqlite3.Connection):
    """Rebuild sector_signals from deals data."""
    conn.execute("DELETE FROM sector_signals")
    conn.execute("""
        INSERT INTO sector_signals (sector, mention_count, avg_round_size, week_start)
        SELECT
            sector,
            COUNT(*) as mention_count,
            AVG(amount_usd) as avg_round_size,
            DATE(published_at, 'weekday 0', '-6 days') as week_start
        FROM deals
        WHERE sector IS NOT NULL AND sector != ''
        GROUP BY sector, DATE(published_at, 'weekday 0', '-6 days')
    """)


if __name__ == "__main__":
    init_db()
    print(f"Database initialized at {DB_PATH}")
