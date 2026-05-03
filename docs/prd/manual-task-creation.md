# PRD: Manual task creation

Status: Approved (shipped in PR #13, doc backfilled 2026-05-03)
Owner: Engineering
Last updated: 2026-05-03
Parent: [docs/prd/roadmap-consolidation.md](./roadmap-consolidation.md)

## Problem

The Plan tab's timeline shows tasks generated from the semester template. Real students have additional tasks the template doesn't know about — "Email coach about lacrosse recruiting Friday", "Get rec letter signed by Mr. Patel by 11/15", "Visit Northeastern's campus during fall break." Without a way to add tasks, students keep these in external apps and the Roadmap loses ground as their single source of truth.

## Goals

- A clearly-labeled "Add task" pill near the top of the Plan tab.
- Click → modal dialog with title, optional due date, optional notes.
- On submit, the task persists to the same `roadmap_tasks` Firestore collection the template tasks land in (so it shows up in the focus card too).
- The new task appears in the timeline immediately (refetch on success).

## Non-goals

- Editing or deleting tasks from this UI. Out of scope; users can mark tasks completed (existing functionality) and we can wire up edit/delete in a follow-up.
- Recurring tasks. Single-occurrence only.
- Subtasks / dependencies / tags. Title + due date + notes is the whole shape.
- Bulk task import.
- Assigning tasks to a counselor or parent. Single-author.

## Users

- Students adding their own context-specific tasks.

## User stories

1. *As a student remembering "I need to get my coach's recommendation letter sent in"*, I click "Add task," type a title and a due date, hit save, and see the task appear in my timeline within a second.
2. *As a student adding a task with no due date* (e.g., "Brainstorm essay topics"), the form lets me skip the date and the task shows up in the "Later" / unscheduled bucket.
3. *As a student with a flaky network*, the modal stays open with my entered values until the save succeeds. If it fails, I see a clear error and can retry without retyping.
4. *As a student finishing a manually-added task*, I check it off the same way I check off any template task.

## Success metrics

- Students with at least one manually-created task: meaningful percentage of active users (target ≥ 30% within 60 days of rollout).
- Save success rate ≥ 99%.
- Manually-added tasks appearing in the focus card on schedule (no separate code path required).

## Open questions

- Should manually-added tasks have a visual marker distinguishing them from template-derived tasks? Defer until a UX pass.
