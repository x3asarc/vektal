---
description: Pending actions for next session or continuation. Updated at session end.
---

## Next Steps

**Completed This Session:**
- [x] Resolve Gemini hook naming conflict (`PreToolUse` -> `BeforeTool`).
- [x] Document provider-specific hook naming in project conventions and gotchas.
- [x] Reinforce 'No Drift' behavioral policy in agent memory.
- [x] Preliminary investigation into `TaskCreate`/`TaskUpdate` hook errors.

**Near-term:**
- [ ] Root cause the `PreToolUse:TaskCreate` and `PostToolUse:TaskUpdate` hook errors.
- [ ] Verify if internal Letta Code tools have implicit hooks causing failures on Windows.
- [ ] Test the hardened OODA loop on a real Dashboard change.
- [ ] Document the cross-platform hook sync protocol in the project wiki.

**Future Considerations:**
- Multi-browser visual audit (Firefox, Safari).
- Advanced CSS variable comparison in audit script.
- Automated regression detection against "Gold Standard" screenshots.
