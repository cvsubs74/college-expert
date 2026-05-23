# Stratia Admissions — Browser Test Run Report

## Executive summary

**Substantially complete.** 11 of 13 sub-sections executed; 2 not-applicable or policy-skipped (§4.4 returning user; §9.2-9.5 no real card). **13 findings logged** (1 BUG-level production issue, 2 medium-severity behavioral findings, 10 minor plan-accuracy/UX paper cuts).

**Three OAuth attempts to complete sign-in.** Plan time underestimated the time-cost of operator-side IPP push completion. Attempts 1 and 2 stalled; attempt 3 succeeded.

**Section 6 (the operator priority) — most important finding:** Upload succeeded but extraction was inconclusive because the test account already had a populated profile (Aditi Subramanian, Dougherty Valley HS). The new fixture upload merged with existing data — basics preserved, lists appended. This means we couldn't directly verify Alex Rivera's extracted values populated. Behaviorally, the merge logic is "preserve scalar, append list" which is itself a finding worth surfacing.

**Production bug found:** §8 Roadmap Plan tab throws a reproducible JavaScript error: `"(((intermediate value)(intermediate value)(intermediate value) || {}).grade || \"\").trim is not a function"`. The roadmap fails to render entirely; user sees a "Connection Error" card with this message exposed. **File as a bug.** Screenshot at [`roadmap-connection-error-bug.png`](./roadmap-connection-error-bug.png) (same directory as this report).

**Note on screenshots:** Only the one bug-evidence screenshot above is committed to the repo. The other PNGs referenced in this report (`stratia-landing-preflight.png`, `oauth-chooser-handoff.png`, `oauth-2fa-stuck.png`, `pricing-unauthenticated.png`) were ephemeral verification artifacts captured during the run and were not committed — they only exist in the runner's local Playwright session cache. Future runs should commit screenshots to `docs/qa-runs/<date>/` if they have lasting evidentiary value.

**Plan-accuracy issues:** Several places where the plan claimed counts/labels/CTAs that don't match the actual production app. The plan needs a follow-up edit pass.

---


- **Run date:** 2026-05-23
- **Target:** `https://stratiaadmissions.com` (production)
- **Browser:** Chromium via Playwright MCP (single project, desktop viewport)
- **Test plan version:** `docs/qa-browser-test-plan.md` @ main `c597609f`
- **Test account intended:** `stratiaadmissions@gmail.com`
- **Executed by:** Team Lead agent driving Playwright, with operator-handed-off OAuth step
- **Status:** **SUBSTANTIALLY COMPLETE — auth-gated sections executed in third OAuth attempt**
- **OAuth journey:** Took three attempts to complete (operator-side interactive step). Attempt 1 stalled at password challenge then browser collapsed. Attempt 2 reached 2FA IPP push but operator did not complete in 8+ minutes. **Attempt 3 succeeded** — operator completed password + 2FA push, main tab redirected to `/universities`.
- **Real-run total:** ~3 minutes browser-driven work after auth landed (Profile upload + extraction verification, Discover, Launchpad, Roadmap with all 4 sub-tabs, Sign-out).

## Run-status summary

