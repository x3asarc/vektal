"""
Unit tests for convention checker guardrails.
"""

from src.graph.convention_checker import check_against_conventions, load_default_conventions


def test_check_against_conventions_flags_conflicts():
    conventions = [
        {
            "rule": "Do not bypass gates except PhaseManager emergency protocol.",
            "scope": "global",
            "enforcement": "advisory",
        }
    ]

    violations = check_against_conventions(
        "Do not bypass gates except PhaseManager emergency protocol.",
        conventions=conventions,
        threshold=0.7,
    )

    assert len(violations) == 1
    assert "bypass gates" in violations[0].convention.lower()


def test_check_against_conventions_no_conflict():
    conventions = [
        {
            "rule": "Use exact dependency pins in requirements.",
            "scope": "global",
            "enforcement": "advisory",
        }
    ]

    violations = check_against_conventions(
        "Add richer API docs and examples.",
        conventions=conventions,
        threshold=0.7,
    )

    assert violations == []


def test_load_default_conventions_returns_structured_items():
    conventions = load_default_conventions(limit=3)
    assert len(conventions) <= 3
    if conventions:
        assert "rule" in conventions[0]
        assert "scope" in conventions[0]
        assert "enforcement" in conventions[0]
