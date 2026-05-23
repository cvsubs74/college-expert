# Stratia Admissions — Browser-Based QA Test Plan

**Version:** 1.0  
**Date:** 2026-05-23  
**Author:** QA Agent  
**Review:** Code Reviewer (blocking), Designer Agent (non-blocking read-pass on §11.3, §11.4, §5.6, §7.4, §8.6)

---

## 1. Purpose & Scope

This document is the canonical pre-release sign-off procedure for
**Stratia Admissions** (`stratiaadmissions.com`). It covers every user-facing
surface reachable from the top-level navigation: Profile, Discover, Launchpad,
Roadmap, and Resources, plus the Pricing/Payment flow.

**Two execution modes:**

1. **Manual sign-off** — run end-to-end before any deploy that touches a
   frontend route, a live data path (Firestore, GCS, Stripe), or a Cloud
   Function serving authenticated users. Estimated wall-clock time: 45–60 min.
2. **Automation source-of-truth** — each scenario in this plan maps 1:1 to a
   future Playwright spec file. Section 13 (Automation handoff) describes the
   migration path.

**Non-goals (explicitly out of scope):**

- Load testing or performance benchmarking.
- Security / penetration testing.
- Accessibility audits (Designer Agent owns that track; Section 11.4 captures
  a lightweight smoke check, not a full WCAG audit).
- API-level assertions — those are covered by the 18 QA-agent scenarios in
  `cloud_functions/qa_agent/scenarios/`.

---

## 2. Test Environment

### 2.1 Target URL

**`https://stratiaadmissions.com` (production).**

Never run this plan against localhost or a staging URL unless the operator
explicitly instructs otherwise and the staging environment has a separate
Firestore project. Production data pollution is a real concern — see §2.3.

### 2.2 Browser matrix

**Day-1 required:** Chromium (Chrome stable, latest).

**Expansion candidates (file as `enhancement,backlog` when ready — do not block
this plan):** Firefox stable, Safari on macOS, mobile Safari (iPhone 14 390×844
viewport), mobile Chrome (Pixel 7 412×915 viewport).

Open DevTools → Console before starting; keep it open for all of §11.1.

### 2.3 Test accounts

**Primary browser test account:** `stratiaadmissions@gmail.com`

This account is the canonical human-in-the-loop test identity. It goes through
real Google OAuth (not the local `__E2E_TEST_USER__` localStorage bypass) and
writes to production Firestore.

**Secondary synthetic account:** `duser8531@gmail.com` (QA agent's backend
test user, configured via `QA_TEST_USER_EMAIL` env var). This account is used
by the automated QA agent's 18 scenarios and the `clear-test-data` endpoint.
It does NOT go through real OAuth and is NOT the primary account for this plan.
The two accounts are complementary — not redundant.

### 2.4 Data hygiene

**Before each full plan run**, ensure the primary account is in a known state.

The `profile_manager_v2` function exposes a `/reset-all-profile` endpoint (see
`cloud_functions/profile_manager_v2/main.py` lines 1267–1327) that deletes the
user's Firestore profile document, all GCS files, and all fit analyses. It
optionally deletes the college list (`delete_college_list: true`).

For the `duser8531@gmail.com` synthetic account, the QA agent's
`/clear-test-data` endpoint (`profile_manager_v2/main.py` line 1744, backed by
`firestore_db.py` lines 867–910) is available. It requires:
- `POST /clear-test-data` with JSON body `{"user_email": "duser8531@gmail.com"}`
- Header `X-Admin-Token: <QA_ADMIN_TOKEN secret>`
- Clears subcollections: `profile`, `roadmap_tasks`, `essay_tracker`,
  `scholarship_tracker`, `college_list`, `aid_packages`, `tasks`.
- Does NOT clear GCS files or fit analyses — those remain.

**Important:** `clear-test-data` only accepts `duser8531@gmail.com` (the
`QA_TEST_USER_EMAIL` env var) and will 403 for any other email, including
`stratiaadmissions@gmail.com`. For the primary browser account, use
`/reset-all-profile` or the manual "Reset Profile" button in the UI.

**Recommended baseline for a full plan run:**

1. Sign in as `stratiaadmissions@gmail.com`.
2. Navigate to `/profile` → "Reset Profile" button → confirm with
   "Delete College List" unchecked (keep school list for Launchpad tests, or
   re-add 3 schools post-reset).
3. Verify the Profile tab shows "No Profile Data" and the "Upload Documents"
   tab is active.

### 2.5 Credits state

The primary account should have **Premium tier or credits seeded** before the
Payment section (§9). If the account is on the free tier, Sections §7.5 and
§7.6 require it. Confirm credit balance via the CreditsBadge in the navbar
before starting §7.

---

## 3. Pre-flight Checks (5 min)

Run these before the full plan. If any check fails, halt and investigate before
proceeding.

| # | Check | Pass criterion |
|---|---|---|
| 3.1 | Navigate to `https://stratiaadmissions.com` | HTTP 200; page renders without white screen or React error boundary |
| 3.2 | `profile_manager_v2` health | `GET https://profile-manager-v2-pfnwjfp26a-ue.a.run.app/health` returns `{"status":"healthy","service":"profile_manager_v2","backend":"firestore"}` |
| 3.3 | `counselor_agent` health | `GET <COUNSELOR_AGENT_URL>/health` returns `{"status":"ok"}` or `{"status":"healthy"}` |
| 3.4 | Firebase Auth domain | DevTools → Application → Storage → Firebase Auth shows `stratiaadmissions.com` as the authorized domain, not a stale staging host |
| 3.5 | Stripe mode | Navigate to `/pricing`; open DevTools → Network; click any "Upgrade" CTA; inspect the Stripe Checkout redirect URL — confirm it contains `live` keys (starts with `pk_live_`) not `pk_test_`. If test keys appear, flag to operator before proceeding with §9 |
| 3.6 | Console clean baseline | DevTools Console shows no errors at `stratiaadmissions.com/` before sign-in |

