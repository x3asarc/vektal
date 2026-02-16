"""Deterministic enrichment execution profiles."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EnrichmentProfile:
    """Execution profile contract for enrichment depth and cost."""

    name: str
    tier: str
    include_visual_oracle: bool
    include_second_opinion: bool
    include_multilingual_norm: bool
    max_retry_attempts: int


PROFILES: dict[str, EnrichmentProfile] = {
    "quick": EnrichmentProfile(
        name="quick",
        tier="tier_2",
        include_visual_oracle=False,
        include_second_opinion=False,
        include_multilingual_norm=False,
        max_retry_attempts=1,
    ),
    "standard": EnrichmentProfile(
        name="standard",
        tier="tier_2",
        include_visual_oracle=False,
        include_second_opinion=True,
        include_multilingual_norm=True,
        max_retry_attempts=2,
    ),
    "deep": EnrichmentProfile(
        name="deep",
        tier="tier_3",
        include_visual_oracle=True,
        include_second_opinion=True,
        include_multilingual_norm=True,
        max_retry_attempts=3,
    ),
}


def get_profile(profile_name: str) -> EnrichmentProfile:
    """Resolve profile by name with deterministic fallback to `standard`."""
    normalized = (profile_name or "").strip().lower()
    return PROFILES.get(normalized, PROFILES["standard"])

