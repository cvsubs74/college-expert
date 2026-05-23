# CLAUDE.md

This file provides guidance to [Claude Code](https://docs.anthropic.com/en/docs/claude-code) when working with code in this repository.

# College Counselor — Claude Code Agent Team

## Required cold-start reading

Before acting on any goal, load:

1. `ETHOS.md` — the three principles that override all other defaults: *Boil the Lake · Search Before Building · User Sovereignty*.
2. `SDLC.md` — branch naming, PR workflow, label scheme, commit conventions.
3. `docs/ARCHITECTURE.md` — system shape + change log.

If a doc is missing, that is a signal — propose creating it rather than working without it.

## Operating posture (must-know before any action)

- **Multi-agent team workflow.** This repo is driven by 7 specialist roles (PM, Triage, Dev, QA, Code Reviewer, DevOps, Designer) coordinated by the Team Lead — 8 contracts under `.claude/agents/`. Skills live under `.claude/skills/`; slash commands under `.claude/commands/`. Pick the right specialist via the `Agent` tool — don't write code directly when a Dev/QA/CR specialist is appropriate.
- **PRD → Design Doc → code.** New user-facing features require `docs/prd/PRD-<topic>.md` then `docs/design/DESIGN-<topic>.md` before implementation. Bug fixes, refactors, chores, and hotfixes skip the gate (see `SDLC.md` Step 0).
- **No direct commits to the default branch.** Every change goes through a PR; squash-merge after CI green + review.
- **Architecture doc currency.** Update `docs/ARCHITECTURE.md` + append a Change Log row whenever a change touches module shape, data flow, schema, or constraints.
- **Worktree hygiene.** Each specialist session creates its own `git worktree add` (e.g. `.worktrees/<task-id>`) off `origin/main`. Never reuse another session's worktree, and never edit inside the primary repo path — it's on whoever's branch.

## Coding discipline

Behavioral guidelines for code changes — bias toward caution over speed (use judgment on trivial tasks). Adapted from [karpathy/CLAUDE.md](https://github.com/multica-ai/andrej-karpathy-skills/blob/main/CLAUDE.md).

- **Think before coding.** State assumptions explicitly. If multiple interpretations exist, surface them — don't pick silently. If something is unclear, stop and name what's confusing rather than guessing. Push back when a simpler approach exists.
- **Simplicity first.** Minimum code that solves the problem. No features beyond what was asked, no abstractions for single-use code, no "flexibility" that wasn't requested, no error handling for impossible scenarios. If 200 lines could be 50, rewrite it. Ask: "would a senior engineer say this is overcomplicated?"
- **Surgical changes.** Touch only what the task requires. Don't "improve" adjacent code, comments, or formatting; don't refactor what isn't broken; match existing style even if you'd do it differently. Remove imports/variables your changes orphaned — leave pre-existing dead code alone (mention it, don't delete it). Every changed line should trace directly to the user's request.
- **Goal-driven execution.** Transform vague asks into verifiable success criteria before coding ("add validation" → "write tests for invalid inputs, then make them pass"; "fix the bug" → "write a test that reproduces it, then make it pass"). For multi-step work, state a brief plan with explicit verify-checks per step.
- **Boil the Lake.** AI-assisted coding makes the marginal cost of completeness near-zero. When the complete implementation costs minutes more than the shortcut — do the complete thing. See `ETHOS.md` for the full principle.

## Common commands

```bash
# Tests (pytest + bash integration suites)
./run_all_tests.sh
pytest tests/

# Lint / type check
# (no project-wide lint configured — CI runs shellcheck/markdown sanity)

# Dev server
./start_local.sh                 # local Cloud Functions + frontend
cd frontend && npm run dev       # frontend only (Vite)

# Deploy
./deploy.sh <function-name>      # individual cloud function
./deploy_frontend.sh             # Firebase Hosting
```

Always pass `--account cvsubs@gmail.com --project college-counselling-478115` to any raw `gcloud`/`firebase` invocation — the active default account on this machine is OneTrust.

## Architecture in one paragraph

Python 3.11 Cloud Functions Gen2 (us-east1) form the backend — `counselor_agent` is the read-side BFF that aggregates from `profile_manager_v2` and `knowledge_base_manager_universities_v2` before responding to chat/roadmap/college-fit requests; writes go directly from the frontend to `profile_manager_v2`. A React 19 + Vite SPA on Firebase Hosting (`frontend/`) talks to those functions; Firestore is the primary store. The legacy Elasticsearch cluster (`*_es` / `*_rag` variants) is offline — those functions remain deployed but are not exercised. Gemini Flash (via `google-genai` SDK) handles all LLM calls; Stripe + `payment_manager_v2` handles subscriptions. GCP project: `college-counselling-478115`; authoritative code under `cloud_functions/<service>/` and `agents/`. See `docs/ARCHITECTURE.md` for the full system shape, module map, and change log; per-feature docs under `docs/prd/` + `docs/design/`. Only the cloud functions listed in `project_live_components_scope` memory are reachable from the frontend — ignore legacy variants.

## Reusable tooling

- `deploy.sh` / `deploy_frontend.sh` — canonical deploy paths (with account/project pinning).
- `run_all_tests.sh`, `comprehensive_integration_test.sh`, `test_*.sh` — backend integration suites against deployed functions.
- `scripts/` — diagnostic + operational scripts (data fixes, KB ingestion, schema migrations).
- `cleanup_test_data.sh`, `setup_secrets.sh`, `setup_firebase_env.sh` — environment + cleanup helpers.
- `bin/merge-pr.sh`, `bin/bootstrap-labels.sh` — PR merge helper and GitHub label bootstrapper.

## Project skills & agent playbooks

Two surfaces for capturing what an agent learns on this project — used differently.

- **Agent playbooks** (`docs/playbooks/<agent>.md`) — lightweight per-agent scratchpad. Gotchas, env quirks, "last time I tried X it broke Y." Append freely, delete when stale. Read only by that agent.
- **Project skills** (`.claude/skills/<skill-name>/SKILL.md`) — a codifiable procedure with a checklist, shared across agents or invoked often enough that drift would hurt. Claude Code auto-discovers anything under `.claude/skills/`; follow the `SKILL.md` frontmatter pattern already used by `label-discipline`, `file-bug-issue`, `worktree-management`.

**Promote-to-skill rule.** If the same multi-step procedure shows up in 2+ playbooks, or one agent has performed it 3+ times the same way, lift it out into `.claude/skills/<name>/SKILL.md`. Until then, leave it in the playbook — skills cost more to author and clutter the available-skills list when overused. The `skill-maintenance` shared skill covers the authoring pattern (frontmatter, line cap, the agent-doc-PR pattern).

## Slash commands

Run these from the Claude Code prompt:

- `/onboard-team` — spawn the 8-agent team with the Team Lead in the driver's seat.
- `/office-hours` — six forcing questions before writing code; surfaces the real problem behind the framing.
- `/plan-review` — run CEO / engineering / design review lenses on a plan or design doc.
- `/investigate` — systematic root-cause debugging. No fixes without an investigation.
- `/ship` — sync, run tests, push, open a PR (manual fallback for the Dev/CR loop).
- `/retro` — weekly retro summarizing shipping streaks, test health, growth opportunities.
- `/heartbeat` — live SDLC dry-run: ship a canary change through PM → Dev → CR, verify four exit-state criteria, report PASS / PARTIAL / FAIL.