---

## 4. Authentication Flow

### 4.1 Landing page — Open App button

- Navigate to `https://stratiaadmissions.com`.
- Assert: the page renders the LandingPage component. Look for a primary CTA
  button with text containing "Open App" or "Get Started" (exact text from
  `frontend/src/pages/LandingPage.jsx`).
- Assert: clicking the button initiates Google OAuth (a Google popup or
  redirect appears, or the user is taken to `/universities` if already signed
  in from a previous session).

### 4.2 Google OAuth popup

- In a fresh browser session (clear cookies if needed), click the sign-in CTA.
- Assert: Google account chooser popup appears.
- Select `stratiaadmissions@gmail.com`.
- Assert: if previously authorized, the consent screen does NOT appear — the
  app returns directly without re-prompting OAuth scopes.
- Assert: on successful auth, the browser navigates to `/universities` (the
  post-auth landing route per `App.jsx` line 193: `path="/universities"`).

### 4.3 Post-auth landing state

- Assert: URL is `https://stratiaadmissions.com/universities`.
- Assert: top navigation bar shows exactly five items in this order:
  **Profile** | **Discover** | **Launchpad** | **Roadmap** | **Resources**
  (verified from `Navigation.jsx` lines 28–32, which define
  `/profile`, `/universities`, `/launchpad`, `/roadmap`, `/resources`
  with those labels).
- Assert: a `CreditsBadge` is visible in the navbar (for authenticated users).

### 4.4 First-time-user onboarding modal

- If the primary account has no profile, the `OnboardingModal` component
  (`App.jsx` lines 136–143) will render.
- Assert: modal is visible.
- Assert: a "Skip" path closes the modal without crashing the page.
- Assert: completing the onboarding wizard calls `saveOnboardingProfile` and
  sets `sessionStorage.onboarding_completed_<email>` = `'true'`.
  (Verify by checking Application → Session Storage in DevTools after
  completing the flow.)

### 4.5 Sign-out

- Navigate to any protected route.
- Find the sign-out control (navbar, per `Navigation.jsx`).
- Click sign out.
- Assert: browser redirects to `/` (LandingPage).
- Assert: navigating to `/profile` after sign-out either redirects to `/` or
  shows a sign-in prompt — never the profile page contents.

### 4.6 Negative: unauthenticated access

- Open an incognito window.
- Navigate directly to `https://stratiaadmissions.com/profile`.
- Assert: HTTP status is not 500; the page either redirects to `/` or renders
  a sign-in prompt.
- Assert: no user data is visible.

---

## 5. Discover Tab (`/universities`)

### 5.1 Page load and grid render

- Navigate to `/universities`.
- Assert: the university grid renders with at least one university card
  visible within 5 seconds.
- Assert: a pagination indicator appears at the bottom of the grid in the form
  `Page 1 of N (M universities)` where M > 0
  (from `UniversityExplorer.jsx` line 1782: `({totalCount} universities)`).

### 5.2 Search by name

- Type `"Crestwood"` in the search input and wait for results (debounce ~300ms).
  (Using a fictional name to test "no results" path is also valid — do both.)
- Clear the search; type `"Stanford"` (or a name known to be in the KB).
- Assert: results narrow to schools matching the query.
- Open one result card; assert the card surface shows: university name,
  acceptance rate or a dash, location, and at least one ranking indicator.

### 5.3 Filters

- Apply the **State** filter (e.g., select "California").
- Assert: all displayed cards are in California (check location text on cards).
- Clear the state filter.
- Apply the **Fit tier** filter (Reach, Target, or Safety).
- Assert: if the primary account has no profile, the filter either shows an
  empty result set or a prompt indicating profile is needed for fit-based
  filtering (the fit data is blank without a profile; the filter is valid but
  will match no schools).
- Assert: with a loaded profile, only schools matching the selected tier appear.

### 5.4 SmartDiscoveryAlert (Launchpad context)

- With the primary account having no saved schools, navigate to `/launchpad`.
- Assert: the `SmartDiscoveryAlert` component renders, displaying a suggestion
  to add schools (confirmed present in `StratiaLaunchpad.jsx` line 576).

### 5.5 University detail panel

- From the `/universities` grid, click any university card to open its detail
  view (`UniversityDetailPage`).
- Assert: the detail panel/modal opens without a page crash.
- Assert: exactly six tabs are present, with these labels:
  **Overview** | **Academics** | **Admissions** | **Financials** |
  **Outcomes** | **Campus**
  (from `UniversityDetailPage.jsx` lines 176–182; note the order:
  Overview, Academics, Admissions, Financials, Outcomes, Campus).
- Click each tab in sequence.
- Assert per tab:
  - Overview: renders descriptive text or stats (not an empty white box).
  - Academics: renders at least one data point (GPA range, graduation rate, etc.).
  - Admissions: renders acceptance rate or "N/A" (not an empty white box).
  - Financials: renders at least one cost-of-attendance figure.
  - Outcomes: renders at least one employment or earnings data point.
  - Campus: renders campus culture or location descriptors.

### 5.6 AI University Chat widget

