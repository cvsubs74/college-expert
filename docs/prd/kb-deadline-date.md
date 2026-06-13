# PRD — Structured `deadline_date` in the university knowledge base

- Issue: #191
- Status: approved (design)
- Date: 2026-05-29

## Problem

University scholarship deadlines in the KB are stored as free-text strings
(`profile.financials.scholarships[].deadline`), e.g. `"January 15, 2026 (for the
entering class…)"`, `"November 1 (admission)"`, `"Varies; website states…"`,
`"Automatic consideration"`. Because there is no machine-readable date:

- The roadmap's "Upcoming Deadlines" can't compute days-left, so scholarship
  deadlines are **dropped** (after #187) or previously rendered as **"overdue"
  / "NaN days left"**.
- Application deadlines (`application_process.application_deadlines[].date`) are
  ISO but **stale** (2025 cycle), so for a current junior every school shows
  **"Passed"**.

Net: the student never sees real, upcoming, actionable deadlines.

## Goal

Give every deadline a reliable, machine-readable date for the **2026–27
application cycle**, sourced from trusted/official data, so the roadmap and
applications surfaces show accurate upcoming deadlines — without losing the
descriptive free-text that several UI surfaces display.

## Users / value

Students (esp. juniors) get a correct, forward-looking deadline list they can
plan against. Counselor/roadmap features become trustworthy.

## Scope

**Phase 1 (this effort) — pilot:**
- Add a structured `deadline_date` field to the scholarship schema (keep
  free-text `deadline`).
- Populate accurate 2026–27 deadlines for **Duke, Ohio State, UCSD, USC** from
  official sources; refresh those schools' application-deadline dates too.
- Make `planner.py` / `work_feed.py` consume `deadline_date`.
- Verify live in the app for the pilot schools.

**Phase 2 (later):** scale population to all ~191 universities in reviewed
batches using curated trusted sources.

## Non-goals

- Populating all 191 universities now.
- Changing how the frontend *displays* deadlines (it keeps rendering the
  free-text `deadline`).
- Re-running the bulk collector (`run_all_250_universities.py`) — it risks
  overwriting good data with LLM guesses.

## Cycle interpretation

The **2026–27 cycle** (a current junior applies fall 2026, enters fall 2027):
fall deadlines map to 2026 (e.g. Nov 1, 2026), winter/spring deadlines map to
2027 (e.g. Jan 15, 2027). Deadlines are looked up from official sources for that
cycle rather than blindly year-substituted.

## Acceptance criteria

- [ ] `Scholarship` model + collector prompt include `deadline_date`
      (ISO `YYYY-MM-DD`, nullable); `deadline` text retained.
- [ ] Pilot schools have accurate 2026–27 scholarship `deadline_date` and
      refreshed application-deadline `date`s, from official sources.
- [ ] `planner.py` / `work_feed.py` use `deadline_date` (roll forward if past;
      drop when null) instead of parsing free-text.
- [ ] Idempotent migration utility updates ONLY deadline fields via the KB save
      path (read-modify-write; no bulk re-research).
- [ ] Live verification: roadmap shows real upcoming scholarship deadlines for
      the pilot schools (no overdue / NaN / missing).

## Risks

- **Accuracy:** official deadlines must be verified; set `null` rather than
  guess. Mitigated by per-school review in the pilot.
- **Cycle drift:** deadlines change year to year; Phase 2 needs a refresh
  cadence (out of scope here, noted).
