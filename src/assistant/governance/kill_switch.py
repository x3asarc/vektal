"""Kill-switch resolution and fail-closed mutation gate enforcement."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import or_

from src.models import AssistantKillSwitch


@dataclass(frozen=True)
class KillSwitchDecision:
    is_blocked: bool
    scope_kind: str | None
    mode: str | None
    switch_id: int | None
    reason: str | None
    metadata: dict

    def to_dict(self) -> dict:
        return {
            "is_blocked": self.is_blocked,
            "scope_kind": self.scope_kind,
            "mode": self.mode,
            "switch_id": self.switch_id,
            "reason": self.reason,
            "metadata": self.metadata,
        }


class KillSwitchBlockedError(Exception):
    """Raised when mutation execution is blocked by kill-switch policy."""

    def __init__(self, *, decision: KillSwitchDecision, action_name: str):
        super().__init__(decision.reason or "Execution paused by kill-switch.")
        self.decision = decision
        self.action_name = action_name
        self.error_type = "kill-switch-active"
        self.title = "Execution Paused"
        self.detail = (
            f"Mutation '{action_name}' is blocked by {decision.scope_kind or 'unknown'} kill-switch."
        )
        self.status = 503
        self.extensions = {
            "kill_switch": decision.to_dict(),
        }


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _active_query(*, scope_kind: str, store_id: int | None = None):
    query = AssistantKillSwitch.query.filter(
        AssistantKillSwitch.scope_kind == scope_kind,
        AssistantKillSwitch.is_enabled.is_(True),
        AssistantKillSwitch.effective_at <= _now(),
        or_(AssistantKillSwitch.expires_at.is_(None), AssistantKillSwitch.expires_at > _now()),
    )
    if scope_kind == "tenant":
        query = query.filter(AssistantKillSwitch.store_id == store_id)
    else:
        query = query.filter(AssistantKillSwitch.store_id.is_(None))
    return query.order_by(AssistantKillSwitch.effective_at.desc(), AssistantKillSwitch.id.desc())


def get_kill_switch_decision(*, store_id: int | None) -> KillSwitchDecision:
    """
    Resolve kill-switch enforcement decision.

    Priority: global switch first, then tenant-scoped switch.
    """
    global_switch = _active_query(scope_kind="global").first()
    if global_switch is not None:
        return KillSwitchDecision(
            is_blocked=True,
            scope_kind="global",
            mode=global_switch.mode,
            switch_id=global_switch.id,
            reason=global_switch.reason,
            metadata=global_switch.metadata_json or {},
        )

    if store_id is not None:
        tenant_switch = _active_query(scope_kind="tenant", store_id=store_id).first()
        if tenant_switch is not None:
            return KillSwitchDecision(
                is_blocked=True,
                scope_kind="tenant",
                mode=tenant_switch.mode,
                switch_id=tenant_switch.id,
                reason=tenant_switch.reason,
                metadata=tenant_switch.metadata_json or {},
            )

    return KillSwitchDecision(
        is_blocked=False,
        scope_kind=None,
        mode=None,
        switch_id=None,
        reason=None,
        metadata={},
    )


def assert_mutation_allowed(*, store_id: int | None, action_name: str) -> KillSwitchDecision:
    """Raise when an active kill-switch blocks mutation execution."""
    decision = get_kill_switch_decision(store_id=store_id)
    if decision.is_blocked:
        raise KillSwitchBlockedError(decision=decision, action_name=action_name)
    return decision

