from __future__ import annotations

from src.assistant.context_broker import assemble_context


def test_graph_attempted_for_all_query_classes():
    queries = [
        "what triggers pre tool hook",
        "how to run memory materialization",
        "current health status of context system",
        "what is the memory schema version",
    ]
    for query in queries:
        bundle = assemble_context(query=query, graph_fetcher=lambda _q, _k: [])
        assert bundle.telemetry["graph_attempted"] is True


def test_fallback_reason_is_present_when_graph_not_used():
    bundle = assemble_context(query="status", graph_fetcher=lambda _q, _k: [])
    assert bundle.telemetry["graph_used"] is False
    assert bundle.telemetry["fallback_used"] is True
    assert bundle.telemetry["fallback_reason"] is not None


def test_token_cap_is_enforced():
    huge = ["token " * 200 for _ in range(40)]
    bundle = assemble_context(
        query="force long context",
        graph_fetcher=lambda _q, _k: huge,
        hard_cap_tokens=400,
    )
    assert int(bundle.telemetry["assembled_tokens"]) <= 400


def test_telemetry_fields_exist():
    bundle = assemble_context(query="what depends on what", graph_fetcher=lambda _q, _k: ["a -> b"])
    for field in [
        "graph_attempted",
        "graph_used",
        "fallback_used",
        "fallback_reason",
        "latency_ms",
        "assembled_tokens",
        "query_class",
        "target_tokens",
        "hard_cap_tokens",
        "compaction_applied",
    ]:
        assert field in bundle.telemetry

