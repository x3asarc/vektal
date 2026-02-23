"""
Convention guardrail checks for architectural suggestions.
"""

from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
import re
from typing import Dict, List, Optional


@dataclass
class ConventionViolation:
    convention: str
    confidence: float
    suggested_alternative: str


_CONVENTION_FILES = [Path("AGENTS.md"), Path("STANDARDS.md")]
_RULE_HINTS = ("must", "never", "required", "always", "cannot", "forbidden")


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, _normalize_text(a), _normalize_text(b)).ratio()


def _extract_candidate_rule(line: str) -> Optional[str]:
    stripped = line.strip()
    if not stripped:
        return None

    if stripped.startswith("- "):
        candidate = stripped[2:].strip()
    else:
        numbered = re.match(r"^\d+\.\s+(.*)$", stripped)
        if not numbered:
            return None
        candidate = numbered.group(1).strip()

    lowered = candidate.lower()
    if not any(hint in lowered for hint in _RULE_HINTS):
        return None
    return candidate


def load_default_conventions(limit: int = 10) -> List[Dict[str, str]]:
    conventions: List[Dict[str, str]] = []
    seen_rules = set()
    for source in _CONVENTION_FILES:
        if not source.exists():
            continue
        for raw in source.read_text(encoding="utf-8", errors="ignore").splitlines():
            rule = _extract_candidate_rule(raw)
            if not rule:
                continue
            normalized = _normalize_text(rule)
            if normalized in seen_rules:
                continue
            seen_rules.add(normalized)
            conventions.append(
                {
                    "rule": rule,
                    "scope": "global",
                    "enforcement": "advisory",
                    "examples": "",
                }
            )
            if len(conventions) >= limit:
                return conventions
    return conventions


def check_against_conventions(
    proposed_change: str,
    conventions: Optional[List[Dict[str, str]]] = None,
    threshold: float = 0.7,
) -> List[ConventionViolation]:
    """
    Return potential convention violations for a proposed architectural change.
    """
    if not proposed_change.strip():
        return []
    conventions = conventions if conventions is not None else load_default_conventions()
    violations: List[ConventionViolation] = []
    for item in conventions:
        rule = item.get("rule", "")
        if not rule:
            continue
        confidence = _similarity(proposed_change, rule)
        if confidence >= threshold:
            violations.append(
                ConventionViolation(
                    convention=rule,
                    confidence=confidence,
                    suggested_alternative=f"Align change with project convention: {rule[:120]}",
                )
            )
    return sorted(violations, key=lambda item: item.confidence, reverse=True)
