# QA Chat — Feedback Context

## Problem

The Ask tab's chat is grounded in last-30-run summaries and answers
operator questions about pass-rate, failures, surface health, etc.
What it **doesn't** see today is the Steer panel's feedback items.

So an operator who asks "did my UC group treatment note drive any
runs?" gets a half-answer: the chat sees `feedback_id: fb_792b19c0`
stamped on synthesized scenarios in the run records, but it has no
way to map that opaque ID back to the operator's actual note text.

The chat answer becomes: *"Run X used feedback_id fb_792b19c0 — I
don't know what that note said."* That breaks the loop the Steer
panel was supposed to close.

## Goals

- Operator can ask "did my note about X drive any runs?" and get a
  concrete answer that quotes the original note text + cites the
  run IDs that referenced it.
- Operator can ask "what feedback retired today?" and get the list
  with applied counts.
- Backwards compatible: chat still answers everything it answered
  before; adding context, not changing prompt structure.

## Non-goals

- Not adding new chat features beyond grounding (no UI changes).
- Not overhauling the prompt format — additive only.

## Success criteria

- The chat prompt includes a `# ADMIN FEEDBACK` section listing
  active + recently-dismissed items with `id`, `text`, `applied_count`,
  `last_applied_run_id`, and status.
- A chat question that mentions feedback text or `feedback_id` returns
  an answer that joins both halves.
