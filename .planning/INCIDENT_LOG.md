# Incident Log

## 2026-02-13 - GSD commit command incident chain

### Timeline

1. `704afbe` (`--help`) was created unintentionally while invoking `gsd-tools` commit help.
2. `3740bb1` reverted `704afbe` per user request to avoid retaining accidental payload.
3. `f66158b` reverted `3740bb1` per user request to restore all removed planning artifacts.

### What happened

- The accidental commit (`704afbe`) included a large staged planning/docs payload (multi-phase `.planning/*` files).
- A full revert of that commit removed all files introduced in that payload, which is expected `git revert` behavior.
- A revert-of-revert restored those artifacts exactly.

### Current state intention

- Keep a transparent, auditable history of the accidental commit and both corrective actions.
- Preserve restored planning artifacts while documenting the incident sequence.

### Commit references

- accidental: `704afbe`
- revert: `3740bb1`
- restore-all: `f66158b`
