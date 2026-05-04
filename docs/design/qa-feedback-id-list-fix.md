# Design — Feedback Credit for Multi-id Scenarios

Spec: docs/prd/qa-feedback-id-list-fix.md.

## Change shape

Extract a small helper from the inline credit loop in
`cloud_functions/qa_agent/main.py::_handle_run`:

```python
def _collect_feedback_ids(scenarios) -> list:
    """Flatten scenario.feedback_id values into a deduped list of strings."""
    seen = []
    for scen in scenarios or []:
        fid = scen.get("feedback_id") if isinstance(scen, dict) else None
        if isinstance(fid, str):
            if fid and fid not in seen:
                seen.append(fid)
        elif isinstance(fid, list):
            for entry in fid:
                if isinstance(entry, str) and entry and entry not in seen:
                    seen.append(entry)
        # Anything else (None, int, dict, …) → skip silently.
    return seen
```

Order is first-seen so credit logging is deterministic across runs.

The caller becomes:

```python
feedback_ids_used = _collect_feedback_ids(chosen)
if feedback_ids_used:
    try:
        feedback_mod.mark_applied(feedback_ids_used, run_id=run_id)
    except Exception as exc:
        logger.warning("qa_agent: mark_applied failed (%s)", exc)
```

## Synthesizer prompt

Acknowledge the list form so the LLM doesn't have to choose between
omitting an attribution and over-compressing intent into a single id.
The relevant snippet in `_build_prompt`:

> If a scenario was designed to address an item from the ADMIN FEEDBACK
> section above, include the matching `feedback_id` in the scenario
> JSON (e.g. `"feedback_id": "fb_abc123"`). **If a single scenario
> addresses multiple feedback items, you may pass an array of ids
> instead (e.g. `"feedback_id": ["fb_abc123", "fb_def456"]`) — each
> will be credited.**

## Tests

`tests/cloud_functions/qa_agent/test_main_endpoints.py` adds
`TestCollectFeedbackIds`:

- single string ids
- list-form is flattened
- mixed list and string across scenarios
- dedupe across scenarios + within a list
- skips missing / None / "" / []
- drops non-string entries inside a list (None, ints)
- empty input → empty list

## Risk

Minimal — the helper is a pure function over already-validated data.
The previous behaviour swallowed the TypeError silently, so any caller
depending on the bug producing a no-op gets the right behaviour now.
