# QA Feedback Credit Reliability — Multi-id Scenarios

## Problem

The synthesizer LLM occasionally emits `feedback_id` as a JSON array
(`["fb_a", "fb_b"]`) when a single generated scenario was designed to
address multiple admin-feedback items. The previous credit loop
appended the raw value into a flat list, so `mark_applied` was called
with a list-of-list — `set([["fb_a","fb_b"]])` raises
`TypeError: unhashable type: 'list'`. The error was swallowed by the
outer `except Exception` and logged as a warning, so the run completed
successfully but **no feedback got credited**.

Net effect on the operator: feedback that drove a multi-target scenario
silently doesn't show the "✓ applied" pill (PR #65) and never hits the
auto-dismiss threshold, so it sticks around the Steer panel forever.

## Goals

- Multi-target scenarios credit every referenced feedback item.
- Bad/unexpected shapes (`null`, ints, lists with non-strings) never
  raise; they're skipped silently.
- The synthesizer prompt acknowledges the list form so the LLM doesn't
  have to compress its intent.

## Non-goals

- Not changing the run-record schema. `feedback_id` continues to live
  on each scenario in either string or list form.
- Not retroactively crediting historical runs that hit the bug.

## Success criteria

- New unit tests in `test_main_endpoints.py::TestCollectFeedbackIds`
  cover string, list, mixed, dedupe, falsy, non-string-entry, empty.
- Production: a scheduled run that includes a list-form `feedback_id`
  bumps `applied_count` by 1 for each id (verifiable via /feedback).
