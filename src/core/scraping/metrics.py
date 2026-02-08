"""
Scraping Metrics Tracking

Tracks success rates, failure patterns, and performance metrics
for adaptive learning and optimization.
"""

import logging
from collections import defaultdict, Counter
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class FailureReason(str, Enum):
    """Categorized failure reasons for learning."""
    SELECTOR_FAILED = "SELECTOR_FAILED"  # Element not found
    TIMEOUT = "TIMEOUT"  # Page load timeout
    RATE_LIMIT = "RATE_LIMIT"  # 429 or rate limit message
    NETWORK_ERROR = "NETWORK_ERROR"  # Connection issues
    VALIDATION_FAILED = "VALIDATION_FAILED"  # SKU mismatch, placeholder image
    UNKNOWN = "UNKNOWN"  # Other errors


@dataclass
class ScrapeAttempt:
    """Individual scrape attempt record."""
    timestamp: datetime
    vendor_name: str
    sku: str
    success: bool
    failure_reason: Optional[FailureReason] = None
    retry_count: int = 0
    duration_ms: int = 0


class ScrapeMetrics:
    """
    Track scraping success rates and failure patterns.

    Session-based in-memory tracking for adaptive learning.
    Provides statistics for overall and per-vendor performance.

    Usage:
        metrics = ScrapeMetrics()
        metrics.track_result('vendor1', 'SKU1', True)
        success_rate = metrics.get_success_rate('vendor1')
    """

    def __init__(self):
        """Initialize empty metrics tracking."""
        # All attempts in chronological order
        self._attempts: list[ScrapeAttempt] = []

        # Per-vendor statistics (computed on demand)
        self._vendor_cache: dict[str, dict] = {}

        # Session start time
        self._session_start = datetime.utcnow()

    def track_result(
        self,
        vendor_name: str,
        sku: str,
        success: bool,
        failure_reason: Optional[str] = None,
        retry_count: int = 0,
        duration_ms: int = 0
    ) -> None:
        """
        Record a scrape attempt.

        Args:
            vendor_name: Vendor identifier
            sku: Product SKU
            success: True if scrape succeeded
            failure_reason: Categorized failure reason (if failed)
            retry_count: Number of retries performed
            duration_ms: Total scrape duration
        """
        # Convert failure reason to enum
        failure_enum = None
        if failure_reason:
            try:
                failure_enum = FailureReason(failure_reason)
            except ValueError:
                # Unknown reason
                failure_enum = FailureReason.UNKNOWN
                logger.warning(f"Unknown failure reason: {failure_reason}")

        attempt = ScrapeAttempt(
            timestamp=datetime.utcnow(),
            vendor_name=vendor_name,
            sku=sku,
            success=success,
            failure_reason=failure_enum,
            retry_count=retry_count,
            duration_ms=duration_ms
        )

        self._attempts.append(attempt)

        # Invalidate vendor cache
        if vendor_name in self._vendor_cache:
            del self._vendor_cache[vendor_name]

    def get_success_rate(self, vendor_name: Optional[str] = None) -> float:
        """
        Calculate success rate.

        Args:
            vendor_name: Optional vendor filter (None = overall)

        Returns:
            Success rate as float 0.0-1.0 (1.0 if no attempts)
        """
        attempts = self._get_vendor_attempts(vendor_name)

        if not attempts:
            return 1.0  # Optimistic default

        successful = sum(1 for a in attempts if a.success)
        return successful / len(attempts)

    def get_failure_breakdown(
        self,
        vendor_name: Optional[str] = None
    ) -> dict[str, int]:
        """
        Get count of failures by reason.

        Args:
            vendor_name: Optional vendor filter

        Returns:
            Dict mapping failure reason to count
        """
        attempts = self._get_vendor_attempts(vendor_name)
        failures = [a for a in attempts if not a.success and a.failure_reason]

        breakdown = Counter(f.failure_reason.value for f in failures)
        return dict(breakdown)

    def get_vendor_stats(self) -> dict[str, dict]:
        """
        Get per-vendor statistics.

        Returns:
            Dict mapping vendor name to stats:
                - total_attempts: int
                - successful: int
                - failed: int
                - success_rate: float
                - most_common_failure: Optional[str]
                - avg_retry_count: float
                - avg_duration_ms: float
        """
        vendors = set(a.vendor_name for a in self._attempts)

        stats = {}
        for vendor in vendors:
            if vendor not in self._vendor_cache:
                self._vendor_cache[vendor] = self._compute_vendor_stats(vendor)
            stats[vendor] = self._vendor_cache[vendor]

        return stats

    def _compute_vendor_stats(self, vendor_name: str) -> dict:
        """Compute statistics for a specific vendor."""
        attempts = self._get_vendor_attempts(vendor_name)

        if not attempts:
            return {
                'total_attempts': 0,
                'successful': 0,
                'failed': 0,
                'success_rate': 1.0,
                'most_common_failure': None,
                'avg_retry_count': 0.0,
                'avg_duration_ms': 0.0
            }

        successful = [a for a in attempts if a.success]
        failed = [a for a in attempts if not a.success]

        # Most common failure reason
        failures_with_reason = [a for a in failed if a.failure_reason]
        most_common = None
        if failures_with_reason:
            failure_counts = Counter(f.failure_reason.value for f in failures_with_reason)
            most_common = failure_counts.most_common(1)[0][0]

        # Averages
        avg_retries = sum(a.retry_count for a in attempts) / len(attempts)
        avg_duration = sum(a.duration_ms for a in attempts) / len(attempts)

        return {
            'total_attempts': len(attempts),
            'successful': len(successful),
            'failed': len(failed),
            'success_rate': len(successful) / len(attempts),
            'most_common_failure': most_common,
            'avg_retry_count': round(avg_retries, 2),
            'avg_duration_ms': round(avg_duration, 1)
        }

    def get_recent_attempts(
        self,
        vendor_name: str,
        limit: int = 10
    ) -> list[ScrapeAttempt]:
        """
        Get recent attempts for a vendor.

        Args:
            vendor_name: Vendor to filter
            limit: Maximum attempts to return

        Returns:
            List of recent attempts (newest first)
        """
        vendor_attempts = [
            a for a in self._attempts
            if a.vendor_name == vendor_name
        ]
        return list(reversed(vendor_attempts[-limit:]))

    def export_session_report(self) -> str:
        """
        Export markdown-formatted session report.

        Returns:
            Markdown report with statistics
        """
        duration = (datetime.utcnow() - self._session_start).total_seconds()
        hours, remainder = divmod(int(duration), 3600)
        minutes, seconds = divmod(remainder, 60)

        lines = [
            "# Scraping Session Report",
            "",
            f"**Session Duration:** {hours}h {minutes}m {seconds}s",
            f"**Session Start:** {self._session_start.isoformat()}",
            "",
            "## Overall Statistics",
            "",
            f"- **Total Attempts:** {len(self._attempts)}",
            f"- **Success Rate:** {self.get_success_rate():.1%}",
            ""
        ]

        # Failure breakdown
        breakdown = self.get_failure_breakdown()
        if breakdown:
            lines.append("### Failure Breakdown")
            lines.append("")
            for reason, count in sorted(breakdown.items(), key=lambda x: x[1], reverse=True):
                lines.append(f"- **{reason}:** {count}")
            lines.append("")

        # Per-vendor stats
        vendor_stats = self.get_vendor_stats()
        if vendor_stats:
            lines.append("## Per-Vendor Statistics")
            lines.append("")
            lines.append("| Vendor | Attempts | Success Rate | Failed | Most Common Failure |")
            lines.append("|--------|----------|--------------|--------|---------------------|")

            for vendor, stats in sorted(vendor_stats.items()):
                failure = stats['most_common_failure'] or 'N/A'
                lines.append(
                    f"| {vendor} | {stats['total_attempts']} | "
                    f"{stats['success_rate']:.1%} | {stats['failed']} | {failure} |"
                )

        return "\n".join(lines)

    def _get_vendor_attempts(self, vendor_name: Optional[str]) -> list[ScrapeAttempt]:
        """Filter attempts by vendor (or all if None)."""
        if vendor_name is None:
            return self._attempts
        return [a for a in self._attempts if a.vendor_name == vendor_name]

    def reset(self) -> None:
        """Clear all tracked metrics."""
        self._attempts.clear()
        self._vendor_cache.clear()
        self._session_start = datetime.utcnow()
