# Pattern: aura-oracle is the read gateway — writes stay direct Cypher

**Promoted:** 2026-03-09
**Occurrences:** 3 (oracle design discussion, Commander LOAD wiring, Watson Casebook decision)
**Domain:** graph / architecture

## Pattern

All Aura graph reads flow through `aura-oracle` (`ask(domain, question, context)`).
No agent writes raw Cypher for discovery purposes.
Writes (TaskExecution, Casebook, BundleTemplate) stay as direct Cypher — oracle is read-only.
Exceptions: Watson Casebook reads use direct Cypher with git-entropy decay logic too specific for a generic block.

## Why It Works

- Schema evolution is isolated: add a block to oracle.py, all agents get it for free
- Domain profiles are declarative specs: "what context does this agent need?"
- Extending a profile = extending all agents that use that domain
- Read/write separation keeps oracle simple and side-effect-free

## Anti-pattern

Writing raw Cypher for discovery in agent specs. This creates drift when schema evolves.
Every ad-hoc query is a future maintenance burden.

## Evidence

- Commander LOAD step migration (2026-03-09): replaced 5 raw queries with `ask(domain="project")`
- oracle.py DOMAIN_PROFILES as declarative context spec
- Watson W-ORACLE action delegates to aura-oracle, not raw Cypher