- With a university detail panel open, locate the chat widget
  (`UniversityDetailPage.jsx` renders `UniversityChatWidget`).
- Send the message: `"What is the average SAT score for admitted students?"`
- Assert: a response appears within 15 seconds.
- Assert: the response references the specific university by name (not a
  generic answer such as "I don't have that information" for schools with SAT
  data in the KB).
- Assert: the conversation persists if you close and reopen the widget for
  the same university (backed by `university-chat-save` / `university-chat-load`
  endpoints in `profile_manager_v2/main.py` lines 753–805).

### 5.7 Add to My Schools

- From the university detail panel, click "Add to My Schools" (or the
  equivalent save button on the card).
- Assert: a success toast or visual confirmation appears.
- Navigate to `/launchpad`.
- Assert: the school appears in the college list.
- Assert: if the primary account is on the free tier and already has 3 schools,
  the "Add to My Schools" action is gated — an upgrade prompt appears instead
  (the free tier limit is `FREE_TIER_SCHOOL_LIMIT = 3` per
  `StratiaLaunchpad.jsx` line 40).

---

## 6. Profile Tab (`/profile`) — CRITICAL

The operator's first-impression flow (auth → discover → profile upload →
attribute population) is entirely concentrated here. Test this section with
precision — it is the most critical user journey on the platform.

### 6.1 Page load

- Navigate to `/profile`.
- Assert: the tab navigation bar renders with these five tab labels:
  **Upload Documents** | **View Profile** | **Profile Editor** |
  **Take Assessment** | **Self-Discovery**
  (from `Profile.jsx` lines 1075, 1087, 1099, 1110, 1122).
  Note: "View Profile" tab is hidden when the profile is empty
  (`!isProfileEmpty` guard at `Profile.jsx` line 1080).
- Assert: for a freshly-reset account, the "Upload Documents" tab is active by
  default (auto-switch logic at `Profile.jsx` lines 183–186).
- Assert: an upload drop zone is visible on the "Upload Documents" tab.

### 6.2 Upload

**Fixture files used in this section:**

- `tests/fixtures/profile-samples/sample-junior-comprehensive.pdf`
- `tests/fixtures/profile-samples/sample-sophomore-partial.docx`

**Supported formats** (from `ProfileBuilder.jsx` upload handler):
`.pdf`, `.docx`, `.txt`.

**Step A — PDF upload:**

1. On the "Upload Documents" tab, drag-and-drop
   `sample-junior-comprehensive.pdf` onto the upload zone, or use the file
   picker.
2. Assert: a progress indicator appears during processing.
3. Assert: upon completion, a success status message appears (no error
   banner).
4. Assert: switching to the "View Profile" tab (which should now be visible)
   shows non-empty content.

### 6.3 Attribute extraction verification — Fixture A (junior comprehensive)

After uploading `sample-junior-comprehensive.pdf`, navigate to the
"Profile Editor" tab (renders `ProfileBuilder` component) and expand each
section. Verify the following values populated:

**Basics section** (ProfileBuilder section label: "Basics"):

| Field (UI label) | Expected value |
|---|---|
| Full Name | Alex Rivera |
| Current Grade | 11 |
| High School | Riverside High School |
| City, State | Lakewood, CA |
| Graduation Year | 2026 |
| Intended Major | Computer Science |

**Academics section** (ProfileBuilder section label: "Academics"):

| Field (UI label) | Expected value |
|---|---|
| Weighted GPA | 4.28 |
| Unweighted GPA | 3.95 |
| UC GPA | 4.15 |
| Class Rank | 12/410 |

**Test Scores section** (ProfileBuilder section label: "Test Scores"):

| Field (UI label) | Expected value |
|---|---|
| SAT Total | 1480 |
| SAT Math | 780 |
| SAT Reading/Writing | 700 |
| ACT Composite | 33 |

**AP Exams section** (ProfileBuilder section label: "AP Exams"):

| Subject | Score |
|---|---|
| AP Computer Science A | 5 |
| AP Calculus BC | 5 |
| AP United States History | 4 |
| AP English Language | 4 |
| AP Statistics | 4 |
| AP Chemistry | 3 |

**Courses section** (ProfileBuilder section label: "Courses"):
Assert at least 10 course entries are present, drawn from the fixture's
13 courses. For each entry, the "Type" field should reflect the course
classification extracted by Gemini (AP courses → "AP"; Honors courses →
"Honors"). Exact course-by-course enumeration is not required — spot-check
3 courses:

| Course Name | Type | Grade Level |
|---|---|---|
| AP Computer Science A | AP | 10 |
| AP Calculus BC | AP | 11 |
| Honors English 9 | Honors | 9 |

**Activities section** (ProfileBuilder section label: "Activities",
Firestore field: `extracurriculars`):

| Activity | Role | Hours/Week |
|---|---|---|
| Robotics Team | Captain | 10 |
| Computer Science Club | President | 5 |
| Varsity Cross Country | Member | 8 |
| Coding for Community | Co-Founder | 3 |

**Awards & Honors section** (ProfileBuilder section label: "Awards & Honors"):
Assert at least 3 awards are present. Spot-check:

| Award | Level |
|---|---|
| USACO Gold Division Qualifier | National |
| National Merit Commended Scholar | National |
| Regional Science Fair — 1st Place | Regional |

**Grounding note:** The extraction code (`profile_extraction.py` lines 132–205)
uses Gemini to extract a flat JSON schema that maps directly to the fields
above. The schema explicitly includes `class_rank` (line 143),
`leadership_roles` (line 172), `special_programs` (line 173–175),
and `work_experience` (lines 176–181). These additional fields are captured
in Firestore but do not have dedicated ProfileBuilder UI sections; they are
available in the raw profile document. **The plan does NOT include a
verification table for `leadership_roles`, `special_programs`, or
`work_experience` because no ProfileBuilder section renders them.**

