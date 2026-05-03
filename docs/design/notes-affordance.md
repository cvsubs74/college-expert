# Design: Inline notes affordance

Status: Approved (shipped in PR #9, doc backfilled 2026-05-03)
Last updated: 2026-05-03
Related PRD: [docs/prd/notes-affordance.md](../prd/notes-affordance.md)

## Component

`frontend/src/components/roadmap/NotesAffordance.jsx`

```jsx
<NotesAffordance
  collection="essay_tracker"
  itemId="essay-123"
  value={item.notes}     // current persisted value
  onSave={(newNotes) => { /* parent can refetch or update local state */ }}
/>
```

The component is the only thing call sites need to know. They pass the four props; the component handles fetch + render + save + revert.

## States

```
collapsed (default)
  ┌──────┐
  │ [📝] │  ← shows filled icon if value.length > 0, hollow otherwise
  └──────┘
        click ↓
expanded
  ┌──────────────────────────┐
  │ <textarea autofocus>     │
  │ ...your notes here...    │
  └──────────────────────────┘
        blur (or ⌘/Ctrl+Enter)
        ↓
saving (optimistic — UI already collapsed and shows new icon state)
        ↓
        success: stay
        failure: revert + toast "Couldn't save notes"
```

## Save path

```js
async function save(newNotes) {
  // Optimistic: update local state right away
  setLocalValue(newNotes);
  setExpanded(false);

  try {
    await axios.post(`${PROFILE_MANAGER_V2_URL}/update-notes`, {
      user_email,
      collection,
      item_id: itemId,
      notes: newNotes,
    });
    onSave?.(newNotes);
  } catch (err) {
    setLocalValue(previousValue);
    toast.error("Couldn't save notes");
  }
}
```

`previousValue` is captured when the textarea opens — so revert is always to the value the student saw before they started editing.

## Debounce

Blur events can fire rapidly (e.g., focus moves fast across nested fields). Debounce save calls at 500ms — if a second blur fires within that window with the same value, only one POST goes out.

## Keyboard

- `Cmd/Ctrl+Enter` saves and collapses immediately (parity with the chat-send convention).
- `Esc` cancels — collapses without saving, reverts to previous value.
- `Tab` blurs (which saves through the normal blur path).

## Visual

Filled icon when notes exist; hollow when empty. No per-tab styling — the component owns its look so it stays consistent across the Plan focus card, Essays rows, Scholarships rows, and Colleges cards.

## Embedding

The component is a leaf — it doesn't know about the Roadmap page or about react-router. It just needs:
- `collection` (the `/update-notes` whitelist value)
- `itemId`
- the current `value`
- an `onSave` callback (optional)

That contract makes it trivially droppable into any tab.

## Testing strategy

- **Vitest** in `frontend/src/__tests__/NotesAffordance.test.jsx`:
  - Click icon → textarea expands, autofocused.
  - Blur → POST `/update-notes` with the right payload.
  - Network error → reverts to previous value + shows toast.
  - Cmd+Enter saves and collapses.
  - Esc cancels and reverts.
  - Empty value vs. populated value renders different icons.
- All HTTP stubbed via `vi.mock('axios')`.

## Risks

- **Save vs. unmount race**. If the user clicks a tab away while a save is in flight, the parent unmounts the component before the response. Mitigation: the optimistic write already happened to local state; the `await` is fire-and-forget from the user's perspective, and the unmount doesn't break anything. Failure case: if the server rejects, the toast won't appear because the toast host might also have unmounted. Acceptable — that's a rare path with a small consequence.
- **Optimistic UI showing success that didn't happen**. We accept the tradeoff: the latency cost of "wait for server before showing collapsed" outweighs the rare wrong-state moment, and the revert path catches it.
- **Notes containing potentially sensitive content**. The `notes` field has the same Firestore security rules as the rest of the user document. No new exposure surface.

## Alternatives considered

- **Modal dialog instead of inline expand.** Rejected: too heavy for a single textarea. The inline-expand pattern keeps the user in context.
- **Auto-save on every keystroke (debounced).** Rejected: tons of network calls, no obvious win over save-on-blur for plain-text notes.
- **Notes as a separate route per item.** Rejected: kills the "I just want to drop a quick reminder" use case, which is the entire point.
