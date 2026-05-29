# Progress log

Append-only. Each session adds an entry. Never rewrite history.

Format:

```
## YYYY-MM-DD HH:MM — <event>
- <bullet 1>
- <bullet 2>
```

Events include: `kickoff`, `F<NNN> <title>`, `retro F<NNN>`, `shipped F<NNN>`, `note`.

---

<!-- Future entries appended below. The first will be the /kickoff entry. -->

## 2026-05-26 19:02 — note
- Discussion-only session: assessed whether the engineering-workflow harness scales to complex server+client products.
- No code, features, or harness files changed. No /kickoff run yet — features.json still empty.
- Conclusion: harness discipline (acceptance criteria, ADRs, agent pipeline, append-only log) ports to any scale; specific tooling (features.json as SoT, one-feature-per-session, worktree parallelism) is sized for solo/small-team work.

## 2026-05-26 21:30 — note
- Harness rewrite: GitHub Issues are now the source of truth (features.json removed).
- Plan executed in 8 commits (c7b707b → 5c09f91): foundation scripts, GH issue forms/PR template/CODEOWNERS, agent specs, worktree scripts, slash commands, hooks, top-level docs, and final deletion of features.json + schema.
- Plan file: /Users/csubramanian@onetrust.com/.claude/plans/toasty-cooking-treehouse.md
- Outstanding: .claude/settings.json needs 4 new Bash permits for scripts/gh-*.sh (auto-mode classifier blocked the edit). Surfaced for manual application.
- Not pushed — local commits awaiting user's call on push.

## 2026-05-26 22:19 — kickoff
- Spec: `docs/spec.md` (drafted from existing live product, not via `/start` wizard).
- Epics filed: 6 (#156 Profile & onboarding, #157 College fit & list, #158 Roadmap & chat, #159 Essay help, #160 Payments & pricing, #161 Operations & QA). All `type:epic,area:<n>,meta:bootstrap`, milestone `v0.1`.
- Stories filed: 20 (#162–#181). P0: 4 (#166, #170, #176, #179). P1: 8 (#162, #167, #168, #171, #173, #174, #177, #180). P2: 8 (#163, #164, #165, #169, #172, #175, #178, #181). Each linked as sub-issue of its parent epic and added to the Projects v2 board.
- Architecture: production stack accepted as-is — Python 3.11 Cloud Functions Gen2 (us-east1, GCP `college-counselling-478115`), Firestore, Gemini Flash, Stripe, React 19 + Vite SPA on Firebase Hosting. Canonical detail in `docs/ARCHITECTURE.md`.
- ADR 0001: `harness/decisions/0001-stack.md` — captures the locked-in stack and the alternatives explicitly considered + rejected (Cloud Run migration, multi-provider LLM, Postgres, ES reactivation, Next.js). Spike issue #182 filed + closed as audit trail.
- Bootstrap issues (closed for audit trail): 1 (#182). The new harness reserves `meta:bootstrap` for `/kickoff`-time audit issues.
- Harness scripts filled: `harness/init.sh` (tool checks + frontend `npm ci` + pytest availability) and `harness/verify.sh` (bash syntax on 17 scripts, python syntax on 8 live cloud functions, frontend Vite build). Baseline verified locally: `verify.sh: PASS` in ~5s. `.github/workflows/ci.yml` extended with `setup-python@v5` + `setup-node@v4` + npm cache.
- Bootstrap script fix: `scripts/gh-bootstrap.sh` patched to skip the Projects v2 `Iteration` field — `gh project field-create` doesn't accept `--data-type ITERATION` (needs GraphQL with iterations[] config). Field can be added manually in the UI; not load-bearing.
- Deferred (flagged for follow-up):
  - Existing OLD label scheme (`bug`, `enhancement`, `backlog`, `prioritized`, `priority:high|medium|low`, `in-progress`, `in-review`, `resolved`, `qa`, `pm`) coexists with the new EW labels. No open issues use them, so no cleanup is urgent — delete via `gh label delete` when comfortable.
  - Projects v2 `Iteration` custom field — add via UI when iteration planning starts.
  - `cloudbuild-main.yaml` path-based auto-deploy still active alongside the new GitHub Actions `verify` workflow. Two CI surfaces. Decide whether to consolidate or keep both (Cloud Build for deploy, Actions for fast verify) in a follow-up ADR.

## 2026-05-28 22:22 — shipped #185
- Bug: profile upload succeeded but saved profile had all fields empty. Root cause: PyMuPDF (fitz) raises `code=7: cycle in resources` on a readable PDF (reproduces on latest PyMuPDF) → no text → LLM returns nulls → falsy `if profile_data:` drops every field while upload reports success.
- Fix: pypdf fallback in `file_processing._extract_pdf_text`; replaced retired `gemini-2.0-flash-exp` (404) with `gemini-2.5-flash-lite` in markdown + change-eval. Added `pypdf` to function requirements + `requirements-test.txt`.
- Diagnosis was evidence-driven: prod logs, local PyMuPDF-vs-pypdf repro, and live Gemini calls proving the structured model works with real text (model 404 was a red herring for the empty-profile symptom).
- PR #186 squash-merged (37e1a9c4), branch deleted, #185 auto-closed. Both CI surfaces green (caught + fixed a Cloud Build break where the new test needed pypdf in requirements-test.txt).
- Reviewer (harness) approved via comment (author can't self-approve; branch protection requires only the `verify` check).
- NOT deployed — needs `./deploy.sh profile-v2` so the live revision picks up `pypdf`.
- Follow-ups (in #185 / noted): silent `success:true` on empty extraction; rotate hardcoded `GEMINI_API_KEY` in `env.deploy.yaml`; `gh-project.sh` set-status fails with >100 records (pagination bug).
