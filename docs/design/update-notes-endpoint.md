# Design: /update-notes endpoint

Status: Approved (shipped in PR #4, doc backfilled 2026-05-03)
Last updated: 2026-05-03
Related PRD: [docs/prd/update-notes-endpoint.md](../prd/update-notes-endpoint.md)

## Where it lives

`profile_manager_v2`. Notes are direct writes to user-owned Firestore documents — that's the data manager's job. `counselor_agent` would be the wrong home (it's read-side).

## Contract

```
POST /update-notes
Body: {
  user_email: string,
  collection: "roadmap_tasks" | "essay_tracker" | "scholarship_tracker"
              | "college_list" | "aid_packages",
  item_id: string,
  notes: string
}
```

Response (success):
```json
{ "ok": true, "updated_at": "2026-05-03T15:42:11.000Z" }
```

Response (error):
- `400` — unknown collection, missing `item_id`, missing `user_email`
- `404` — document `users/{uid}/<collection>/<item_id>` doesn't exist
- `500` — Firestore error

## Implementation

```python
WHITELIST = {
    "roadmap_tasks", "essay_tracker", "scholarship_tracker",
    "college_list", "aid_packages",
}

def update_notes(req):
    body = req.get_json()
    user_email = body["user_email"]
    collection = body["collection"]
    item_id    = body["item_id"]
    notes      = body.get("notes", "")

    if collection not in WHITELIST:
        return error(400, f"unknown collection: {collection}")

    uid = email_to_uid(user_email)        # existing helper
    doc_ref = (db.collection("users").document(uid)
                  .collection(collection).document(item_id))

    if not doc_ref.get().exists:
        return error(404, "item not found")

    updated_at = datetime.now(UTC).isoformat()
    doc_ref.update({                       # only these two fields
        "notes": notes,
        "updated_at": updated_at,
    })
    return {"ok": True, "updated_at": updated_at}
```

The whitelist + the explicit `update({"notes": …, "updated_at": …})` together enforce that no other field can be written, even if extra keys leak into the request body.

## Why a single endpoint instead of extending the existing ones

Alternative considered: add a `notes` field to each of `update-essay-progress`, `update-scholarship-status`, `update-task`, etc. Slightly less new code, but spreads notes-writing across five different endpoint shapes. Inconsistencies are inevitable (one endpoint accepts `notes` as the field name, another accepts `note`, etc.). The unified endpoint is the cleaner choice — and the client gets one function that takes `(collection, item_id, notes)` regardless of source.

## Idempotency

Writes the same value twice are idempotent at the data level — the document ends up identical. The `updated_at` timestamp does refresh on each call, but that's a feature (it doubles as a "user-touched-this" signal we may use later for sorting).

## Auth model

Same as the other `profile_manager_v2` endpoints — Firebase auth gate at the deploy layer, plus the `user_email → uid` lookup the function already does. No additional changes.

## Testing strategy

- Unit tests in `tests/cloud_functions/profile_manager_v2/test_firestore_db.py` (TestUpdateNotes*) cover:
  - Happy path for each of the five whitelisted collections (parametrized).
  - Unknown collection → 400.
  - Missing `item_id` → 400.
  - Document doesn't exist → 404.
  - Notes value is empty string → succeeds, clears field.
  - Notes value contains newlines, special chars → preserved.
- Firestore is stubbed in conftest, so tests run as fast pytest unit tests.

## Migration / rollout

No migration. The `notes` field already exists on every doc in every whitelisted collection (it's been there since those collections were created — just never UI-exposed). Rolling back is removing the endpoint; data stays where it is.

## Risks

- **Whitelist drift.** A future collection added to user data won't be writable through this endpoint until the whitelist is extended. Acceptable: we want the whitelist to be the gate.
- **`notes` overwriting concurrent writes.** Two browser tabs editing the same item's notes will race. Last-writer-wins, no merge. The notes field is single-author per item in practice (the student themself); accepting last-writer-wins is fine.
- **Endpoint name collision** with any future "add a note" feature (where notes might be a list). If we ever introduce notes-as-array, this endpoint stays as-is and a separate `/append-note` ships alongside.

## Alternatives considered

- **Per-collection endpoints**: rejected (above).
- **Generic `/update-field` endpoint with a field-name parameter**: rejected — opens a too-broad mutation surface to defend.
- **Client writes Firestore directly via Firebase SDK**: rejected — bypasses the server-side rules layer where we'd have to put equivalent enforcement, and we'd lose `updated_at` consistency.