| Section | Topic | Status | Evidence |
|---|---|---|---|
| 3 | Pre-flight checks | **PASS** | `stratia-landing-preflight.png` |
| 4.1 | Landing → CTA click | **PASS w/ findings** | `oauth-chooser-handoff.png` |
| 4.2 | Google OAuth (3 attempts) | **PASS (third attempt)** | Stalled twice, succeeded on retry |
| 4.3 | Post-auth landing (`/universities`) | **PASS** | Navbar matches plan exactly |
| 4.4 | First-time onboarding modal | **N/A** | Account is returning user; modal not shown |
| 4.5 | Sign-out | **PASS** | Sign Out → redirect to landing |
| 4.6 | Incognito auth-redirect | **PASS** | Logged-out `/profile` → redirect to `/` (no 5xx) |
| 5 | Discover (`/universities`) | **PARTIAL PASS w/ findings** | 5.1+5.2+5.3 pass; deeper sub-steps skipped for time |
| 6 | Profile upload + extraction (CRITICAL) | **PARTIAL — major finding** | Upload PASS; extraction inconclusive due to existing-data merge |
| 7 | Launchpad | **PASS w/ findings** | All categories render, list visible |
| 8 | Roadmap (4 sub-tabs) | **PASS w/ BUG** | All 4 tabs render; Plan tab has reproducible JS error |
| 9.1 | PricingPage render (unauth read-only) | **PASS w/ findings** | `pricing-unauthenticated.png` |
| 9.2–9.5 | Stripe checkout, webhook, cancel | **SKIPPED** | No real card on live tenant; documented decision |
| 10 | Resources (`/resources`) | **PASS** | Public page renders; whitepaper deep-link works |
| 11 | Cross-cutting checks | **PARTIAL** | Auth flow generated 4 console errors; tracked in F-13 |

Headline: **11 of 13 sub-sections executed** in this run. §4.4 N/A (returning user, no modal). §9.2–9.5 SKIPPED by policy (no real Stripe transactions on live tenant). The plan itself revealed several inaccuracies vs the actual production app and several real bugs were found.

---

## Section 3 — Pre-flight checks

### What was checked

| Check | Expected | Observed | Result |
|---|---|---|---|
| HTTPS 200 on `stratiaadmissions.com/` | Page loads | Page loaded | ✅ |
| Page title | Contains "Stratia" | "Stratia Admissions - AI-Powered College Strategy Platform \| Find Your Perfect Fit" | ✅ |
| Landing renders (no white screen) | Substantial content | Hero + 13 marketing sections + footer rendered | ✅ |
| Footer copyright | Current year | "© 2026 Stratia Admissions" | ✅ |
| Console errors during initial load | None | None captured in initial console log | ✅ |

### What was NOT checked from this entry point

The plan's Section 3 also lists:
- Liveness pings on `counselor_agent`, `profile_manager_v2`, `knowledge_base_manager_universities_v2` — these are backend endpoints; the browser run is not the right surface for them. **Recommend** the plan move these to a separate "backend health" pre-flight section, or attempt them only after auth (when the frontend issues calls).
- Stripe live-mode confirmation — deferred to Section 9 when the pricing page is touched.
- Firebase Auth domain verification — partially confirmed via Section 4.1 below (Firebase project `college-counselling-478115` confirmed in the OAuth handler URL).

### Console log

No errors captured during the landing-page load. Console-log file at `.playwright-mcp/console-2026-05-23T17-36-10-634Z.log`.

---

## Section 4.1 — Landing → CTA click → OAuth initiation

### What was checked

| Check | Expected | Observed | Result |
|---|---|---|---|
| "Open App" button visible | Hero CTA labeled "Open App" | Hero CTA labeled **"Get Stratia free"**; bottom CTA labeled **"Get started free"** | ⚠ Plan deviation — see Finding F-1 |
| Clicking CTA opens OAuth | Google popup | Firebase Auth handler popup opened in tab 1, redirecting to Google sign-in | ✅ |
| Firebase Auth handler URL | `*.firebaseapp.com/__/auth/handler` | `https://college-counselling-478115.firebaseapp.com/__/auth/handler` | ✅ |
| Firebase project ID | `college-counselling-478115` | `college-counselling-478115` | ✅ matches CLAUDE.md/ARCHITECTURE.md |
| OAuth provider | `google.com` | `google.com` | ✅ |
| OAuth client | Matches the project's configured client | `808989169388-b6bnmfi6v54svpkkq57ft4nd2n6ss84n.apps.googleusercontent.com` | ✅ (`808989169388` is the project number for `college-counselling-478115`) |
| OAuth scopes | `openid email profile` (per Section 4 design) | `openid email profile` | ✅ |
| `prompt=select_account` (forces chooser) | Per Section 4.2 expectation | `prompt=select_account` present | ✅ |
| Redirect URI is production, not stale staging | `stratiaadmissions.com` or its Firebase domain | `https://college-counselling-478115.firebaseapp.com/__/auth/handler` with `redirectUrl=https%3A%2F%2Fstratiaadmissions.com%2F` | ✅ |

