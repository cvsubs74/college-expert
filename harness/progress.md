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

## 2026-05-28 23:09 — shipped #187
- Bug: Roadmap "Upcoming Deadlines" showed scholarship rows as "132d/5687d overdue" and "NaN days left" for a junior.
- Root cause: planner.py scholarship branch copied raw KB `deadline` into `due_date` verbatim (no parse/skip-past/roll), unlike the application-deadline branch; frontend `getDaysUntil` had no Invalid-Date guard.
- Fix: `_normalize_scholarship_deadline()` rolls past annual deadlines forward to next occurrence + drops free-text/unparseable; frontend date helpers extracted to `utils/roadmapDeadlines.js` with NaN guard + "Date TBD" label.
- PR #188 squash-merged (46009e27), branch deleted, #187 auto-closed. Both CI surfaces green; harness reviewer approved (via comment).
- Deploy: counselor_agent auto-deploys via path-based cloudbuild-main on merge to main.
- Note: existing saved roadmap_tasks keep old due_dates until user hits "Refresh Tasks"; stale rows render "Date TBD" via the frontend guard.
- Follow-up surfaced by reviewer: `ApplicationsPage.jsx` has its own duplicate `getDaysUntil` (same latent NaN/TZ behavior) — candidate for consolidation onto `utils/roadmapDeadlines.js`.

