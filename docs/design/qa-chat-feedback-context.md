# Design — QA Chat Feedback Context

Spec: docs/prd/qa-chat-feedback-context.md.

## Where the change lands

`cloud_functions/qa_agent/chat.py`:

- New helper `_load_feedback_context() -> dict` that wraps
  `feedback.active_items()` + `feedback.recently_dismissed_items()`,
  swallowing failures (chat must never crash on a feedback load).
- New helper `_format_feedback_context(active, dismissed) -> str` that
  renders both lists as a compact prompt section. Returns an explicit
  "(no operator feedback in scope)" string when both lists are empty
  so the LLM has plain text rather than an absent section.
- `handle_chat` calls the loader once at the top of each request,
  threads the formatted text into the prompt right after the run
  context.

The system prompt gets one extra sentence telling the LLM to cite
feedback by both `text` and `id` when relevant.

## Prompt shape (after this PR)

```
{system}

Recent QA runs (most recent first):
{runs}

Admin feedback (operator notes that steer the synthesizer):
- ACTIVE: fb_792b19c0 · applied 5/5 · "Focus on UC group treatment …"
- RETIRED: fb_fa136214 · applied 5/5 · last_run=run_… · "Make sure to cover …"

Conversation so far:
{history}

User: {question}
```

## Tests

`tests/cloud_functions/qa_agent/test_chat.py`:

- `_format_feedback_context` renders an active item + a retired item
  with the expected fields.
- Empty + empty input returns the explicit no-feedback fallback string.
- Truncates to a sensible cap (e.g. 10+10) so a long history doesn't
  blow the prompt budget.
- `handle_chat` happy path passes feedback context into `_call_gemini`
  alongside the existing run context (proven via a spy on the prompt).
- `_load_feedback_context` swallows feedback module exceptions and
  returns `{active: [], dismissed: []}` so chat stays available even
  when the feedback store is unhealthy.

## Risk

Negligible:
- Pure additive: chat keeps answering all existing questions.
- Empty-state fallback prevents prompt malformation.
- Try/except around the feedback load means a feedback outage doesn't
  cascade into a chat outage.
