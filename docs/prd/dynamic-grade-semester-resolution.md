# PRD: Dynamic grade & semester resolution on /roadmap

Status: Approved (shipped in PR #5, doc backfilled 2026-05-03)
Owner: Engineering
Last updated: 2026-05-03
Parent: [docs/prd/roadmap-consolidation.md](./roadmap-consolidation.md)

## Problem

Until this feature shipped, `/roadmap` was hardcoded to `grade_level='11th Grade'` regardless of who was asking. A 9th grader, a senior, and a parent all received the same junior-spring template. The student's real grade lives in their profile (`graduation_year`), and today's date determines what semester they're in — both signals are available and just weren't being used.

## Goals

- A student's `/roadmap` response is computed from their actual grade and the current semester, every time.
- A frontend that already knows the right (grade, semester) pair (e.g., a future "show me what senior fall would look like" preview) can override.
- The endpoint never crashes when any of the inputs are missing — it picks a safe default and reports how it got there.

## Non-goals

- New templates. The 9 templates (`freshman_fall` through `senior_spring`, plus `junior_summer`) already exist; this feature just routes to the right one.
- Profile editing UI. Students set their `graduation_year` during onboarding; this feature reads it.
- Predicting what semester a student "should" be in based on transcript or course load. Strictly date-driven.

## Users

- Every caller of `POST /roadmap`, primarily the Plan tab on `/roadmap`.

## User stories

1. *As a junior in the spring semester*, my roadmap shows me junior-spring tasks (test prep, college research) — not the hardcoded 11th-grade template.
2. *As a freshman in October*, my roadmap shows me freshman-fall tasks (settle into HS, start an activity), not application-crunch tasks.
3. *As an already-graduated student still using the app*, the resolver clamps me to senior-spring instead of crashing or returning empty.
4. *As a frontend developer*, I can pass `grade_level` and `semester` explicitly and the endpoint honors my override.
5. *As a debugger*, the response tells me which template was chosen and how the resolver got there (`profile`, `caller`, `caller-grade-only`, or `default`).

## Success metrics

- Zero `/roadmap` requests served from the hardcoded `'11th Grade'` path post-rollout.
- Every response carries `metadata.template_used`, `metadata.grade_used`, `metadata.semester_used`, `metadata.resolution_source`.
- Test coverage for all 12 grade × semester combinations + the four resolution sources + the major edge cases (already-graduated, far-future grad year, summer-with-no-template, missing graduation_year).

## Open questions

- None at backfill time.
