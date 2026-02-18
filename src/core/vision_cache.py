"""
Vision AI Alt Text Cache
Stores generated alt text indexed by image URL hash to minimize API costs.
"""
import hashlib
import sqlite3
import json
import os
import logging
from datetime import datetime, date
from typing import Optional, Dict
from src.core.paths import VISION_CACHE_DB


logger = logging.getLogger(__name__)


class BudgetExceededError(RuntimeError):
    """Raised when the configured daily vision AI budget is exceeded."""


class VisionAltTextCache:
    """SQLite-based cache for vision-generated alt text."""

    def __init__(self, db_path: Optional[str] = None, daily_budget_eur: Optional[float] = None):
        self.db_path = db_path or os.getenv("VISION_AI_CACHE_DB") or VISION_CACHE_DB
        self.daily_budget_eur = daily_budget_eur
        if self.daily_budget_eur is None:
            self.daily_budget_eur = self._parse_float_env("VISION_AI_DAILY_BUDGET_EUR")
        self.monthly_budget_eur = self._parse_float_env("VISION_AI_MONTHLY_BUDGET_EUR")
        self._initialize_db()

    @staticmethod
    def _parse_float_env(name: str) -> Optional[float]:
        value = os.getenv(name)
        if value is None or value == "":
            return None
        try:
            return float(value)
        except ValueError:
            logger.warning("Invalid float for %s: %s", name, value)
            return None

    def _initialize_db(self):
        """Create tables if not exist."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Cache table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS image_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                image_hash TEXT UNIQUE NOT NULL,
                image_url TEXT NOT NULL,
                alt_text TEXT NOT NULL,
                product_context TEXT,
                model_used TEXT DEFAULT 'google/gemini-flash-1.5-8b',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                use_count INTEGER DEFAULT 1
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_image_hash ON image_cache(image_hash)")

        # Usage tracking table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS api_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATE NOT NULL,
                images_processed INTEGER DEFAULT 0,
                cache_hits INTEGER DEFAULT 0,
                api_calls INTEGER DEFAULT 0,
                estimated_cost_eur REAL DEFAULT 0.0,
                UNIQUE(date)
            )
        """)

        conn.commit()
        conn.close()

    def _hash_image_url(self, image_url: str) -> str:
        """Generate MD5 hash of image URL."""
        return hashlib.md5(image_url.encode('utf-8')).hexdigest()

    def ensure_within_budget(self):
        """Raise BudgetExceededError if today's usage exceeds the configured budget."""
        if self.daily_budget_eur is not None:
            today_cost = self._get_today_cost()
            if today_cost is not None and today_cost >= self.daily_budget_eur:
                raise BudgetExceededError(
                    f"Daily vision AI budget exceeded: {today_cost:.4f} EUR >= {self.daily_budget_eur:.4f} EUR"
                )
        if self.monthly_budget_eur is not None:
            month_cost = self._get_month_cost()
            if month_cost is not None and month_cost >= self.monthly_budget_eur:
                raise BudgetExceededError(
                    f"Monthly vision AI budget exceeded: {month_cost:.4f} EUR >= {self.monthly_budget_eur:.4f} EUR"
                )

    def _get_today_cost(self) -> Optional[float]:
        today = datetime.now().date()
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT estimated_cost_eur FROM api_usage WHERE date = ?
        """, (today,))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else 0.0

    def _get_month_cost(self) -> Optional[float]:
        month_key = datetime.now().strftime("%Y-%m")
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT SUM(estimated_cost_eur) FROM api_usage
            WHERE strftime('%Y-%m', date) = ?
        """, (month_key,))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row and row[0] is not None else 0.0

    def get(self, image_url: str) -> Optional[str]:
        """Get cached alt text for image URL (returns None if not cached)."""
        image_hash = self._hash_image_url(image_url)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT alt_text FROM image_cache WHERE image_hash = ?
        """, (image_hash,))

        result = cursor.fetchone()

        if result:
            # Update usage stats
            cursor.execute("""
                UPDATE image_cache
                SET last_used_at = CURRENT_TIMESTAMP, use_count = use_count + 1
                WHERE image_hash = ?
            """, (image_hash,))
            conn.commit()

            # Track cache hit
            self._track_cache_hit(cursor)
            conn.commit()

        conn.close()
        return result[0] if result else None

    def set(self, image_url: str, alt_text: str, product_context: Dict, model: str):
        """Store generated alt text in cache."""
        image_hash = self._hash_image_url(image_url)
        context_json = json.dumps(product_context or {}, default=str)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO image_cache
            (image_hash, image_url, alt_text, product_context, model_used)
            VALUES (?, ?, ?, ?, ?)
        """, (image_hash, image_url, alt_text, context_json, model))

        # Track API call
        self._track_api_call(cursor, cost_eur=0.000014)  # Gemini Flash 1.5 cost

        conn.commit()
        conn.close()

    def _track_cache_hit(self, cursor):
        """Track daily cache hit."""
        today = datetime.now().date()
        cursor.execute("""
            INSERT INTO api_usage (date, images_processed, cache_hits)
            VALUES (?, 1, 1)
            ON CONFLICT(date) DO UPDATE SET
                images_processed = images_processed + 1,
                cache_hits = cache_hits + 1
        """, (today,))

    def _track_api_call(self, cursor, cost_eur: float):
        """Track daily API call."""
        today = datetime.now().date()
        cursor.execute("""
            INSERT INTO api_usage (date, images_processed, api_calls, estimated_cost_eur)
            VALUES (?, 1, 1, ?)
            ON CONFLICT(date) DO UPDATE SET
                images_processed = images_processed + 1,
                api_calls = api_calls + 1,
                estimated_cost_eur = estimated_cost_eur + ?
        """, (today, cost_eur, cost_eur))
        self._enforce_budget(cursor)

    def _enforce_budget(self, cursor):
        if self.daily_budget_eur is not None:
            today = datetime.now().date()
            cursor.execute("""
                SELECT estimated_cost_eur FROM api_usage WHERE date = ?
            """, (today,))
            row = cursor.fetchone()
            if row and row[0] is not None and row[0] > self.daily_budget_eur:
                logger.error(
                    "Daily vision AI budget exceeded: %.4f EUR > %.4f EUR",
                    row[0],
                    self.daily_budget_eur,
                )
                raise BudgetExceededError(
                    f"Daily vision AI budget exceeded: {row[0]:.4f} EUR > {self.daily_budget_eur:.4f} EUR"
                )

        if self.monthly_budget_eur is not None:
            month_key = datetime.now().strftime("%Y-%m")
            cursor.execute("""
                SELECT SUM(estimated_cost_eur) FROM api_usage
                WHERE strftime('%Y-%m', date) = ?
            """, (month_key,))
            row = cursor.fetchone()
            month_total = row[0] if row and row[0] is not None else 0.0
            if month_total > self.monthly_budget_eur:
                logger.error(
                    "Monthly vision AI budget exceeded: %.4f EUR > %.4f EUR",
                    month_total,
                    self.monthly_budget_eur,
                )
                raise BudgetExceededError(
                    f"Monthly vision AI budget exceeded: {month_total:.4f} EUR > {self.monthly_budget_eur:.4f} EUR"
                )

    def get_stats(self) -> Dict:
        """Get usage statistics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                SUM(images_processed) as total_processed,
                SUM(cache_hits) as total_cache_hits,
                SUM(api_calls) as total_api_calls,
                SUM(estimated_cost_eur) as total_cost
            FROM api_usage
        """)

        row = cursor.fetchone()
        conn.close()

        total_processed, cache_hits, api_calls, total_cost = row or (0, 0, 0, 0.0)

        return {
            "total_processed": total_processed or 0,
            "cache_hits": cache_hits or 0,
            "api_calls": api_calls or 0,
            "cache_hit_rate": (cache_hits / total_processed) if total_processed else 0,
            "total_cost_eur": total_cost or 0.0
        }

    def get_stats_for_date(self, date_value: Optional[date] = None) -> Dict:
        """Get usage statistics for a specific date (defaults to today)."""
        if date_value is None:
            date_value = datetime.now().date()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                images_processed,
                cache_hits,
                api_calls,
                estimated_cost_eur
            FROM api_usage
            WHERE date = ?
        """, (date_value,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return {
                "date": date_value,
                "processed": 0,
                "cache_hits": 0,
                "api_calls": 0,
                "cache_hit_rate": 0.0,
                "cost_eur": 0.0
            }

        processed, cache_hits, api_calls, cost = row
        return {
            "date": date_value,
            "processed": processed or 0,
            "cache_hits": cache_hits or 0,
            "api_calls": api_calls or 0,
            "cache_hit_rate": (cache_hits / processed) if processed else 0,
            "cost_eur": cost or 0.0
        }