**Attributes verified in plan vs. original aspirational list:**

| Attribute | Status |
|---|---|
| Basics (name, grade, school, location, grad year, major) | Verified — in schema + UI |
| Academics (weighted GPA, unweighted GPA, UC GPA) | Verified — in schema + UI |
| Class rank | Verified — in schema (`class_rank` line 143) + UI (ProfileBuilder "Class Rank" field) |
| Test scores (SAT total, math, reading; ACT) | Verified — in schema + UI |
| AP exams (subject + score) | Verified — in schema + UI |
| Courses (name, type, grade level, semester grades) | Verified — in schema + UI |
| Activities (name, role, grades, hours/week, description) | Verified — in schema (`extracurriculars`) + UI ("Activities") |
| Awards (name, grade, level) | Verified — in schema + UI |

### 6.4 Round-trip integrity

- After completing the upload and seeing extracted attributes:
- Sign out of the app.
- Sign back in as `stratiaadmissions@gmail.com`.
- Navigate to `/profile` → "Profile Editor" tab.
- Assert: all attributes from §6.3 are still populated — confirming Firestore
  persistence survived the auth cycle.
- Network: open DevTools → Network; confirm a `GET .../get-profile?user_email=...`
  request returns HTTP 200 with a non-null `profile` field.

### 6.5 Manual edit and persistence

- In the "Profile Editor" tab, change the Weighted GPA field from `4.28` to
  `4.30`.
- Click the save button (or trigger the field-update call).
- Assert: a success indicator appears.
- Hard-refresh the page (`Cmd+Shift+R` / `Ctrl+Shift+R`).
- Navigate back to "Profile Editor".
- Assert: Weighted GPA field shows `4.30` (the edit persisted).

### 6.6 Take Assessment (GuidedInterview)

- Click the "Take Assessment" tab (renders `GuidedInterview` component).
- Assert: a multi-step question form appears.
- Answer at least the first 2 questions and advance.
- Assert: clicking "Finish" or "Complete" calls `onProfileUpdate` and the
  "Profile Editor" tab reflects the answered fields.

### 6.7 Self-Discovery chat

- Click the "Self-Discovery" tab (chat interface).
- Assert: a chat input is visible with a header reading "Self-Discovery"
  (from `Profile.jsx` line 1201).
