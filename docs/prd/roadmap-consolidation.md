# PRD: Roadmap Consolidation

Status: Draft
Owner: Product
Last updated: 2026-04-30

## Problem

A student preparing college applications today moves between four separate routes that each track a fragment of their work: `/counselor` (semester roadmap), `/progress` (Essays + Scholarships sub-tabs), `/essays` (a duplicate of the Essays sub-tab), and `/applications` (per-school deadlines). Each surface stores user-entered state independently, so a student updating "I drafted my Stanford essay" in one place sees no reflection of that work in the others. The semester roadmap also runs on a hardcoded grade level (`'11th Grade'`) regardless of profile, and the `notes` field that exists on every relevant Firestore document is invisible in the UI.

The cost is friction at the moments students need calm and clarity most: as deadlines approach. Students miss tasks, lose track of which essay belongs to which school, and don't have a single place to write down the kind of context-rich notes ("Mom said to ask about merit aid before Nov 1") that make the difference in the final weeks.

## Goals

- One top-level navigation entry that subsumes all admissions tracking work.
- A default landing experience that shows the student what is urgent **right now**, so the first thing they see is what they should do next.
- First-class notes on every trackable item (essay, scholarship, college, semester task), surfacing data fields that already exist in Firestore.
- Semester and grade computed from the student's profile and today's date, never hardcoded.
- Cross-linking between roadmap tasks and their concrete artifacts (a "Draft personal statement" task in the timeline links to the matching row in the Essays tab).

## Non-goals

- New Firestore data model. Existing collections (`roadmap_tasks`, `essay_tracker`, `scholarship_tracker`, `college_list`, `aid_packages`) remain authoritative. No migrations.
- User-authored SMART goal-setting flow. The semester templates already produce SMART-shaped tasks; we expose them well rather than letting students invent their own framework.
- Calendar grid view, Kanban board, or Gantt visualization. The page is list-shaped on purpose.
- Counselor chat redesign. Chat moves to a floating launcher in M2 but its content is unchanged.

## Users

- **Primary**: high-school students applying to college. Typical session length 5-15 minutes, 2-4 sessions per week in peak season.
- **Secondary**: parents reviewing their child's progress. Same screens, no separate role today.

## User stories

1. *Focus*. As a student opening the app on a Tuesday afternoon, I see the 5-8 most urgent items across all my work — not the entire semester plan — so I can pick what to do this session in under 30 seconds.
2. *Plan*. As a student, I see my full semester laid out as a timeline of phases and tasks, with progress bars, so I understand where I am in the bigger picture.
3. *Essays*. As a student, I track every essay I owe (auto-populated from my college list) with status, word count, and free-form notes about my approach.
4. *Scholarships*. As a student, I track every scholarship I'm eligible for, with status and notes about application strategy.
5. *Per-college view*. As a student picking which school to work on next, I see a per-school dashboard with its deadlines, essay count, scholarship count, and overall progress.
6. *Cross-link*. As a student looking at a "Draft personal statement" task in the semester plan, I click it and land on the actual essay row with the prompt and word limit.
7. *Notes*. As a student, I capture context — "Mom recommended applying for merit aid", "Counselor said add leadership angle" — directly on the relevant item, and find it again next session.

## Functional requirements

### M1 (ships first)

**Route & navigation**
- New route `/roadmap` containing the consolidated experience.
- Top-level nav entry "Roadmap" replaces the current "Roadmap" (`/counselor`) and "Tracker" (`/progress`) entries.
- Old routes redirect: `/counselor`, `/progress`, `/essays`, `/applications` → `/roadmap`, optionally with a query param to land on the relevant inner tab (`/applications` → `/roadmap?tab=colleges`).

**Inner tabs (in this order, left to right)**
1. **Plan** (default) — semester roadmap timeline, with a "This Week" focus card pinned at the top.
2. **Essays** — current `EssayDashboard` content lifted in.
3. **Scholarships** — current `ScholarshipTracker` content lifted in.
4. **Colleges** — current `ApplicationsPage` content lifted in.

**Plan tab**
- "This Week" focus card at top: top 5-8 items across all collections, sorted by urgency. Each row shows title, due-date label ("Due in 3d"), source-collection icon, and a notes affordance.
- Below the focus card: the existing `RoadmapView` timeline, unchanged in structure.
- Grade and current semester computed from `profile.grade_level` + today's date. Replaces the hardcoded `'11th Grade'`.

**Notes everywhere**
- Inline notes affordance on every essay row, scholarship row, college card, and timeline task. Click the icon → expands a textarea. Saves on blur. Persists to the existing `notes` field on each collection (no schema change).

**Backend**
- New endpoint `GET /work-feed` on `profile_manager_v2`: aggregates `roadmap_tasks`, `essay_tracker`, `scholarship_tracker`, and per-college deadlines into a unified, sorted, paginated list. Powers the "This Week" focus card.
- New endpoint `POST /update-notes` on `profile_manager_v2`: writes to the `notes` field of any of the four collections, keyed by `{collection, item_id}`. (Or extend the existing per-collection update endpoints.)
- `counselor_agent` `/roadmap` endpoint reads `grade_level` from profile when `grade_level` is not provided in the request. Computes current semester (fall/spring/summer) from server-side date.

### M2 (separate PRs after M1)

- `artifact_ref: { type, id }` on template tasks. Generic tasks like "Draft personal statement" resolve to the user's specific essay row. Click → opens an inline drawer or jumps to the Essays tab focused on that row.
- Counselor chat moves to a floating launcher (bottom-right) accessible from any tab.
- Manual task creation: a "+ Add task" button on the Plan tab lets the student add custom tasks with title, due date, optional college link, and notes.
- Per-college expandable mini-dashboard within the Colleges tab (drill into a school without leaving the page).

## Success metrics

- Time to first useful action on the consolidated tab: median student picks an item within 30 seconds of landing. Measure via click-tracking on the "This Week" focus card.
- Cross-tab navigation reduction: track average tab switches per session. Target: median ≤ 2 (vs. the current ≥ 4 implied by the four-route layout).
- Notes adoption: % of active students who have written at least one note within two weeks of M1 launch. Target: ≥ 30%.
- Old-route traffic: redirects from `/counselor`, `/progress`, `/essays`, `/applications` should drop to under 5% of `/roadmap` traffic within a month, indicating bookmarks have updated.

## Out of scope

- Push notifications or email reminders for upcoming deadlines.
- Shared collaborator access (parents, counselors).
- Mobile-native app changes — web-responsive only.
- Bulk-edit or import/export of items.

## Open questions

- Should "This Week" be a permanent banner above the tab strip (always visible regardless of active tab) instead of living inside the Plan tab? Current decision: inside Plan, to keep the tab strip uncluttered.
- Should `/applications` redirect preserve the school the user was viewing? E.g., `/applications?school=stanford` → `/roadmap?tab=colleges&school=stanford`. Worth doing if old links are used externally; otherwise unnecessary.
- Does `/essays` need a separate redirect rule, or can it share the same handler as `/progress`?