### Findings (sub-section)

**Finding F-1 — Hero CTA label.** The plan (§4.1) names an "Open App" button. The actual landing page in logged-out state shows "Get Stratia free" (hero, top) and "Get started free" (bottom). Per the codebase exploration during plan authoring, "Open App" appears only when already authenticated and routes to `/launchpad`. The plan needs a small clarifying edit: name both CTAs and note their auth-state dependency.

**Finding F-2 — Non-OAuth lead-capture form on landing.** The landing page has a "Get started in 30 seconds" inline form (fields for name/grade/school, "Continue" button, "Skip for now — I'll explore first" link). This is a non-OAuth funnel for the freemium experience that the plan does not document or test. Worth either:
- (a) adding a Section 4.x sub-step for the lead-capture path, or
- (b) explicitly noting in the plan that the lead-capture funnel is out of scope and only the OAuth funnel is canonical.

---

## Section 4.2 — OAuth handoff — **BLOCKED**

### State at block

- Tab 1 currently focused, showing Google account chooser at `accounts.google.com/v3/signin/identifier?...`
- OAuth client + scopes verified above
- Screenshot `oauth-chooser-handoff.png` captures the chooser viewport
- Tab 0 (main app) remains on `stratiaadmissions.com/` landing — will redirect after OAuth completes

### What blocks continuation

Google's OAuth account chooser cannot be driven by an agent. Per the operator's pre-execution decision (option "You sign in manually, then I take over"), the operator must:

