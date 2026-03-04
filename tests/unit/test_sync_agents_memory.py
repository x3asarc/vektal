from __future__ import annotations

from scripts.memory.sync_agents_memory import (
    _load_contract_from_design,
    _render_memory_contract,
    _upsert_memory_section,
)


def test_memory_contract_render_and_upsert():
    design = "\n".join(
        [
            "WORKING MEMORY",
            "Location: .memory/working/{session_id}.json",
            "Scope: Session only",
            "TTL: 24h",
            "SHORT-TERM MEMORY",
            "Location: .memory/short-term/{date}.jsonl",
            "Scope: Day",
            "TTL: 7 days",
            "LONG-TERM MEMORY",
            "Location: .memory/long-term/",
            "Scope: Project",
            "TTL: Forever",
        ]
    )
    tiers = _load_contract_from_design(design)
    assert len(tiers) == 3
    assert tiers[1].location == ".memory/short-term/{date}.jsonl"
    assert tiers[2].ttl == "Forever"

    rendered = _render_memory_contract(tiers)
    assert "Session bootstrap: `python scripts/memory/session_start.py`" in rendered
    assert "location `.memory/working/{session_id}.json`" in rendered

    agents_text = "# Baseline\n\n## Artifact contract\n1. Sample.\n"
    with_section = _upsert_memory_section(agents_text, rendered)
    assert "<!-- MEMORY-CONTRACT:START -->" in with_section

    again = _upsert_memory_section(with_section, rendered)
    assert again == with_section
