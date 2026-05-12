"""SQLite-based caching for analytics API responses.

Account-aware: cache keys now include `account` so data from different
profiles on the same platform doesn't collide.
"""

import sqlite3
import json
import hashlib
import os
from datetime import date, timedelta
from typing import List, Optional
from attribution_schema import Metric


class Cache:
    """SQLite cache for metrics data with account isolation."""

    def __init__(self, db_path: Optional[str] = None):
        # Use absolute path based on current working directory
        if db_path is None:
            db_path = os.path.join(os.getcwd(), ".attribution_cache.db")
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize database schema with account column."""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source TEXT NOT NULL,
                    account TEXT NOT NULL DEFAULT 'default',
                    date DATE NOT NULL,
                    metric_type TEXT NOT NULL,
                    dimensions_hash TEXT NOT NULL,
                    value REAL NOT NULL,
                    dimensions_json TEXT NOT NULL,
                    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(source, account, date, metric_type, dimensions_hash)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS content (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source TEXT NOT NULL,
                    account TEXT NOT NULL DEFAULT 'default',
                    content_id TEXT NOT NULL,
                    content_type TEXT NOT NULL,
                    url TEXT,
                    title TEXT,
                    created_at TIMESTAMP,
                    data_json TEXT NOT NULL,
                    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(source, account, content_id)
                )
            """)
            conn.commit()
        finally:
            conn.close()

    def _dimensions_hash(self, dimensions: dict) -> str:
        """Create hash of dimensions for unique constraint."""
        return hashlib.md5(
            json.dumps(dimensions, sort_keys=True).encode()
        ).hexdigest()

    def get_metrics(
        self,
        source: str,
        start_date: date,
        end_date: date,
        account: str = "default",
        max_age_hours: int = 1
    ) -> List[Metric]:
        """Fetch cached metrics if fresh enough.

        Now filters by account so different profiles don't share cache.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("""
            SELECT source, date, metric_type, value, dimensions_json, account
            FROM metrics
            WHERE source = ?
            AND account = ?
            AND date >= ?
            AND date <= ?
            AND fetched_at >= datetime('now', ?)
        """, (
            source,
            account,
            start_date.isoformat(),
            end_date.isoformat(),
            f'-{max_age_hours} hours',
        ))

        metrics = []
        for row in cursor.fetchall():
            metrics.append(Metric(
                source=row[0],
                date=date.fromisoformat(row[1]),
                metric_type=row[2],
                value=row[3],
                dimensions=json.loads(row[4]),
                account=row[5],
            ))
        conn.close()
        return metrics

    def set_metrics(self, metrics: List[Metric]):
        """Store metrics in cache with account tracking."""
        conn = sqlite3.connect(self.db_path)
        for m in metrics:
            conn.execute("""
                INSERT OR REPLACE INTO metrics
                (source, account, date, metric_type, dimensions_hash, value, dimensions_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                m.source,
                m.account,
                m.date.isoformat(),
                m.metric_type,
                self._dimensions_hash(m.dimensions),
                m.value,
                json.dumps(m.dimensions)
            ))
        conn.commit()
        conn.close()
