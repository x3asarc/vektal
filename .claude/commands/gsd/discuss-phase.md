---
name: gsd:discuss-phase
description: Gather phase context through adaptive questioning before planning
argument-hint: "<phase>"
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
  - Grep
  - AskUserQuestion
---

<objective>
Extract implementation decisions that downstream agents need. Researcher and planner use PRE-CONTEXT-SCOPE.md plus CONTEXT.md to understand direction, what to investigate, and what choices are locked.

**How it works:**
1. Create a concise pre-context alignment memo (project-wide).
2. Ask user to pick route A/B/C (keep, keep+amend, alternate).
3. Analyze phase to identify gray areas (UI, UX, behavior, etc.).
4. Deep-dive selected areas with the user.
5. Create CONTEXT.md with decisions that guide research and planning.

**Output:** `{phase}-PRE-CONTEXT-SCOPE.md` and `{phase}-CONTEXT.md`
</objective>

<execution_context>
@./.claude/get-shit-done/workflows/discuss-phase.md
@./.claude/get-shit-done/templates/context.md
</execution_context>

<context>
Phase number: $ARGUMENTS (required)

**Load project state:**
@.planning/STATE.md

**Load roadmap:**
@.planning/ROADMAP.md
</context>

<process>
1. Validate phase number (error if missing or not in roadmap).
2. Check if CONTEXT.md exists (offer update/view/skip if yes).
3. **Pre-context scope gate (mandatory)** - create concise project-wide alignment memo:
   - completed phases
   - planned/active phases
   - hard facts from roadmap/state/project
   - 3 explicit direction options (each includes scope now, defers, hard-fact basis, and tradeoff)
4. Ask user to choose route from explicit options (not generic keep/amend/alternate labels).
5. **Analyze phase** - identify domain and generate phase-specific gray areas.
6. **Present gray areas** - multi-select: which to discuss? (no skip option).
7. **Deep-dive each area** - 4 questions per area, then offer more/next.
8. **Question gate check (mandatory)** - do not write context until at least 4 explicit user answers are captured.
9. **Write CONTEXT.md** - sections match areas discussed and include Discussion Evidence.
10. Offer next steps (research or plan).

**CRITICAL: Scope guardrail**
- Phase boundary from ROADMAP.md is fixed.
- Pre-context remains high-level only (no execution waves, no low-level architecture details).
- Pre-context choices must be explicit and evidence-backed; generic labels without concrete direction are invalid.
- Discussion clarifies HOW to implement, not WHETHER to add more.
- If user suggests new capabilities: "That is its own phase. I will note it for later."
- Capture deferred ideas - do not lose them, do not act on them.

**Domain-aware gray areas:**
Gray areas depend on what is being built. Analyze phase goal:
- Something users SEE -> layout, density, interactions, states
- Something users CALL -> responses, errors, auth, versioning
- Something users RUN -> output format, flags, modes, error handling
- Something users READ -> structure, tone, depth, flow
- Something being ORGANIZED -> criteria, grouping, naming, exceptions

Generate 3-4 phase-specific gray areas, not generic categories.

**Probing depth:**
- Ask 4 questions per area before checking.
- "More questions about [area], or move to next?"
- If more -> ask 4 more, check again.
- After all areas -> "Ready to create context?"

**Non-negotiable context gate:**
- No assumptions-only context creation.
- Must record at least 4 explicit user answers before writing CONTEXT.md.

**Do NOT ask about (Claude handles these):**
- Technical implementation
- Architecture choices
- Performance concerns
- Scope expansion
</process>

<success_criteria>
- PRE-CONTEXT-SCOPE created and remains concise/high-level.
- User explicitly selected A/B/C route before context drafting.
- Gray areas identified through intelligent analysis.
- User chose which areas to discuss.
- Each selected area explored until satisfied.
- Scope creep redirected to deferred ideas.
- CONTEXT.md captures decisions, not vague vision.
- User knows next steps.
</success_criteria>
</phase>