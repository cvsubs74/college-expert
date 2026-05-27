# Backlog (local mode)

> **Note:** This project is currently in **`github` mode** (see `.claude/harness-mode.json`). The authoritative backlog lives on GitHub Issues — this file is the template/skeleton, not the active source of truth.
>
> To switch this project to local-mode tracking: `/init-mode local`.
>
> To use this template in another project, copy `harness/backlog.md` plus `.claude/skills/*` and `.claude/commands/init-mode.md` over, then run `/init-mode local` in the new project.

---

Append-only task list. The harness reads this in local mode the same way it reads GitHub Issues in github mode.

Format per entry:

```
## T-NNN — <Title>
- Type: story | bug | spike | epic
- Priority: P0 | P1 | P2
- Area: <one-word>
- Status: open | in-progress | in-review | done
- Worktree: <path or "-">
- Filed: YYYY-MM-DD by <git user>

### Summary
<1-3 sentences>

### Acceptance criteria
- [ ] <testable bullet 1>
- [ ] <testable bullet 2>

### Notes
<optional>
```

T-NNN IDs are zero-padded sequential (T-001, T-002, ..., T-099, T-100, ...). Append at the bottom; never reorder. Closed tasks (`Status: done`) stay in place for audit-trail.

The same evidence discipline as GitHub mode applies:

- Only the **tester** ticks acceptance boxes, after evidence.
- Only the **product-manager** assigns `Priority:`.
- The **implementer** flips `Status:` from `open` → `in-progress` on pickup.
- `/ship` flips `Status: in-progress` → `Status: done` after PR merge.

For bug filings, see `.claude/skills/file-bug/SKILL.md` (the local-mode block).

---

<!-- entries appended below -->