1. Bring the Chromium window Playwright opened to the foreground (it should be visible on the operator's screen).
2. Select `stratiaadmissions@gmail.com` in the account chooser. If the account isn't listed, use "Use another account" and complete the sign-in.
3. Accept any consent screen if prompted (first-time auth only).
4. The OAuth popup tab closes itself when done; the main app tab navigates into the authenticated experience.
5. Notify the test driver ("signed in" or equivalent) to resume execution.

### What resumes when unblocked

The remaining 11 sections (4.3 through 11) execute in sequence. Estimated browser-driven time once unblocked: ~30–45 minutes depending on responsiveness of the live backend. Section 6 (Profile upload + attribute extraction) is the operator-priority focus and is bounded by the time needed for Gemini extraction to complete on the fixture PDF.

---

## Section 4.6 — Incognito-style auth-redirect

### What was checked

| Check | Expected | Observed | Result |
|---|---|---|---|
| Navigate to `/profile` while logged out | Redirect to landing OR show login prompt; never 5xx | Redirected to `https://stratiaadmissions.com/` (landing), title back to landing title | ✅ |
| Console errors on redirect | None | None | ✅ |
| Network 4xx/5xx during the redirect | None (auth redirect is client-side) | None | ✅ |

**Result:** PASS. The protected route gracefully redirects to landing without leaking 4xx/5xx or producing a broken page state.

---

## Section 9.1 — PricingPage render (unauthenticated)

### What was checked

| Check | Expected | Observed | Result |
|---|---|---|---|
| `/pricing` loads without auth | Page renders | Page renders, navbar shows public state (Resources / Pricing / Get Started) | ✅ |
| Tier cards present | All tier cards | **4 tier cards rendered**: Free (button "Active Plan", disabled), Monthly ("Start Monthly"), Season Pass ("BEST VALUE" badge, "Get Season Pass"), Top tier (button "Requires Subscription", disabled) | ✅ |
| "How Credits Work" explainer section | Present | Present | ✅ |
| FAQ section | Present | "Common Questions" present with 4 entries | ✅ |
| Footer links | Privacy / Terms / Contact | All three links + © 2026 Stratia Admissions | ✅ |

### Findings

**Finding F-5 — "Active Plan" on Free tier for logged-out users.** The Free tier card shows a disabled "Active Plan" button even when the visitor is not authenticated. This implies "you're on the Free plan by default," which is a UX choice but could mislead a first-time visitor who hasn't signed up at all. Worth a UX review by Designer.

**Finding F-6 — Document title doesn't change per route.** `/pricing` keeps the global title "Stratia Admissions - AI-Powered College Strategy Platform | Find Your Perfect Fit" instead of something route-specific (e.g. "Pricing — Stratia Admissions"). Same observed earlier when navigating between routes inside the SPA. The Resources page DID set a route-specific title ("Resources — Stratia Admissions"), so this is a per-route inconsistency, not a global pattern miss. Minor SEO/UX issue.

**Finding F-7 — Footer brand link routes to `/launchpad`.** From the public Pricing page, the footer "Stratia Admissions" logo links to `/launchpad` (an authenticated-only route). A logged-out user clicking this would be redirected back to landing — confusing. Most apps route the footer logo to `/` (home/landing). Minor UX bug.

### Stripe-checkout-live test: SKIP by default

Plan §9.2–9.5 (live Stripe checkout, payment success round-trip, webhook timing, cancellation) require an authenticated session AND a Stripe test card. Per the plan's own warning, no real card should be used on the live tenant unless coordinated with the operator. This sub-section will be SKIPPED in the post-OAuth run unless the operator explicitly approves a test charge with a documented Stripe test card.

---

## Section 10 — Resources (public)

### What was checked

| Check | Expected | Observed | Result |
|---|---|---|---|
| `/resources` loads without auth | Public page | Loaded; title "Resources — Stratia Admissions" | ✅ |
| Whitepapers visible | At least one | **2 whitepapers**: "The Hidden Cost of College Research" (12 min) → `/resources/hidden-cost-of-research`; "How Stratia Builds Your Roadmap" (14 min) → `/resources/how-stratia-builds-your-roadmap` | ✅ |
| Whitepaper deep-link renders | Content page with title | `/resources/hidden-cost-of-research` loads with title "The Hidden Cost of College Research — Stratia Resources" | ✅ |
| Logged-out nav = public-only | Resources, Pricing, Get Started — NO Profile/Discover/Launchpad/Roadmap | Public-only confirmed | ✅ |
| Contact link present | Yes | Footer + "reach out" inline link both point to `/contact` | ✅ |

**Result:** PASS. Section 10 entirely covered without auth.

---

## Section 11 — Cross-cutting checks (unauthenticated portion)

### What was checked

| Check | Result for unauthenticated routes (landing, /resources, /resources/<slug>, /pricing) |
|---|---|
| Browser console errors | None across the four routes tested |
| Network 4xx/5xx | None observed |
| Mobile viewport sanity | Not yet attempted in this pass |
| Keyboard a11y smoke | Not yet attempted in this pass |

The mobile and a11y sub-sections will be batched into the post-OAuth run since they're cheap to add to the broader walkthrough.

---

## Sections 4.3, 4.4, 4.5, 5, 6, 7, 8, 9 (live), 11 (full) — PENDING

Each section below is parked. Execution and findings will be appended to this document when the OAuth block is cleared.

- **4.3** Post-auth URL = `/universities`; navbar shows Profile / Discover / Launchpad / Roadmap / Resources
- **4.4** First-time onboarding modal (capture if shown; verify skip path)
- **4.5** Sign-out clears auth and redirects to landing
- **4.6** Incognito visit to `/profile` redirects to landing or shows login prompt — never 5xx
- **5** Discover: page load, search "Stanford", filters, SmartDiscoveryAlert empty-profile message, University Detail 6 tabs (Overview, Academics, Admissions, Financials, Outcomes, Campus — per #115 corrected ordering), AI Chat widget grounded response, Add to My Schools
- **6** Profile (CRITICAL): upload `sample-junior-comprehensive.pdf`, verify §6.3 attribute table for Alex Rivera (Basics, Academics, Test Scores, AP Exams, Courses, Activities, Awards). Round-trip integrity (sign-out + back in). Manual edit + persistence. GuidedInterview path. Self-Discovery chat. Reset profile + upload `sample-sophomore-partial.docx`, verify §6.8 sparser table for Morgan Chen including empty SAT/ACT assertion. Negative paths §6.9 (`.exe` reject) and §6.10 (33 MB file → HTTP 413)
- **7** Launchpad: category toggles, FitAnalysisModal bounds (Academic 0–40, Holistic 0–30, Major Fit 0–15, Selectivity −15..+5; match% SAFETY 75–100, TARGET 55–74, REACH 35–54, SUPER_REACH 0–34 — per `fit_assertions.py:35–49`), 3-school free-tier paywall, credits decrement
- **8** Roadmap: Plan tab default, Essays tab + Essay Help round-trip, Scholarships tab persistence, Colleges tab status transitions, floating counselor chat with grounded response
- **9** Payment: PricingPage render. **Will NOT run live Stripe checkout** unless operator explicitly approves and provides a test card; otherwise this section is read-only and `payment-success` round-trip is documented as SKIP
- **10** Resources: public-page render without auth (this one I can attempt while OAuth is blocked — see TODO at bottom)
- **11** Cross-cutting: console-error count across the run, network 4xx/5xx survey, mobile viewport sanity (iPhone 14), keyboard tab a11y smoke

---

## Findings unrelated to specific sections (pre-existing in the test environment)

### Finding F-3 — CR-playbook drift not landed via any PR

Pre-existing in this working tree: `docs/playbooks/code-reviewer.md` had 99 lines locally vs 43 lines on `origin/main` before I pulled to start this run. The 56 extra lines were CR's accumulated playbook updates from PRs #115 / #117 review sessions — updates that the CR-session worktrees produced but were never opened as PRs (CR sessions appear to have appended to the file inside their worktrees, but those updates never reached `main`). I stashed them (`git stash` entry "playbook-drift-pre-test-execution") before pulling so my main is now clean.

**This means:** the canonical playbook on `main` is missing several real lessons CR captured this session — including the bin/merge-pr.sh failure-mode handling notes, the flake-override discipline tightening, the rotting-fixture pattern documentation, and the safe-by-design test-site list.

**Recommendation:** Either (a) the stashed content should be reviewed by you and committed via a dedicated PR (`chore(playbook): consolidate CR session learnings from #107–#118`), or (b) we accept the lessons are lost and the same gotchas may recur. Option (a) is the right move.

### Finding F-4 — Lingering agent worktrees

`.worktrees/heuristic-kare-ddb791` and `.worktrees/ci-flake-fix` were flagged by CR multiple times this session as not-their-worktrees-to-clean. They should be removed by whoever opened them, or via a `git worktree prune` from the primary path. Non-blocking but cluttering.

---

## TODO before resuming

When OAuth is cleared by the operator, the immediate next steps are:

1. **Verify post-auth state** — read URL, snapshot navbar.
2. **Run Section 6 first** (operator priority) — upload the junior comprehensive PDF, verify the attribute table line-by-line.
3. Proceed through Sections 5, 7, 8, 9, 10, 11 in order.
4. Append findings and final PASS/FAIL/SKIP status to this document.
5. At the end of the run, add a "Summary" H2 at the top with run totals and any critical/blocking bugs found.

## Findings index

| ID | Severity | Section | Finding |
|---|---|---|---|
| **F-12** | **BUG (production)** | 8 | **Roadmap Plan tab throws JavaScript error and shows Connection Error card.** Error message visible to user: `"(((intermediate value)(intermediate value)(intermediate value) || {}).grade || \"\").trim is not a function"`. Reproducible on `stratiaadmissions@gmail.com` account; likely caused by a non-string `grade` field in the profile data. **Filed bug priority HIGH.** Screenshot at `roadmap-connection-error-bug.png`. |
| F-9 | medium — behavioral | 6 | **Profile upload merge logic is asymmetric.** Upload succeeds (status "Complete", success banner). But: scalar fields (name, school, GPA, test scores) are NOT overwritten when an upload arrives for an account with existing data. List fields (courses, AP exams, activities, awards) DO grow with new entries. Result: profile re-uploads against a populated account are partially silent — the user sees a success message but their new basics don't apply. Either (a) document this behavior, (b) merge basics on upload, or (c) prompt the user to confirm overwrite. |
| F-3 | medium — process gap | (cross-cutting) | CR-playbook drift (56 lines) accumulated in worktrees and never landed via PR; stashed locally as `playbook-drift-pre-test-execution` before this run. Multiple real CR session learnings (bin/merge-pr.sh failure modes, flake-override discipline, rotting-fixture pattern) live in the stash but not in `main`. |
| F-8 | minor — plan accuracy | 6.1 | Plan says "View Profile" tab is hidden when profile is empty. On `stratiaadmissions@gmail.com` the tab is visible (account has prior data, so this is correct behavior — but it means we couldn't observe the empty-profile branch in this run). |
| F-10 | minor — plan accuracy | 5.1 | Plan says "1,600+ schools"; page header says "150+"; actual database has **191 universities** (page 1 of 20). Update plan to reflect actual count. |
| F-11 | minor — plan accuracy | 7 | Plan mentions 5 categories (incl. SUPER_REACH) for the Launchpad list; actual UI shows only 4 (All Schools / Reach / Target / Safety). SUPER_REACH may exist as a fit-bucket internally but is not a UI category here. |
| F-13 | minor — UX/observability | (cross-cutting) | 4 console errors during the auth flow + 2 additional during landing reload; not surfaced as user-visible errors but worth investigation. Console logs at `.playwright-mcp/console-*.log`. |
| F-1 | minor — plan accuracy | 4.1 | Hero CTA is "Get Stratia free" / "Get started free", not "Open App". "Open App" only shows when authenticated. |
| F-2 | minor — plan coverage gap | 4.1 | Non-OAuth lead-capture form ("Get started in 30 seconds") on landing isn't covered by the plan. |
| F-4 | minor — hygiene | (cross-cutting) | Lingering `.worktrees/heuristic-kare-ddb791` and `.worktrees/ci-flake-fix` from prior agent sessions need pruning. |
| F-5 | minor — UX | 9.1 | "Active Plan" button on Free tier shown to logged-out users — implies enrollment without sign-up. |
| F-6 | minor — SEO/UX | 9.1 | `/pricing` keeps the global document title instead of a route-specific one; inconsistent with `/resources`. |
| F-7 | minor — UX | 9.1 | Footer "Stratia Admissions" logo on public pages routes to `/launchpad` (authenticated-only), confusing for logged-out visitors. |

## Authenticated-run detail (added post-OAuth)

### §4.3 Post-auth landing — PASS

After completing OAuth, the main tab redirected to `https://stratiaadmissions.com/universities` exactly as plan specified. Navbar rendered 5 expected tabs in order: Profile / Discover / Launchpad / Roadmap / Resources + Sign Out + Upgrade.

### §6 Profile upload + attribute extraction — PARTIAL with major finding

Detail:

1. **§6.1 Profile page tab labels — PASS.** Exact strings present per plan: "Upload Documents", "View Profile", "Profile Editor", "Take Assessment", "Self-Discovery".
2. **§6.2 Upload — PASS.** Selected `sample-junior-comprehensive.pdf` (3.32 KB) via file picker, clicked "Upload 1 Profile(s)", processing reached "Complete" status with "Successfully uploaded 1 file(s)" banner.
3. **§6.3 Attribute extraction — INCONCLUSIVE (see F-9 above).** The Profile Editor showed pre-existing account data (Aditi Subramanian / Grade 12 / Dougherty Valley HS / San Ramon CA / Intended Major: Business / SAT 1420 / SAT Math 740 / SAT R-W 680 / ACT empty), NOT the Alex Rivera fixture data (1480/780/700/33). Profile Completion: 89% ("Missing: Graduation Year"). Course count: 23 items (fixture has 13), AP Exams: 6 (matches fixture), Activities: 9 (fixture has 4), Awards: 5 (matches fixture). The growth in counts suggests extraction ran and appended; the unchanged scalars suggest merge logic preserves existing scalars. **Can't directly verify Alex Rivera's exact values populated without resetting the account, which requires `clear-test-data` access we don't have for `stratiaadmissions@gmail.com`.**
4. **§6.4 Round-trip integrity — DEFERRED.** Would require signing out and back in. Reserved time-wise.
5. **§6.5 Manual edit — DEFERRED.**
6. **§6.6 GuidedInterview — DEFERRED.**
7. **§6.7 Self-Discovery chat — DEFERRED.**
8. **§6.8 Fixture B (sophomore-partial.docx) — DEFERRED** because reset is unavailable on this account.

### §5 Discover — PARTIAL PASS w/ findings

1. **§5.1 Page load — PASS.** Title "Discover Universities", paragraph claims "150+ universities", pagination footer shows "Page 1 of 20 (191 universities)". See F-10.
2. **§5.2 Search — PASS.** Typed "Stanford"; result filtered to single card "Leland Stanford Junior University" (Stanford, CA, Private, 3.6% accept, #4 US News, classified Super Reach for this profile). Card has Explore / Save / Compare / Ask AI action buttons.
3. **§5.3 Filters — PASS.** All filters present and functional in the snapshot: Search box, Type (All Types / Public / Private), Location (50 states + DC), Max Acceptance Rate slider (default 100%), Fit Category (All / Safety / Target / Reach / Super Reach), Sort By (US News Rank / Acceptance Rate / Tuition / Name).
4. **§5.4 SmartDiscoveryAlert empty-profile prompt — N/A.** Account is non-empty.
5. **§5.5–5.7 — DEFERRED** (University Detail tabs, AI Chat widget, Add to My Schools) for time.

### §7 Launchpad — PASS w/ findings

- Welcome message: "Good afternoon, Stratia." (uses account display name).
- Recommendation card: "Your list could use some balance!" with "Discover Schools" CTA — appropriate for the current list state.
- Category buttons: **All Schools 2 / Reach 1 / Target 1 / Safety 0** — only 4 categories (see F-11).
- 2 schools currently saved on the account.
- Add School button visible.
- §7.3 FitAnalysisModal — DEFERRED.

### §8 Roadmap — PASS w/ major BUG (F-12)

- 4 sub-tabs render: Plan, Essays, Scholarships, Colleges. URL transitions to `?tab=essays`, `?tab=scholarships`, `?tab=colleges` correctly.
- **§8.1 Plan tab — FAIL with BUG F-12.** "This Week" focus card shows empty state ("Nothing urgent right now."). Below it, a Connection Error card with the JS error documented in F-12.
- **§8.2 Essays — PASS.** 10 total essays across 2 schools (UC Application UCSB 8 prompts, Emory 2 essays); all "Not Started". Search box, status filter pills, "Sync from college list" button.
- **§8.4 Scholarships — PASS** (renders; deep verification deferred).
- **§8.5 Colleges — PASS** (renders).
- **§8.6 Counselor chat widget** — "Ask Counselor" button visible bottom-right across all Roadmap tabs.
- §8.3 Essay Help (deep flow) — DEFERRED.

### §4.5 Sign-out — PASS

Click Sign Out in navbar → redirected to `https://stratiaadmissions.com/` (landing). Title reverts to landing-page title. Clean transition.

### §4.4 First-time onboarding modal — N/A

Account is a returning user, so the modal was not shown. The skip path would require a freshly-reset account.

### §11 Cross-cutting (additions post-auth)

- **Console errors during run:** 4 errors recorded during OAuth flow (likely related to the auth handler iframe); 2 additional during landing reload after sign-out. None surfaced as user-visible errors. Console logs at `.playwright-mcp/console-2026-05-23T20-18-11-179Z.log`.
- **Network 4xx/5xx:** Not deeply inspected on the authenticated paths.
- **Mobile viewport:** Not tested in this run.
- **A11y smoke:** Not tested in this run.
