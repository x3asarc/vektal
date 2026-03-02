"""Shared types and constants for Phase 15 sandbox verification."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

STATUS_GREEN = "GREEN"
STATUS_YELLOW = "YELLOW"
STATUS_RED = "RED"
STATUS_SKIP = "SKIP"

GATE_ORDER = [
    "syntax",
    "type",
    "unit",
    "contract",
    "governance",
    "rollback",
]

GATE_TIMEOUT_SECONDS = {
    "syntax": 5,
    "type": 30,
    "unit": 120,
    "contract": 30,
    "governance": 30,
    "rollback": 30,
}


@dataclass
class VerificationGate:
    name: str
    status: str = "PENDING"
    message: Optional[str] = None
    duration_ms: float = 0.0


@dataclass
class SandboxResult:
    run_id: str
    success: bool
    gates: list[VerificationGate]
    logs: str = ""
    error_details: Optional[str] = None
    revert_plan_valid: bool = False
