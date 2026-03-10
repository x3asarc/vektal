"""
scripts/agents/pipeline.py — Forensic Partnership pipeline runner.

Runs the full Commander → Watson → Lestrade (if needed) → Bundle → Lead chain
and renders each agent's output as plain conversational text.

Usage:
    python scripts/agents/pipeline.py --task "description of task"
    python scripts/agents/pipeline.py --task "..." --context "pre-seeded oracle data"
    python scripts/agents/pipeline.py --task "..." --lead project-lead
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.agents.invoke import invoke  # noqa: E402


# ── Prompt templates ─────────────────────────────────────────────────────────

COMMANDER_PROMPT = """\
Task: {task}

Run P-LOAD mentally from context. Respond in plain conversational text — 3-5 sentences max.
State:
- Your proposed scope tier (MICRO / STANDARD / EXTENDED) and why
- Which Lead you're routing to and why
- Your proposed loop_budget
- That you've spawned Watson blind

No JSON. No headers. Just speak as Commander."""

WATSON_PROMPT = """\
Task for blind review (you have NOT seen Commander's routing): {task}

Context: {context}

Respond in plain conversational text — 4-6 sentences max.
State:
- Whether you AGREE or DISAGREE with STANDARD scope (and why in one sentence)
- Your loop_budget verdict and why
- The single biggest risk you see
- Your LOCK signal: APPROVED or CHALLENGED

No JSON. No headers. No tool calls. Reason from context only."""

LESTRADE_PROMPT = """\
Arbitrate this dispute in plain text — 2-3 sentences max.

Task: {task}
Commander proposed: {commander_budget}
Watson proposed: {watson_budget}
Watson reasoning: {watson_reasoning}

Give your binding verdict and one-sentence rationale. State the final loop_budget clearly."""

BUNDLE_PROMPT = """\
Configure the execution package in plain text — 3-4 sentences max.

Task: {task}
Scope: {scope}
Loop budget: {loop_budget} (Lestrade binding: {lestrade_binding})
Lead: {lead}
Watson conditions: {watson_conditions}

Describe what you've configured for the Lead. No JSON."""

LEAD_PROMPT = """\
Architectural sign-off in plain text — 2-3 sentences max.

Task: {task}
Bundle config: loop_budget={loop_budget}, Lead={lead}
Watson conditions: {watson_conditions}

Give GO or NO-GO with a single sentence rationale."""


# ── Simple extraction helpers ─────────────────────────────────────────────────

def _extract(text: str, keywords: list[str], default: str) -> str:
    tl = text.lower()
    for kw in keywords:
        if kw in tl:
            return kw
    return default


def _budget_from_text(text: str, default: int) -> int:
    import re
    m = re.search(r"loop.budget[=:\s]+(\d)", text, re.IGNORECASE)
    if m:
        return int(m.group(1))
    for n in ["three", "3"]:
        if n in text.lower():
            return 3
    for n in ["two", "2"]:
        if n in text.lower():
            return 2
    return default


def _print_agent(name: str, color_code: str, text: str) -> None:
    RESET = "\033[0m"
    BOLD  = "\033[1m"
    print(f"\n{BOLD}{color_code}── {name} {'─' * (50 - len(name))}{RESET}")
    print(text.strip())


# ── Pipeline ─────────────────────────────────────────────────────────────────

def run_pipeline(task: str, context: str = "", lead_override: str = "") -> None:
    GOLD    = "\033[33m"
    BLUE    = "\033[34m"
    RED     = "\033[31m"
    GREEN   = "\033[32m"
    MAGENTA = "\033[35m"
    CYAN    = "\033[36m"

    print("\n\033[1m🔍 Forensic Partnership Pipeline\033[0m")
    print(f"Task: {task[:80]}{'...' if len(task) > 80 else ''}\n")

    # ── Commander ────────────────────────────────────────────────────────────
    print("Invoking Commander (grok-3)...", end=" ", flush=True)
    commander_out = invoke(
        agent="commander",
        message=COMMANDER_PROMPT.format(task=task),
        context=context,
        max_tokens=400,
    )
    print("done")
    _print_agent("Commander", GOLD, commander_out)

    scope = _extract(commander_out, ["extended", "standard", "micro"], "standard").upper()
    commander_budget = _budget_from_text(commander_out, 2)
    lead = lead_override or _extract(
        commander_out,
        ["infrastructure-lead", "engineering-lead", "project-lead",
         "forensic-lead", "design-lead"],
        "infrastructure-lead"
    )

    # ── Watson (blind) ────────────────────────────────────────────────────────
    print("\nInvoking Watson blind (claude-opus-4-6)...", end=" ", flush=True)
    watson_out = invoke(
        agent="watson",
        message=WATSON_PROMPT.format(task=task, context=context or "No additional context provided."),
        max_tokens=500,
    )
    print("done")
    _print_agent("Watson", BLUE, watson_out)

    watson_budget = _budget_from_text(watson_out, commander_budget)
    watson_approved = "challenged" not in watson_out.lower()
    watson_conditions = ""
    for line in watson_out.splitlines():
        if any(w in line.lower() for w in ["loop 1", "pre-flight", "verify", "before"]):
            watson_conditions += line.strip() + " "

    # ── Lestrade (only if budget differs) ────────────────────────────────────
    lestrade_binding = False
    final_budget = commander_budget

    if watson_budget != commander_budget:
        print(f"\n⚖️  Budget disagreement ({commander_budget} vs {watson_budget}) — invoking Lestrade...", end=" ", flush=True)
        watson_reasoning = ""
        for line in watson_out.splitlines():
            if any(w in line.lower() for w in ["loop", "budget", "contingency", "risk", "cold"]):
                watson_reasoning += line.strip() + " "

        lestrade_out = invoke(
            agent="forensic-lead",
            message=LESTRADE_PROMPT.format(
                task=task,
                commander_budget=commander_budget,
                watson_budget=watson_budget,
                watson_reasoning=watson_reasoning[:300],
            ),
            max_tokens=200,
        )
        print("done")
        _print_agent("Lestrade (arbitrator)", RED, lestrade_out)
        final_budget = _budget_from_text(lestrade_out, watson_budget)
        lestrade_binding = True
    else:
        final_budget = watson_budget

    # ── Bundle ───────────────────────────────────────────────────────────────
    print("\nInvoking Bundle (gemini-2.5-flash)...", end=" ", flush=True)
    bundle_out = invoke(
        agent="bundle",
        message=BUNDLE_PROMPT.format(
            task=task,
            scope=scope,
            loop_budget=final_budget,
            lestrade_binding="YES" if lestrade_binding else "NO",
            lead=lead,
            watson_conditions=watson_conditions[:300] or "Standard pre-flight verification.",
        ),
        max_tokens=300,
    )
    print("done")
    _print_agent("Bundle", MAGENTA, bundle_out)

    # ── Project Lead sign-off ─────────────────────────────────────────────────
    print("\nInvoking Project Lead sign-off (gemini-2.5-flash)...", end=" ", flush=True)
    lead_out = invoke(
        agent="project-lead",
        message=LEAD_PROMPT.format(
            task=task,
            loop_budget=final_budget,
            lead=lead,
            watson_conditions=watson_conditions[:200] or "Standard verification.",
        ),
        max_tokens=150,
    )
    print("done")
    _print_agent("Project Lead", CYAN, lead_out)

    # ── Summary ───────────────────────────────────────────────────────────────
    go = "NO-GO" not in lead_out.upper()
    print(f"\n\033[1m{'✅ GO' if go else '🛑 NO-GO'} — {scope} · loop_budget={final_budget}"
          f"{' (Lestrade binding)' if lestrade_binding else ''} · Lead: {lead}\033[0m\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Forensic Partnership pipeline")
    parser.add_argument("--task", "-t", required=True, help="Task description")
    parser.add_argument("--context", "-c", default="", help="Pre-seeded oracle/state context")
    parser.add_argument("--lead", "-l", default="", help="Override lead agent")
    args = parser.parse_args()

    run_pipeline(task=args.task, context=args.context, lead_override=args.lead)


if __name__ == "__main__":
    main()