- Send message: `"What are my strongest academic subjects based on my profile?"`
- Assert: a non-empty response appears within 15 seconds.
- Assert: the response references data from the uploaded profile (e.g., mentions
  Computer Science or the student's GPA), confirming the `profile-chat`
  endpoint (`profile_manager_v2/main.py` line 532) is pulling the real profile.

### 6.8 Fixture B — Sophomore partial (upload and attribute spot-check)

1. Reset the profile (§2.4 "Reset Profile" button).
2. Upload `tests/fixtures/profile-samples/sample-sophomore-partial.docx`.
3. Assert: upload succeeds without error.
4. Navigate to "Profile Editor" tab. Verify:

| Field | Expected value |
|---|---|
| Full Name | Morgan Chen |
| Current Grade | 10 |
| High School | Mountain View Academy |
| Graduation Year | 2027 |
| Intended Major | Biology / Pre-Med |
| Weighted GPA | 3.80 |
| Unweighted GPA | 3.60 |

5. Assert: SAT Total, SAT Math, SAT Reading, ACT Composite are all empty/null
   (fixture has no test scores — verifies the extractor does not hallucinate
   scores).
6. Assert: AP Exams section is empty or shows 0 entries.
7. Assert: at least 2 activity entries are present (Science Olympiad, Hospital
   Volunteer).

### 6.9 Negative: unsupported file format

- Attempt to upload a file with extension `.exe` (rename any small binary).
- Assert: the upload is rejected with a user-facing error message before any
  API call is made (client-side validation).
- Assert: the page does not crash; the upload zone remains functional after
  the rejection.

### 6.10 Negative: oversize file

**Code grounding:** No explicit `MAX_CONTENT_LENGTH` or byte-count check exists
anywhere in the upload path. The `profile_manager_v2` upload handler
(`main.py` lines 134–165) calls `file.read()` without inspecting
`len(file_content)`. The client-side upload zone (`Profile.jsx` line 1499) only
applies an `accept=".pdf,.docx,.txt,.doc,.md,.markdown"` MIME filter — no
JavaScript size validation. The effective hard ceiling is the **Cloud Functions
Gen2 32 MB HTTP request body limit**, enforced by the GCP runtime
infrastructure, not by application code.

**Test steps:**

1. Create a file that is over 32 MB (e.g., pad a `.txt` file:
   `dd if=/dev/urandom of=big.txt bs=1M count=33` on macOS/Linux, then rename
   to `big.pdf`).
2. Attempt to upload it via the "Upload Documents" tab.
3. Assert: the upload fails. Expected behavior — one of two outcomes:
   a. The GCP runtime returns HTTP 413 before the function processes the
      request. The frontend catches the network error and displays a generic
      error banner ("All uploads failed" per `Profile.jsx` line 720–722 error
      state).
   b. The browser itself stalls or the upload takes extremely long before
      timing out.
4. Assert: the page does not enter a permanently broken state — the upload
   zone is still functional after the failure.
5. Assert: NO in-app size error message appears (because none exists in code).
   If a size-specific message DOES appear, that would indicate new validation
   was added — update this step accordingly.

**Coverage note:** The absence of an in-app size limit is itself a test finding.
If a future PR adds explicit size validation, this step should be updated to
assert the specific error message and byte threshold. File a
`enhancement,backlog` issue if the 32 MB limit is reached in real usage.

---

## 7. Launchpad (`/launchpad`)

### 7.1 Saved-schools list

- Ensure the primary account has at least 3 schools saved (add them from
  Discover if needed after the profile reset in §6).
- Navigate to `/launchpad`.
- Assert: each school card renders with: university name, fit category badge
  (SAFETY / TARGET / REACH / SUPER_REACH, or "Analyzing..." if fit not yet
  computed).

### 7.2 Category filter

- The filter tabs (from `StratiaLaunchpad.jsx` lines 488–492):
  **All Schools** | **Reach** | **Target** | **Safety**
- Click "Reach" filter.
- Assert: only schools with fit category REACH or SUPER_REACH are shown
  (both map to the "Reach" bucket in the filter).
- Click "All Schools".
- Assert: all saved schools reappear.

### 7.3 Fit Analysis Modal

- From a school card, trigger the fit analysis (click "Analyze Fit" or the
  fit score badge if a fit is already computed).
- Assert: the `FitAnalysisModal` renders.
- Assert: the **four factor scores** are present, labeled, and within bounds
  (sourced from `fit_assertions.py` lines 43–49, module constants
  `_EXPECTED_FACTORS`):

  | Factor | Minimum | Maximum |
  |---|---|---|
  | Academic | 0 | 40 |
  | Holistic | 0 | 30 |
  | Major Fit | 0 | 15 |
  | Selectivity | -15 | +5 |

- Assert: a `match_percentage` value is shown as a number in [0, 100].
- Assert: the `fit_category` displayed matches the category on the card
  (SAFETY / TARGET / REACH / SUPER_REACH — from `fit_assertions.py` line 32).
- Assert: `match_percentage` falls within the band for its category
  (from `_CATEGORY_MATCH_RANGES` at `fit_assertions.py` lines 35–40):

  | Category | Match % range |
  |---|---|
  | SAFETY | 75–100 |
  | TARGET | 55–74 |
  | REACH | 35–54 |
  | SUPER_REACH | 0–34 |

- Assert: the advisory blocks are non-empty — specifically `explanation`,
  `essay_angles`, `application_timeline`, `test_strategy`, `major_strategy`,
  `recommendations` should all contain text (these are the "strict tier"
  blocks per `fit_assertions.py` lines 64–71).

### 7.4 Fit Chat widget

- From the Launchpad with a school card selected or within the
  `FitAnalysisModal`, locate the Fit Chat widget.
- Send: `"What should I focus on to strengthen my application to this school?"`
- Assert: a non-empty response appears within 15 seconds.
- Assert: the response references the specific university and at least one
  factor from the fit analysis (Academic, Holistic, etc.), confirming the
  `fit-chat` endpoint is passing university context.

### 7.5 Free-tier paywall at 3-school cap

- If the primary account is on the free tier:
- With exactly 3 schools saved, attempt to add a 4th school from Discover.
- Assert: an upgrade prompt appears instead of the normal save confirmation
  (from `StratiaLaunchpad.jsx` line 401: the action is blocked when
  `isFreeTier && collegeList.length >= FREE_TIER_SCHOOL_LIMIT`).
- Assert: clicking "Upgrade" in the prompt navigates to the pricing page
  or opens the `UpgradeModal`.

### 7.6 Credits tracker

- Locate the `CreditsBadge` in the navbar.
- Assert: the displayed credit count matches the value returned by
  `GET /get-credits?user_email=<email>` from `profile_manager_v2`
  (`profile_manager_v2/main.py` line 469).
- After spending a credit (e.g., by running a fit analysis on a new school):
- Assert: the badge decrements by 1 within 10 seconds of the action completing.

---

## 8. Roadmap (`/roadmap`)

The Roadmap surface is a single route with four inner tabs. Tab IDs and labels
(from `RoadmapPage.jsx` lines 44–47):

| Tab ID | Label |
|---|---|
| `plan` | Plan |
| `essays` | Essays |
| `scholarships` | Scholarships |
| `colleges` | Colleges |

Tab state is URL-driven: `?tab=plan`, `?tab=essays`, etc.

### 8.1 Plan tab (`/roadmap?tab=plan` or `/roadmap`)

- Navigate to `/roadmap` (default tab is `plan`).
- Assert: URL is `/roadmap?tab=plan` or `/roadmap` with the Plan tab
  highlighted.
- Assert: the `PlanTab` component renders. Look for a "This Week Focus"
  heading or card (from the RoadmapPage comment at line 42).
- Assert: if a roadmap plan has been generated for the user, semester-level
  boards or task lists are visible.
- Assert: if no roadmap exists yet, an empty-state prompt or "Generate Plan"
  CTA appears — not a blank white page.

### 8.2 Essays tab (`/roadmap?tab=essays`)

- Click "Essays" tab or navigate to `/roadmap?tab=essays`.
- Assert: `EssayDashboard` renders (embedded mode per `RoadmapPage.jsx`
  line 111: `<EssayDashboard embedded />`).
- Assert: if the primary account has schools with essay prompts in the tracker,
  essay entries are listed by school name.
- Assert: clicking into a specific school's essay entry opens the essay
  detail view.

### 8.3 Essay Help (`/essay-help/:universityId`)

- From the Essays tab, click into a school's essay prompt, or navigate
  directly to `/essay-help/<universityId>` where `<universityId>` is a school
  ID in the user's college list.
- Assert: `EssayHelpPage` renders at the route
  `/essay-help/:universityId` (confirmed in `App.jsx` line 207).
- Assert: at least one essay prompt is visible for the university.
- Click "Generate Starters" or the equivalent CTA.
- Assert: 2–4 essay starter hooks appear within 15 seconds.
- Select one starter and click "Get Feedback" or equivalent.
- Assert: a non-canned AI feedback response appears that references the
  selected hook or the essay prompt text.
- If an authenticity score is present, assert it is a number in [0, 100].

### 8.4 Scholarships tab (`/roadmap?tab=scholarships`)

- Click "Scholarships" tab.
- Assert: `ScholarshipTracker` renders (embedded mode, per `RoadmapPage.jsx`
  line 112).
- Assert: a search or filter input is visible.
- Assert: scholarship entries render with deadline dates.
- Toggle a scholarship's status (e.g., from "Not Started" to "Interested").
- Assert: the status change persists after switching tabs and returning.

### 8.5 Colleges tab (`/roadmap?tab=colleges`)

- Click "Colleges" tab.
- Assert: `ApplicationsPage` renders (embedded mode).
- Assert: each saved school appears with an application status.
- Change one school's status from "Not Started" to "In Progress"
  (via `update-application-status` endpoint in `profile_manager_v2/main.py`
  line 954).
- Assert: the status badge updates immediately.
- Hard-refresh or switch tabs and return.
- Assert: the "In Progress" status persisted.

### 8.6 Floating Counselor Chat

The `FloatingCounselorChat` component (`RoadmapPage.jsx` line 119) persists
across all Roadmap tabs.

- Assert: a floating chat icon or button is visible on all four Roadmap tabs.
- Click to open the chat.
- Send: `"What should I focus on this week given my saved schools and grade level?"`
- Assert: a non-empty response appears within 15 seconds.
- Assert: the response references at least one piece of user-specific context
  (grade level, a saved school name, or a pending task) — not a generic "I
  don't know your profile" message.

---

## 9. Payment & Credits (`/pricing` → Stripe → `/payment-success`)

> **Caution:** This section involves Stripe Checkout on the live tenant.
> Coordinate with the operator before running §9.2 if uncertain about which
> Stripe mode is active. See §3.5 pre-flight check.

### 9.1 Pricing page renders

- Navigate to `/pricing`.
- Assert: `PricingPage` renders tier cards (free, premium, etc.).
- Assert: each card shows a price in USD.
- Assert: a "Upgrade" or "Get Started" CTA is present on at least one
  paid tier card.

### 9.2 Stripe Checkout

- Click "Upgrade" on a paid tier.
- Assert: Stripe Checkout opens (either embedded or a redirect to
  `checkout.stripe.com`).
- Use a Stripe test card if the environment is confirmed to be in test mode
  (see §3.5). **Do NOT use a real payment card unless the operator explicitly
  instructs and the test account is set up for it.**
- Common test card (Stripe): `4242 4242 4242 4242`, any future expiry, any CVC.
- Assert: entering a valid test card and confirming does not produce an error.

### 9.3 Payment success page

- Assert: after a successful checkout, the browser redirects to
  `/payment-success` (route confirmed in `App.jsx` line 159).
- Assert: `PaymentSuccess` component renders a success message (not a 404
  or blank page).
- Assert: the `CreditsBadge` in the navbar reflects an increased credit
  balance (allow up to 30 seconds for the Stripe webhook to process and update
  Firestore, as noted in `docs/STRIPE_WEBHOOKS.md`).

### 9.4 Webhook delay handling

- If credit balance does not update within 30 seconds, wait an additional 30
  seconds and hard-refresh.
- If still not updated after 60 seconds total, log as a potential webhook delay
  issue in the run report (§12) but do not mark §9 as failed — webhook timing
  is environment-dependent.

### 9.5 Subscription cancellation (if applicable)

- If the product exposes a cancellation UI:
- Locate the cancellation option (likely in the Pricing page or a settings
  surface).
- Assert: initiating cancellation shows a confirmation step — not an
  immediate cancellation.
- Assert: after confirming cancellation, the credit balance or tier label
  reflects the cancelled state.

---

## 10. Resources (`/resources`)

### 10.1 Public access

- Open a new incognito window (signed out).
- Navigate to `https://stratiaadmissions.com/resources`.
- Assert: HTTP 200; `ResourcesPage` renders without requiring sign-in
  (the route is public per `App.jsx` line 164).
- Assert: a list of whitepapers or articles is visible.

### 10.2 Whitepaper deep-links

- Click on any whitepaper entry.
- Assert: the browser navigates to `/resources/<slug>` where `<slug>` is a
  non-empty path segment.
- Assert: `ResourcePaperPage` renders the paper content — not a 404.
- Optionally: navigate directly to a known slug URL.
  Assert: the page renders even without auth.

### 10.3 Auth-sensitive nav

- In the same incognito (signed-out) window, assert: the navigation bar shows
  only the Resources link and a "Try Stratia" or sign-in CTA — NOT the full
  five-tab nav (Profile, Discover, Launchpad, Roadmap, Resources).
  (Confirmed by `Navigation.jsx` comment at line 53:
  "today: just Resources. When logged in, every link is visible.")

---

## 11. Cross-Cutting Checks

### 11.1 Browser console — zero errors

- At the end of the full plan run, review all console entries captured in
  DevTools.
- Assert: no `[Error]` or `[Uncaught]` entries that were not already
  triaged during the run.
- Acceptable: `[Warning]` entries for development-mode React or minor
  deprecation notices.
- If any unrecognized error appears: screenshot the console, note the URL
  where it occurred, and file a `bug,qa` issue.

### 11.2 Network — no unexpected 4xx/5xx

- In DevTools → Network, filter by status 4xx and 5xx.
- Expected: a single 404 from `GET .../get-profile` when the account has no
  profile (from `profile_manager_v2/main.py` lines 253–257).
- Expected: a 401 from the incognito test in §4.6 (unauthenticated request).
- Not expected: any 500 from profile upload, fit analysis, essay generation,
  or payment flows.
- If unexpected 5xx appears: note the endpoint, request body, and response
  body. File as `bug,qa` issue.

### 11.3 Mobile viewport sanity (non-blocking)

- In DevTools, switch to the iPhone 14 preset (390×844) or use
  Cmd+Shift+M (Chrome) to toggle device mode.
- Walk the top-level nav (Profile, Discover, Launchpad, Roadmap).
- Assert: navigation is accessible (hamburger or scrollable nav, not clipped).
- Assert: no horizontal overflow (no scroll bar on the `<body>`).
- Do NOT block sign-off on mobile issues found here — file them as
  `enhancement,backlog` for PM/Designer.
- Designer Agent should review this section during its non-blocking read-pass.

### 11.4 A11y smoke (non-blocking)

- Press Tab through the navigation links on the landing page.
- Assert: keyboard focus ring is visible on each focused element.
- Press Tab through the sign-in button.
- Assert: focus does not get trapped or lost.
- Optional: install axe DevTools extension and run on `/universities` and
  `/profile`. Record the issue count per page (do not block sign-off on
  specific violations — file them for Designer follow-up).
- Designer Agent should review this section and §5.6, §7.4, §8.6 (chat
  widget accessibility) during its non-blocking read-pass.

### 11.5 Data teardown

At the end of the full plan run, document the state left in the primary test
account so the next run starts clean:

- [ ] Profile uploaded? Which fixture?
- [ ] Schools saved (list them).
- [ ] Application statuses changed from default?
- [ ] Credits balance (start vs. end).
- [ ] Any Stripe test payment made?

If another run is needed within the same day, use the "Reset Profile" button
in `/profile` to clear the uploaded profile and fit analyses before re-running
§6.

---

## 12. Run Report Template

Copy this template to a new file (e.g., `qa-run-2026-05-23.md`) and fill it
in as you run the plan. Screenshot and console-log evidence should be attached
inline or linked.

```
# QA Run Report — Stratia Admissions Browser Plan
Date: YYYY-MM-DD
Tester: <name>
Browser: Chrome <version>
Environment: https://stratiaadmissions.com (production)
Account: stratiaadmissions@gmail.com
Credits at start: X  |  Credits at end: Y
Profile fixture used: sample-junior-comprehensive.pdf / sample-sophomore-partial.docx / none

## Section results

| Section | Status | Notes / Evidence |
|---|---|---|
| 3. Pre-flight | PASS / FAIL / SKIP | |
| 4.1 Landing | PASS / FAIL / SKIP | |
| 4.2 OAuth popup | PASS / FAIL / SKIP | |
| 4.3 Post-auth landing | PASS / FAIL / SKIP | |
| 4.4 Onboarding modal | PASS / FAIL / SKIP | |
| 4.5 Sign-out | PASS / FAIL / SKIP | |
| 4.6 Incognito negative | PASS / FAIL / SKIP | |
| 5.1 Discover load | PASS / FAIL / SKIP | |
| 5.2 Search | PASS / FAIL / SKIP | |
| 5.3 Filters | PASS / FAIL / SKIP | |
| 5.4 SmartDiscoveryAlert | PASS / FAIL / SKIP | |
| 5.5 University detail tabs | PASS / FAIL / SKIP | |
| 5.6 AI chat widget | PASS / FAIL / SKIP | |
| 5.7 Add to My Schools | PASS / FAIL / SKIP | |
| 6.1 Profile load | PASS / FAIL / SKIP | |
| 6.2 Upload (PDF) | PASS / FAIL / SKIP | |
| 6.3 Fixture A extraction | PASS / FAIL / SKIP | |
| 6.4 Round-trip integrity | PASS / FAIL / SKIP | |
| 6.5 Manual edit | PASS / FAIL / SKIP | |
| 6.6 Take Assessment | PASS / FAIL / SKIP | |
| 6.7 Self-Discovery chat | PASS / FAIL / SKIP | |
| 6.8 Fixture B partial | PASS / FAIL / SKIP | |
| 6.9 Bad format negative | PASS / FAIL / SKIP | |
| 7.1 Launchpad load | PASS / FAIL / SKIP | |
| 7.2 Category filter | PASS / FAIL / SKIP | |
| 7.3 Fit Analysis Modal | PASS / FAIL / SKIP | |
| 7.4 Fit Chat | PASS / FAIL / SKIP | |
| 7.5 Paywall | PASS / FAIL / SKIP | |
| 7.6 Credits tracker | PASS / FAIL / SKIP | |
| 8.1 Plan tab | PASS / FAIL / SKIP | |
| 8.2 Essays tab | PASS / FAIL / SKIP | |
| 8.3 Essay Help page | PASS / FAIL / SKIP | |
| 8.4 Scholarships tab | PASS / FAIL / SKIP | |
| 8.5 Colleges tab | PASS / FAIL / SKIP | |
| 8.6 Counselor chat | PASS / FAIL / SKIP | |
| 9.1 Pricing page | PASS / FAIL / SKIP | |
| 9.2 Stripe Checkout | PASS / FAIL / SKIP | |
| 9.3 Payment success | PASS / FAIL / SKIP | |
| 9.4 Webhook delay | PASS / FAIL / SKIP | |
| 9.5 Cancel path | PASS / FAIL / SKIP | |
| 10.1 Resources public | PASS / FAIL / SKIP | |
| 10.2 Deep-links | PASS / FAIL / SKIP | |
| 10.3 Auth-sensitive nav | PASS / FAIL / SKIP | |
| 11.1 Console errors | PASS / FAIL / SKIP | |
| 11.2 Network 4xx/5xx | PASS / FAIL / SKIP | |
| 11.3 Mobile viewport | PASS / FAIL / SKIP | |
| 11.4 A11y smoke | PASS / FAIL / SKIP | |

## Overall result
PASS / FAIL / PARTIAL

## Issues filed this run
- #N — <title>

## Data state at end of run
Profile: <uploaded / reset / not touched>
Schools saved: <list>
Credits: <X>
Stripe test payment: <yes / no>
```

---

## 13. Automation Handoff

### 13.1 Existing Playwright infrastructure

The repo has a single E2E spec:
`frontend/tests-e2e/roadmap.spec.js` (covers Roadmap only, local mode).

Config: `frontend/playwright.config.js`.

The local spec uses two auth-bypass mechanisms:
- `localStorage.__E2E_TEST_USER__` — sets the signed-in user without real OAuth.
- `page.route(...)` — intercepts API calls and returns mocked responses.

**Both mechanisms are LOCAL-ONLY.** They cannot be used against
`stratiaadmissions.com` — the production Firebase Auth will reject the fake
token and the Cloud Functions will receive real (not mocked) requests.

### 13.2 Real-OAuth automation pattern

To automate the browser-based plan against production:

1. Sign in manually as `stratiaadmissions@gmail.com` once.
2. Save the browser state:
   ```
   npx playwright codegen --save-storage=auth.json https://stratiaadmissions.com
   ```
3. In each spec file, load the saved state:
   ```js
   test.use({ storageState: 'auth.json' });
   ```
4. `auth.json` contains Firebase ID tokens and cookies; treat it as a secret
   (add to `.gitignore`, rotate periodically).

### 13.3 API-level coverage complement

The 18 QA-agent scenarios in `cloud_functions/qa_agent/scenarios/` cover
backend data flows (fit computation, profile operations, essay generation) as
a synthetic backend user. They are the complement to browser tests, not a
substitute. See `cloud_functions/qa_agent/system_knowledge.md` for the
endpoint map.

### 13.4 Suggested new Playwright spec files

One spec per top-level surface, each building on the pattern in
`roadmap.spec.js`:

| Spec file | Sections it covers |
|---|---|
| `frontend/tests-e2e/auth.spec.js` | §4.1–4.6 |
| `frontend/tests-e2e/discover.spec.js` | §5.1–5.7 |
| `frontend/tests-e2e/profile.spec.js` | §6.1–6.9 (upload uses fixtures from `tests/fixtures/profile-samples/`) |
| `frontend/tests-e2e/launchpad.spec.js` | §7.1–7.6 |
| `frontend/tests-e2e/roadmap.spec.js` | Expand existing spec to cover §8.1–8.6 against production |
| `frontend/tests-e2e/resources.spec.js` | §10.1–10.3 |

The payment flow (§9) is intentionally omitted from automation — Stripe
Checkout automation against production requires operator coordination and
is typically done only in staging with test mode keys.

### 13.5 Fit bounds as assertions

The factor bounds and category-match-% ranges in
`cloud_functions/qa_agent/fit_assertions.py` (lines 35–49) should be imported
or duplicated as constants in `launchpad.spec.js` for the UI-level assertions
in §7.3. They are the ground truth — do not hardcode different values.

---

## Appendix — Route reference

Confirmed routes from `frontend/src/App.jsx`:

| Route | Component | Auth required |
|---|---|---|
| `/` | LandingPage | No |
| `/pricing` | PricingPage | No |
| `/payment-success` | PaymentSuccess | No |
| `/resources` | ResourcesPage | No |
| `/resources/:slug` | ResourcePaperPage | No |
| `/profile` | Profile | Yes |
| `/universities` | UniversityExplorer ("Discover" in nav) | Yes |
| `/launchpad` | StratiaLaunchpad | Yes |
| `/roadmap` | RoadmapPage | Yes |
| `/essay-help/:universityId` | EssayHelpPage | Yes |
| `/qa-runs` | QaRunsListPage (admin only, no nav entry) | Yes + admin |

Legacy redirects (from `App.jsx` lines 202–205, all redirect to `/roadmap?tab=...`):

| Old path | Redirects to |
|---|---|
| `/counselor` | `/roadmap?tab=plan` |
| `/progress` | `/roadmap?tab=essays` |
| `/essays` | `/roadmap?tab=essays` |
| `/applications` | `/roadmap?tab=colleges` |

---

*This document is the canonical pre-release sign-off checklist for Stratia Admissions.
Update it whenever a route changes, a new UI section ships, or an extraction attribute
is added or removed. The document must stay synchronized with
`cloud_functions/profile_manager_v2/profile_extraction.py` (the extraction schema),
`frontend/src/components/ProfileBuilder.jsx` (the UI field map), and
`cloud_functions/qa_agent/fit_assertions.py` (the fit bounds).*