## 2026-05-29 14:28 — shipped #189
- Cleanup (follow-up to #187): ApplicationsPage had its own unguarded `getDaysUntil` duplicate → NaN rendered as "Passed" / "Invalid Date".
- Fix: import shared guarded `getDaysUntil`; lift badge presentation into exported pure `deadlineUrgencyClass` / `deadlineDaysLabel` that handle null ("Date TBD" / neutral class); guard the formatted date span.
- PR #190 squash-merged (78c99931), branch deleted, #189 auto-closed. Both CI surfaces green; harness reviewer approved (via comment).
- Deploy: frontend auto-deploys via cloudbuild-main (`./deploy_frontend.sh` when frontend changed) → Firebase Hosting.
- Note: checkout had switched to `main` during the long CI gap; PR/commit were unaffected (changes lived on the pushed branch).

## 2026-06-12 10:45 — year-versioned university KB (feat-kb-year-versioning, PR pending gh auth)
- Goal session: full-codebase sweep + design/implement year-versioned university knowledgebase (ADR harness/decisions/0002-university-kb-year-versioning.md).
- KB versioning: `universities/{id}/versions/{year}` snapshots; main doc serves latest year (back-compat proven — deployed old code reads refreshed docs fine). Ingest takes `year` + validation gate (errors 400 / quality warnings); GET `?year=` / `?action=versions`; DELETE year promotes latest remaining. New CLI `scripts/ingest_universities.py` (--dir/--file/--year/--dry-run/--only/--merge-with-current); `ingest_specific.py` deprecated to a shim (was pointing at retired v1 ES function).
- Accuracy: `merge_cycle_refresh` overlays cycle-sensitive sections onto the rich current profile (fresh single-pass is ~3x thinner than original multi-agent collection); trends unioned by year.
- Tests: 59 KB unit tests vs in-memory Firestore fake (kbv2_* module aliasing avoids sys.modules collision with profile_manager_v2's firestore_db) + 7 merge tests. Suite: 861 backend + 190 frontend green. Real-Firestore e2e (10 checks, sentinel id, cleaned up) passed.
- Live demo: princeton_university archived as 2025 snapshot; merged 2026 profile promoted (acceptance 4.4→4.62, RD deadline corrected Jan 15→Jan 1, rich sections kept). Deployed function serves it correctly.
- Bugs fixed along the way:
  - tests/qa_agent/test_runner.py date-dependent mock (broke in June: junior_spring→junior_summer) — branch fix-qa-runner-date-dependent-test, cherry-picked here too.
  - qa-agent-hourly-poll scheduler attemptDeadline 180s < run duration (106-237s) → false URL_TIMEOUT errors every long run; raised to 540s (gcloud, prod config).
  - Secret Manager GEMINI_API_KEY was EXPIRED; synced new version (v2) from the working counselor-agent env var. (Key still needs proper rotation — old follow-up stands.)
  - deep_research_cli.py broke on new Interactions API shape (outputs[] → steps[].content[]); fixed with both-shapes extractor.
- Reviewer (subagent) approved the diff; SHOULD-FIX applied (storage failures now 500, not 400).
- BLOCKED on user: `gh auth login` (gh was not installed; brew-installed now, unauthenticated) → then open PRs for both branches. KB function deploys via path-based cloudbuild on merge.
- Operational follow-up (user's call, costs Gemini quota + hours): full 179-university refresh via deep_research_cli per university + `scripts/ingest_universities.py --dir ... --year 2026 --merge-with-current` after merge+deploy. Runbook: docs/university-kb-yearly-refresh.md.

## 2026-06-12 13:35 — full 2026 KB refresh executed (191/191)
- PRs shipped: #196 (date-fix), #197 (year-versioned KB), #199 (legacy auto-archive), #200 (research_2026 snapshot). KB function auto-deployed; versioned APIs live.
- Collection: deep_research_cli via 8-way concurrent driver, 191/191 universities, 0 failures, ~2.4h, ~100M tokens (mostly tool-use).
- Ingest: scripts/ingest_universities.py --year 2026 --merge-with-current in waves; final pass 191 ok / 0 failed.
- Incident caught mid-run: wave 1 (43 unis) promoted over legacy docs with no archive → 2025 snapshots backfilled (148 legacy archived from prod state, 39 from research/ sources; arizona_state/colorado_state/duquesne have no 2025 snapshot — history only via trends union). Root cause fixed server-side in #199 (auto-archive legacy doc under year-1 before takeover).
- Verification: 191/191 serving data_year=2026; 188/191 with 2025 archive; 0 bad acceptance rates; 1 deadline-less (wichita, rolling-only, warned at ingest). QA synthetic runs during+after refresh: all scenarios pass.

## 2026-06-12 14:10 — #204 Fit provenance stamping + KB-staleness detection (phase 1)
- Implementer: new fit_staleness.py — provenance stamped in calculate_fit_for_college (kb_data_year/kb_last_updated/input_snapshot); deterministic classify_kb_changes with material/minor/unknown severity; new check-fit-recomputation route returning kb_updates[]; KB batch endpoint now exposes data_year/last_updated (additive).
- Tester evidence: posted on #204 (18 unit tests; suite 889; verify.sh PASS); acceptance boxes ticked.
- PR: #209
- Reviewer: approved (comment review); raise_for_status + test-name notes applied.
- Discovered: /compute-all-fits never existed in v2 (frontend call no-ops) → filed #208.
- Note: gh token lacks 'project' scope → board status not moved; run `gh auth refresh -s project,read:org` when convenient.

## 2026-06-12 14:45 — #205 + #206 shipped: fit-staleness UX complete (epic #203 done)
- PRs: #210 (history archival + nudge suppression, backend), #211 (vintage chips + refresh banner + review screen + fit history UI + roadmap deadline annotation). Both squash-merged; #205/#206 auto-closed; epic #203 complete (with #209/#204 earlier).
- UX shipped: chips on Discover/Launchpad/fit-modal showing the cycle vintage; one dismissible banner per cycle when material changes hit the student's list; review screen with old→new facts + projected shift; student-applied updates with prior analyses archived (college_fits/{id}/history/{year}); applied/accepted colleges never nudged; moved roadmap deadlines annotated, not silently swapped.
- Live bug fixed en route: undeclared setRecomputingFits in UniversityExplorer crashed the profile-driven recompute path and aborted fits loading.
- Reviewer caught a real one: banner dismissal memory broke when kbUpdates arrived after mount (lazy useState init with year=undefined) — fixed + regression test.
- Suites at merge: backend 904, frontend 218, builds green. Auto-deploy on merge covers profile-v2, counselor-agent, KB v2, frontend.
- Note: #211 needed a merge of main after #210's squash landed (-X ours; branch was a strict superset).

## 2026-06-12 16:55 — consolidated scenario suite built, executed, shipped (#213)
- docs/scenarios/system-scenarios.md (13 executable scenarios) + scripts/run_scenarios.py (--skip-live for unit-only) + SCENARIO-RUN-2026-06-12.md: **13/13 PASS** (unit suites, live KB lifecycle incl. legacy auto-archive, versioned read APIs, validation gates, 191-doc 2026 integrity, deployed fit staleness/suppression/history via sentinel user, roadmap annotation, QA monitoring, health).
- Executing the suite caught a real defect: 19/191 collector files were JSON fragments (extractor grabbed first parseable block; merge mode masked it — ingest 'succeeded' with zero refresh). Fixed extractor (prefer profile-shaped candidate) + ingest CLI now validates fresh pre-merge (fragments fail loudly). 17/19 re-collected + re-ingested with real 2026 data; georgia_tech + michigan_state truncate on program catalogs (3 attempts each) — documented exceptions, KB docs uncorrupted, re-collect manually next cycle.
- Run the suite after every yearly refresh (noted in scenarios doc).

## 2026-06-12 21:30 — #215 "Update Fit" button morph (fit-staleness UX polish)
- Goal (via /goal + screenshot): move the "update available" signal off the passive chip and onto the Fit Analysis button. Product owner chose the "morph to Update Fit" treatment.
- Implementer: Launchpad UniversityCard's green "Fit Analysis" button morphs to an amber "Update Fit" (refresh icon) when kb_update is present; click recomputes via computeSingleFit (prior analysis archived server-side), shows "Updating…" spinner, then opens the refreshed FitAnalysisPage; failure re-enables + inline error. Card chip now vintageOnly (states data cycle only) so the CTA isn't duplicated — Discover (UniversityExplorer) + fit modal keep full chip text. New kbVintage helpers fitUpdateAvailable()/updateTooltip(); vintageChip exposes bare `vintage` (backward-compatible).
- Tests: +6 (kbVintage helpers, vintageOnly chip, UniversityCard morph/spinner/error). Frontend suite 224 PASS (was 218); build green.
- Issue #215, PR #216 (Closes #215). Branch feat-fit-update-button.
- Note: gh token still lacks 'project' scope → board status not moved.

## 2026-06-13 — #217 match-field sync + #215 split Fit Analysis control (PR #218, shipped)
- Investigated user report "Update Fit doesn't overwrite the DB". Traced compute-single-fit end-to-end (handler always recomputes; calculate_fit_for_college → essay_copilot.fetch_university_profile → top-level data_year=2026 → build_kb_provenance; save_fit_analysis archives + save_college_fit merge=True; read/write same college_fits subcollection). Confirmed deployed revision newer than #204/#206 provenance commits. Live KB probes: single-read + batch both return data_year=2026.
- ROOT CAUSE (#217): recompute emits only match_percentage; save is a Firestore merge; legacy docs carry match_score that the recompute never includes → stale match_score survived and FitAnalysisPage (match_score || match_percentage) showed the OLD score. Reproduced on deployed system via sentinel save-fit-analysis (match_percentage=34 but match_score=99).
- Fix: save_fit_analysis mirrors match_score/match_percentage on every save; FitAnalysisPage prefers match_percentage. +4 backend tests. Verified live post-deploy: match_score now syncs (FIX LIVE).
- UX (#215 follow-up): user asked to bring back "view current analysis" (the morph had removed it) and make it top-class. Built a SPLIT control on UniversityCard (green view segment always opens current analysis + attached amber refresh segment with pulsing dot when stale) + new FitUpdateBanner on the detail page (old→new cycle context, one-click Update analysis). +4 frontend tests.
- Bundled into one deploy. Suites: backend profile_manager_v2 125, frontend 228, build green. college-expert-main build b7b0f944 SUCCESS → profile-v2 rev 00098-cem + frontend (stratiaadmissions.com). #217 closed; #215 stays (the original morph issue auto-closed earlier via #216 — this is polish on top).

## 2026-06-13 — #191 deadline_date pilot + KB-wide stale-year sweep (PR #221, shipped)
- Rebuilt #191 on current main (stale issue-191-kb-capture branch predated KB year-versioning; old #192 closed/superseded).
- Schema: Scholarship.deadline_date (ISO, nullable) + collector prompt. Consumers: planner._scholarship_due_date (deadline_date-first, roll past→next, null-drop, text fallback via extracted _roll_forward_iso) + work_feed prefers deadline_date.
- Migration scripts/populate_deadline_dates.py (idempotent, deadline-fields-only) → pilot Duke/OSU/UCSD/USC: 32 fields; UCSD RD 2024-11-30→2025-11-30; scholarships dated/nulled. HTTP-verified; re-run no-op.
- GOAL "stale data in entire KB": scripts/fix_stale_kb_deadline_years.py — deterministic year-normalization to cycle window (month/day trusted; strict full-ISO guard skips annotated multi-date strings like Yale's; skips non-dict entries + unversioned docs). Applied: 277 application-deadline + 45 supplemental fields across ~130 schools; 0 stale on re-scan; versioning intact.
- Tests: backend 953 pass (model, planner deadline_date, both migration utils). CI fix: agents model test importorskip('pydantic') (CI backend image lacks collector deps).
- Deploy: counselor-agent rev 00032-quv. Live /deadlines for UCSD+Duke → 2025-11-30 / 2025-11-01 / 2026-01-02 (real upcoming, no stale). #191 acceptance boxes ticked w/ evidence.
- Note: existing stored fits still show old baked-in deadline until recomputed; Update Fit now pulls corrected KB date. Free-text scholarship deadlines + non-ISO supplemental strings left for Phase-2 structured-field work. Acceptance rates/financials NOT auto-touched (can't judge stale without fresh source; no mass-guessing).

## 2026-06-14 — Stripe subscription "charged but Free" — full end-to-end fix (PR #227)
- GOAL: stratiaadmissions@gmail.com charged monthly but app showed Free. Reviewed subscription logic end-to-end against the live system.
- DISPROVED #228 ("wrong account"): the DEPLOYED payment-manager-v2 STRIPE_SECRET_KEY is already the Stratia key (GET /v1/account → acct_1SqNZkIaK5CUG9Yl). #228 had read the legacy Secret Manager `stripe-secret-key` (used only by v1). Closed #228 not-planned.
- ROOT CAUSE (headline): stripe-python v12+ made StripeObject NOT a dict and removed .get(); every webhook read payloads/retrieve() results with dict-style .get() → first .get() raised AttributeError('get'), swallowed as "Error handling subscription webhook …: get". No webhook (checkout/subscription/invoice) ever provisioned anyone. Also current_period_end moved onto line items (broke .current_period_end dot-access).
- ROOT CAUSE #2: deployed webhook signing secret was the KA Academy one (Stratia API key + KA whsec = mismatched halves) → Stratia events failed signature. Recreated the Stratia webhook endpoint (we_1TiGye…), stored secret in new `stratia-stripe-webhook-secret`, deleted stale we_1SqSCV…
- ROOT CAUSE #3 (deploy): deploy_payment_manager_v2 read a gitignored/absent env.yaml → "Unable to read file [env.yaml]". Now renders env.deploy.yaml from committed env.yaml.template + Secret Manager (stratia-stripe-secret-key/-webhook-secret, both verified on acct_1SqNZkIaK5CUG9Yl).
- FIX: _as_dict() normalizes any Stripe object→plain dict (version-agnostic, no-op on dicts), applied at handle_webhook + defensively at handler entries + around every retrieve(); _subscription_period_end_iso() reads sub-or-item period end. Plus prior commit's provision_subscription (any-source + annual+monthly renewals), _norm email keys, signature-required.
- VERIFIED: reproduced the exact ": get" failure AND the fix with the REAL stripe 15.x lib. Backend 995 passed/2 skipped; payment_manager_v2 14 passed (+6 v15 regression tests via a _V15Obj fake). Deployed payment-manager-v2-00021-hoh. Reconciled the subscriber via the real signed webhook → tier=monthly, subscription_active=true, 20 credits (was free/0). Only one active Stratia sub existed.
- OPEN/NOTE: KA Academy's webhook still also points at payment-manager-v2/webhook (cross-account leak; out of scope per "only Stratia") — those deliveries now fail signature and are ignored. PR #227 (3 commits) open on branch fix-subscription-sync.

## 2026-06-14 — Research Notebook: save Claude analysis into the app (PR #229, shipped)
- GOAL: implement the Research Notebook feature end to end (cross-module: connector → profile_manager_v2 → frontend).
- Backend (profile_manager_v2): firestore_db save/get/list/delete over users/{email}/research (Python-side filter+sort, no composite index); routes save-research/get-research(list+single)/update-research/delete-research; provenance stamping (source, model, kb_year, generated_at) + kind validation. Fixed a latent function-scope datetime shadow (3 redundant local `from datetime import datetime` in the http entry → UnboundLocalError in the new branch).
- Connector: stratia_client + MCP tools save_research/list_research/get_research/update_research/delete_research (writes rate-guarded); server instructions prompt Claude to offer saving analysis.
- Frontend: ResearchNotebook page + ResearchCard (kind badge, college chips, expandable Markdown, provenance footer + amber staleness chip when based on an older KB cycle), /research route + nav link, utils/research.js, kbVintage.currentCycleYear().
- Tests: backend 7 + connector 7 + frontend 18. Suites green: backend 1009 passed, frontend 247 passed, build OK.
- Verified live: ran the real data path against deployed profile-v2 (save→list→get→update→kind-filter→delete; provenance correct; cleanup confirmed). MCP endpoint healthy + auth-gated.
- Shipped: PR #229 squash-merged to main (83142483). cloudbuild-main auto-deploy built+deployed all changed targets: profile-manager-v2-00101-xes, stratia-connector-00012-m89, frontend (bundle index-BB_2MDIV.js contains "Research Notebook"). stratiaadmissions.com/research → 200.
- Note: deploying frontend from a branch fails locally (frontend/.env gitignored/absent); the canonical frontend deploy is via cloudbuild-main.yaml which injects .env from Secret Manager `frontend-env-prod`. Don't hand-roll prod .env.

## 2026-06-14 — Research authoring in-app + Era-style "Connect your AI agent" hub + ChatGPT support (PR #230, shipped)
- Feedback on #229: research must not be Claude-only (add it in the app yourself; agents add via tool), and replicate Era's multi-agent connect experience incl. ChatGPT.
- Manual authoring: ResearchEditorModal (create+edit: title, kind, summary, Markdown body, link colleges, tags); "New research" button + per-card edit pencil; api.updateResearch (partial). Notebook copy now source-agnostic; empty state offers manual create + link to /connect. Manual notes stamp source='app' (verified live: save→provenance.source=app→delete).
- Connect hub (/connect, nav "Agents"): one copyable MCP URL + per-client setup for 9 clients (Claude.ai, ChatGPT, Claude Code, Cursor, VS Code, Gemini CLI, Windsurf, Cline, Goose) — concise steps, copyable config/CLI snippets, deep links (Cursor/VS Code/Goose), tier prereqs, "See all 9 clients". "Ask something real" = 8 curated prompts with Ask-in-Claude/Ask-in-ChatGPT + Copy. Per-client facts from a 10-agent parallel research workflow (official docs, 2026-06).
- ChatGPT support (server): settings.allowed_origins() now includes chatgpt.com + chat.openai.com (was Claude-only) so DNS-rebinding/Origin checks don't block ChatGPT's web client; CLI/IDE clients send no Origin. Rest of OAuth2.1+DCR+Streamable-HTTP already fits ChatGPT custom connectors. Note: connector runs auth before the Origin check on unauthenticated POST /mcp, so all origins return 401 there — the deterministic proof of the fix is the unit test (allowed_origins contains chatgpt.com); a full ChatGPT connect needs a real Plus account.
- Tests: frontend 256 (ResearchEditorModal, ConnectAgents, updated Notebook); backend/connector 1011 (allowed_origins). Build OK.
- Shipped: PR #230 squash-merged (6e598e50). cloudbuild-main deployed stratia-connector-00013-bfd + frontend (bundle index-BqW5NnKD.js contains the hub + authoring). /research + /connect → 200.

## 2026-06-14 — Collapsible left sidebar navigation (#231, PR #232)
- Operator ask: move the global nav to the left as a collapsible/expandable pane, referencing RegInsights /inbox. Stratia's nav was a sticky TOP bar — so "move to the left" was literal here.
- New SidebarContext (collapsed state → localStorage; shared so content offsets beside the fixed rail). Navigation.jsx rewritten: desktop fixed left rail (240px expanded / 64px icon-rail with tooltips, chevron toggle, persisted); mobile off-canvas drawer from a slim sticky top bar (hamburger + backdrop). Logo to top; user/Upgrade/Sign-out (or Sign in/Try Stratia) in the footer; aria-current active route; single Primary nav landmark.
- App.jsx: SidebarProvider around routes; AppLayout <main> offsets lg:pl-16/60. ResourcesPage + ResourcePaperPage offset when signed-in (shared Navigation); logged-out keeps MarketingHeader. Navigation.test.jsx rewritten for the sidebar.
- Verify: npm run build OK; 259 frontend tests pass (38 files). PR #232 (Closes #231). Follow-up noted: mobile drawer needs Escape/focus-trap/scroll-lock (a11y).

## 2026-06-14 — Fix: research mislabeled "From Claude" for all MCP clients (#233, PR #234)
- Operator: research saved from a ChatGPT session showed "From Claude". Root cause in 3 layers all defaulting to Claude: connector hardcoded source=claude_mcp/model=claude on save_research; profile_manager defaulted missing source to claude_mcp; frontend mapped claude_mcp→"From Claude".
- Server is stateless_http, so initialize clientInfo isn't available at tool-call — but the OAuth token carries client_id and each client's DCR client_name is stored. server._client_attribution() maps client_id→client_name→(source,model) for ChatGPT/Claude/Claude Code/Cursor/Windsurf/Cline/Goose/Gemini/VS Code; honest fallback keeps an unknown client's real name else neutral mcp/"an AI agent" (never Claude); logs unmapped names. save_research takes source/model; pm default claude_mcp→mcp; frontend SOURCE_LABELS map + fallback (legacy claude_mcp still "From Claude").
- Tests: connector _client_attribution parametrized + save_research pass-through/neutral-default; frontend per-client labels + fallback. Full frontend 257, connector 34, pm research 7 — green. PR #234 (Closes #233).
- Caveats: detection depends on registered client_name (logged to confirm/extend); already-saved notes keep claude_mcp (true origin not recorded). Needs deploy of stratia-connector + profile_manager_v2 + frontend to verify "From ChatGPT".

## 2026-06-14 — Research-notebook MCP analysis tools (#236, PR pending)
- Operator: beyond save/list/get, what tools make sense for the notes notebook? Built 6 (connector-only; all reuse existing profile_manager endpoints — get-research already returns full bodies, update-research whitelists pinned, save-roadmap-task exists):
  - search_research (weighted term rank over title/summary/body/tags + snippet), get_all_research (paginated, trimmed bodies, has_more), research_overview (counts by kind/college, stale/pinned, kinds_absent, last_updated), list_stale_research (kb_year < current cycle), pin_research (via update-research), research_to_tasks (agent-supplied tasks → roadmap, linked via source_research_id).
  - Cycle staleness mirrors frontend kbVintage (current cycle = year, +1 from August); functions take now= for deterministic tests.
  - University/KB research tools left untouched per operator.
- Tests: 10 new connector tests (rank/filter/paginate/aggregate/stale/pin/to-tasks/missing-note) + registration smoke. Full connector suite 69 green; both files compile. 28 MCP tools total.

## 2026-06-15 — Build a student profile from an agent (MCP tool + bulk-upsert route) (PR #238, shipped)
- GOAL: a student uploads a transcript/résumé in Claude/ChatGPT and the agent creates their Stratia profile.
- Backend: POST /update-structured-profile (profile_manager_v2) — bulk merge-upsert of a structured profile dict via the existing index_student_profile primitive (smart scalar/array merge, per-field source provenance). Returns merged profile. Imported index_student_profile into main.
- Connector: update_student_profile(profile, source?, source_text?) MCP tool + client; tool description carries the full canonical schema (name/grade/GPA/SAT/ACT, ap_exams, courses, extracurriculars, leadership_roles, special_programs, awards, work_experience) so the agent fills it from the doc; rate-guarded write; returns merged profile (internal/bulky keys stripped). Server instructions tell the agent to build the profile when a doc is shared.
- Frontend: "Build my profile from my transcript" prompt on /connect for discoverability.
- Verified live (profile-manager-v2-00104-tot, stratia-connector-00017-hb7): built a profile from a 'transcript' → persisted → second doc enriched without clobbering (name preserved, ACT added, courses merged+deduped) → cleaned up test data via source-aware delete-profile (profile back to empty). Used QA user duser8531; delete-profile by source filename is the surgical cleanup (field_sources provenance).
- Tests: backend 2 (create + smart merge via fake DB; stubs file_processing/profile_extraction/gcs_storage to avoid fitz), connector 3. Full suite 1026 passed.
- Note: `research_to_tasks` MCP tool already existed in main from prior research-notebook work (not added this session). Frontend /save-onboarding-profile route referenced by api.js does NOT exist in main.py (latent dead path; onboarding could reuse /update-structured-profile).
- Shipped: PR #238 squash-merged (5f522814); main pipeline redeploys profile-v2 + connector.

## 2026-06-15 — Fix: Profile page blank tabs / nonsensical counts (PR #239, shipped)
- BUG: /profile View Profile showed garbage counts (284 Activities, 176 Awards) and blank Academics/Activities/Achievements/Experience tabs.
- ROOT CAUSE: array fields (extracurriculars/awards/...) stored as STRING blobs on some accounts → OverviewTab rendered the string's char length as a count; detail tabs crashed calling .map() on a string → blank. (Confirmed live: stratiaadmissions profile is well-formed arrays-of-dicts and renders fine; the affected account's fields are strings.)
- FRONTEND (ProfileViewCard): asArray/asObjects coercion everywhere → array-only counts (string field reads 0, not its length), tabs never .map() a non-array (no crash); guard ActivityCard.achievements + leadership_roles items that may be objects (object-as-React-child crashes); string blobs surfaced as readable text (RawTextNote) instead of hidden.
- BACKEND (/update-structured-profile): coerce object-array fields to lists (dict→[dict]; un-structurable string→drop) + leadership_roles string→[string], so an agent passing a string can't corrupt the profile. Verified live (profile-manager-v2-00106-yom): posting extracurriculars as a string → stored as list[0] (dropped), not a string.
- Tests: ProfileViewCard (well-formed across tabs / sane counts for string fields / no-crash + blob surfaced / empty profile). Frontend 264 passed; backend 1026 passed; build OK.
- Shipped: PR #239 squash-merged (0bb459e9); main pipeline deploys frontend + profile-v2. Existing corrupted profiles now display gracefully; re-import via upload/agent restores structured cards.

## 2026-06-15 — Repeatable workflows: capture + repeat widget + workflows-as-algorithms (PR #241, shipped)
- GOAL/steer: save the tool-call workflows behind researches (NO BigQuery, NO instrumentation), let users repeat them, and associate each workflow with the researches it produced (workflows = reusable custom algorithms). Design: docs/design/tool-call-telemetry.md (PR #240).
- KEY INSIGHT: no instrumentation/correlation needed — the agent self-reports the workflow when it calls save_research (it knows its own steps). Rides on the research doc in Firestore.
- Capture: save_research accepts source_prompt (user's ask) + workflow ([{tool,label}]); backend sanitizes + stores + computes workflow_signature (ordered tool sequence). MCP tool description instructs the agent to include them (PII-free labels). Connector client passes them through.
- Repeat widget: ResearchCard Workflow section (steps) + 'Run again in Claude/ChatGPT' (repeat-prompt via /connect askLinks) + copy. App never executes tools — repeat = re-run in the agent.
- Workflows-as-algorithms: ResearchNotebook Research|Workflows toggle; Workflows view groups researches by workflow_signature → WorkflowGroupCard shows HOW (steps) + WHAT it produced (its researches, expandable inline) + Run-again. utils: workflowSteps/hasWorkflow/repeatPrompt/workflowSignature/workflowName/groupByWorkflow.
- Verified live (profile-manager-v2-00108-zaj + connector redeploy): save-research stores workflow/source_prompt/signature; get-research returns them.
- Tests: frontend 279; backend 1026 + connector workflow params; build OK.
- Shipped: PR #241 squash-merged (9e0117c3); main pipeline deploys frontend.

## 2026-06-15 — Popular Workflows: cross-user aggregate (PR #242, shipped)
- Built the Popular Workflows view: a third "Popular" tab in the Research Notebook surfacing the most-run workflows across all users as launchable templates. No BigQuery.
- Backend: firestore_db.upsert_workflow_stat (atomic Increment on root workflow_stats/{signature}) + get_popular_workflows (top-N by count, Python tie-break by recency). save-research upserts the stat. get-popular-workflows route (limit 1..50). NEW ROOT COLLECTION workflow_stats (cross-user readable via the endpoint; firestore.rules default-deny direct client reads).
- PRIVACY (key design): aggregate stores ONLY allowlisted tool-sequence signature + tools + kind + count + updated_at — NO user text. Server-side _KNOWN_WORKFLOW_TOOLS allowlist (_workflow_agg_tools) drops free-form/unknown tools so no PII can leak into the cross-user surface and tool names can't break the doc id; requires >=2 known tools.
- Frontend: api.getPopularWorkflows; utils tool-label map + popularWorkflowName/Prompt; PopularWorkflowCard (run count, friendly steps, Run in Claude/ChatGPT generic re-run prompt); Popular tab in ResearchNotebook (shown even with no personal research).
- ADVERSARIAL REVIEW (workflow, 2 lenses → verifier, 5 confirmed): fixed the free-form-tool privacy leak + doc-id-slash via the allowlist (verified live: a "John Smith ssn 123" tool was dropped, never aggregated); single-step gate; deterministic tie-break. ACCEPTED/known: profile_manager_v2 is --allow-unauthenticated and trusts X-User-Email (connector is the auth gateway) → count-inflation possible but bounded to legit signatures by the allowlist; endpoint auth is a separate cross-cutting change.
- Verified live (profile-manager-v2-00111-cit): ranking by count, PII dropped, single/unknown not aggregated; all seeded data cleaned up (research + workflow_stats docs via Firestore REST DELETE).
- Tests: backend 1030 (+ workflow_stats), frontend 286 (+ popular helpers/card/tab); build OK.
- Shipped: PR #242 squash-merged (61661666); main pipeline deploys frontend. Populates as agents save >=2-step workflows (reconnect connector so save_research sends workflow).

## 2026-06-15 — Agents+Research: feature ideation + quick-win bundle (PR #246, open)
- GOAL: suggest useful + cool features around the Agents (MCP connector) and Research surface, then build picks.
- IDEATION (Workflow wf_a73d2daf-35c, 44 agents): map real surface → 8-lens ideation (40 ideas) → cluster (15) → 2-lens adversarial scoring → synthesis. Top picks: Decision Ledger (flagship), This Week's 3 Things, Profile-aware Popular templates, Balance Ring, Research→Roadmap loop, Fit Drift Timeline. Filed the 6 as backlog: #247-#252.
- STEER: user chose the "quick-win bundle" (3 S-effort features) for this session; filed #243/#244/#245.
- BUILT (PR #246, Closes #243/#244/#245):
  - #243 Revive pinned: `pinned` was persisted by the connector (update-research whitelists it) but had ZERO frontend consumers. Added api.pinResearch + pinned passthrough, optimistic pin toggle on ResearchCard, pinned-first ordering in the Research tab.
  - #244 Balance Ring: pure utils/listBalance (verdict/segments) + presentational BalanceRing on the Launchpad over the EXISTING categorizedColleges/stats (merges personalized fit_category) — summarizes exactly what the page shows, can't lie. Gated >=3; honest "N estimated" caption; "Fix my balance" hands off to the agent with an explicit NO-recompute prompt (no credit burn).
  - #245 Trending Popular: upsert_workflow_stat also increments per-ISO-week bucket weeks[YYYY-Www] (atomic nested Increment, read-free); get_popular_workflows trims returned weeks to recent window (read-bandwidth bounded; stored doc keeps all, ~52 ints/yr = negligible). Frontend isoWeekKey/workflowTrend/isNewToUser (ISO week matches Python isocalendar) → 🔥 Trending badge (count>=5 AND this>1.5x last) + ✨ New-to-you chip. Aggregate stays PII-free.
- REVIEW: adversarial reviewer agent APPROVED — ISO-week JS/Python parity cross-checked 2018-2031 (0 mismatches), nested-Increment merge atomic/key-preserving, no-NaN gating, optimistic rollback verified. Verdict posted as PR comment (self-approve blocked by GitHub).
- TESTS: backend 1032 passed (+2 weekly-bucket/trim), frontend 305 passed (+19), build green.
- NOT shipped: PR #246 left open for review/merge — merging to main auto-deploys to prod (needs user go-ahead). Trending populates once agents save >=2-step workflows post-merge.

## 2026-06-15 14:40 — shipped #243 #244 #245 (PR #246)
- PR #246, squash-merged (afe6951a), branch deleted.
- Tracking: #243 #244 #245 all auto-closed (Closes lines).
- Board: set-status FAILED — gh token missing 'read:project' scope (cosmetic; issues are source of truth). Fix with: gh auth refresh -s project,read:org
- Deploy: push to main triggers cloudbuild-main.yaml → frontend (Firebase Hosting) + profile_manager_v2 (firestore_db.py weekly buckets).
- Quick-win bundle live after pipeline: pinned toggle, Balance Ring, Trending Popular. Trending fills in as agents save >=2-step workflows.

## 2026-06-15 14:58 — Decision Ledger (flagship, PR #253) — #247
- GOAL/steer: user said "proceed" → build the next pick. Built #247 Decision Ledger end-to-end via the pipeline (one issue/session).
- WHAT: agent (or student in-app) records real admission OUTCOMES; app shows predicted (fit category) vs actual (decision). The "graded against reality" flagship from the ideation workflow.
- Connector: set_application_status (safe-write, rate-guarded) + get_outcome_calibration (read). decision (accepted/waitlisted/denied/deferred/enrolled) kept SEPARATE from process status; synonyms normalized, unknowns REJECTED symmetric with frontend (no junk stored); '' clears.
- Backend: firestore_db.get_outcome_calibration joins college_list.decision ⋈ college_fits.fit_category (soft fallback), decided newest-first; route get-outcome-calibration; update-application-status stamps decided_at. Read-only, no LLM/credits.
- Frontend: pure utils/outcomes.js (normalize/predictedBand/calibrationOutcome/calibrationSummary — reach-admit = "beat the odds" not a hit, so hit-rate never overclaims; headline suppressed <3 decisions). DecisionLedger strip on Launchpad (predicted band + decision selector + predicted-vs-actual marker), optimistic setter; api getOutcomeCalibration + setApplicationDecision.
- REVIEW: reviewer agent APPROVED (decision/status separation, join+normalization parity, no cross-user leak verified); both NITs fixed. Verdict posted as PR comment.
- TESTS: backend 1040 passed (+8), frontend 320 passed (+16 across 2 files), build green.

## 2026-06-15 — Resources: third whitepaper "How Stratia Works With AI Agents" (PR #254)
- GOAL: add a Resources paper on how Stratia exposes itself as MCP so AI agents can work with it; ground it in the recent MCP features.
- BRANCHED off main (resources-mcp-agent-paper) — NOT the in-flight issue-247 branch — since this is a standalone content task.
- WROTE paper how-stratia-works-with-ai-agents.js (cat: Platform & Architecture, violet/fuchsia). 7 sections: app-vs-agent-operable thesis → the connector (remote MCP, Google OAuth+DCR, Cloud Run) → 31-tool surface (read/act/remember) → per-user safety model → the write-back round trip → honest-about-itself (attribution + workflows + Decision Ledger) → what-this-gets-you. Every claim grounded in shipped code: #222/#226 connector, #229/#236 notebook, #233 attribution, #238 profile-from-agent, #241/#242 workflows, #247 Decision Ledger.
- BUILT 3 inline visuals + registered: AgentBridgeFlow (hero: agents⇄connector⇄data), ToolSurfaceGrid (31 tools, ASKS FIRST/1 CREDIT badges), ClosedLoopDiagram (ask→read→reason→save_research → notebook note w/ provenance + spun-out roadmap task). Matched the existing visual idioms (framer-motion useInView, palette).
- Hub hero copy: two papers → three.
- TEST: generalized per-paper render test to it.each over ALL papers (mounts every hero+section visual → catches bad icon/visual refs). vitest 307 passed (+2); build clean.
- VERIFIED visually: rendered logged-out at localhost:3000, screenshotted hub + hero + both inline visuals — all on-brand. (Local dev needed a throwaway .env.local with fake Firebase keys to mount AuthProvider; removed after.)
- NOT merged: PR #254 left open — merging to main auto-deploys frontend to prod (needs user go-ahead). Paper goes live at stratiaadmissions.com/resources on merge.

## 2026-06-15 (cont.) — Landing page: surface the AI-agent (MCP) capability (PR #254)
- Follow-on to the whitepaper: user asked to also feature the agent/MCP capability on the landing page.
- ADDED a "Works with your AI agent" band to LandingPage.jsx, after How-It-Works (white → green band → cream rhythm). Contents: NEW pill, serif headline "Already use Claude or ChatGPT? Now they work with Stratia.", a your-agent ⇄ Stratia ⇄ your-data bridge graphic (white card on the green band), 3 capability cards (reads your data / acts on your behalf / saves the work back), CTA row (Get started free + "See how it works →" → /resources/how-stratia-works-with-ai-agents). Brand palette (dark-green accent like stats/CTA bands), framer-motion in-view via new agentRef.
- /connect is auth-gated, so the secondary CTA points at the PUBLIC whitepaper (clean funnel) and primary uses the existing handleGetStarted.
- FIXED ⇄ arrow rotation in resources AgentBridgeFlow (was vertical on desktop; now horizontal between side-by-side columns; vertical on mobile stack).
- VERIFIED: vitest 307 passed; build clean; screenshotted the landing band on desktop AND mobile (390px) — bridge stacks correctly, all on-brand, no page errors.
- Same branch/PR #254 (scope broadened): title now "surface the AI-agent (MCP) capability — resources whitepaper + landing section".

## 2026-06-15 15:32 — shipped #253 (Decision Ledger / #247) + #254 (AI-agents whitepaper)
- PR #253 squash-merged (15aa6300) → #247 auto-closed. Decision Ledger live after pipeline: connector tools set_application_status/get_outcome_calibration, backend get-outcome-calibration, Launchpad DecisionLedger strip.
- PR #254 squash-merged (dc9b57f1). Resolved a harness/progress.md conflict (both branches appended) by merging origin/main into the branch (no force-push) + re-running CI. Reviewed #254 before merge (reviewer APPROVED: whitepaper claims cross-checked against the real 31-tool connector; JSX/registry/route correct). Whitepaper + landing band live after pipeline.
- Board: #247 set-status skipped (gh token lacks read:project; cosmetic).
- Deploy: both merges trigger cloudbuild-main.yaml → connector + profile_manager_v2 + frontend to prod.
