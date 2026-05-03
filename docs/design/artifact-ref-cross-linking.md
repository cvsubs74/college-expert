# Design: Artifact-ref cross-linking

Status: Approved (shipped in PR #12, doc backfilled 2026-05-03)
Last updated: 2026-05-03
Related PRD: [docs/prd/artifact-ref-cross-linking.md](../prd/artifact-ref-cross-linking.md)

## Shape

Every task object returned by `/roadmap` may carry an `artifact_ref`:

```json
{
  "id": "task_research_mit",
  "title": "Research MIT — programs, admissions, fit",
  "type": "core",
  "artifact_ref": {
    "type": "college" | "essay" | "scholarship" | "tab",
    "university_id": "mit",                              // when type=college
    "essay_id": "common_app_personal",                   // when type=essay
    "scholarship_id": "...",                             // when type=scholarship
    "tab": "colleges" | "essays" | "scholarships",       // when type=tab
    "label": "Open MIT",
    "deep_link": "/roadmap?tab=colleges&school=mit"
  }
}
```

Type semantics:

| `type` | Meaning |
|---|---|
| `college` | Points at a specific school card on the Colleges tab. |
| `essay` | Points at a specific row on the Essays tab. |
| `scholarship` | Points at a specific row on the Scholarships tab. |
| `tab` | Points at a tab as a whole (no specific item — used for "Verify materials" etc.). |

`label` is always present and is what the pill displays. `deep_link` is always present and is what the pill navigates to.

## Backend translation

In [cloud_functions/counselor_agent/planner.py](../../cloud_functions/counselor_agent/planner.py), `translate_task(template_task, college_context)` already produces per-school and per-essay tasks. This feature extends that translator to attach the `artifact_ref`:

- **`translate_rd_submission`** — for each non-UC college on the list, emits a "Submit <name> app" task with `artifact_ref = { type: 'college', university_id: <id>, label: 'Open <name>', deep_link: '/roadmap?tab=colleges&school=<id>' }`.
- **UC group submission** — emits a "Submit UC Application" task whose `artifact_ref.label` joins all UC names ("Open UC Berkeley, UCLA, UCSD") and whose `university_id` anchors at the alphabetically-first UC. `deep_link` points at that anchor.
- **`translate_essays`** — per-school supplemental-essay tasks get `type: 'college'` (the supplements live on the college's view); UC PIQs get `type: 'tab', tab: 'essays'` (no canonical per-essay row for PIQs).
- **`translate_verify_materials`** — `type: 'tab', tab: 'colleges'`.
- **Generic template tasks (no translation)** — no `artifact_ref` (the field is omitted, not set to null).

## Frontend rendering

`RoadmapView.jsx` (the timeline) renders each task. When `task.artifact_ref` is present, it appends a pill:

```jsx
{task.artifact_ref && (
  <button
    role="button"
    name={task.artifact_ref.label}
    onClick={() => navigate(task.artifact_ref.deep_link)}
  >
    {task.artifact_ref.label}
    <ChevronRightIcon />
  </button>
)}
```

The pill is small, green, with rounded corners — visually distinct from the task body so it's clearly a navigation affordance.

## Receiver: scrolling to the target item

Each receiving tab reads the target ID from URL params on mount and scrolls to it:

- Colleges tab — reads `?school=<id>`, scrolls to that school's card, and expands its mini-dashboard.
- Essays tab — reads `?essay_id=<id>`, scrolls to that row, highlights it briefly.
- Scholarships tab — reads `?scholarship_id=<id>`, same behavior.
- Tab-level (`?tab=…` only) — no scroll target; just lands on the tab.

Highlight: target row gets a `outline` ring for 1.5s after navigation, then fades. Helps the student visually confirm "yes, this is the thing I clicked from."

## Stable IDs

- `university_id` matches the keys used by the knowledge base v2 (Firestore-backed) — e.g., `mit`, `university_of_california_berkeley`. Already canonical.
- `essay_id` and `scholarship_id` use the Firestore document IDs of the respective tracker rows. Stable across sessions.

## Testing strategy

- **Unit (Python)** — `tests/cloud_functions/counselor_agent/test_planner.py` covers the translation: per-school RD task has the right `artifact_ref` shape; UC group task joins names; tab-level type is correct for `translate_verify_materials`; absence of `artifact_ref` for untranslated generic tasks. Plus the scenario tests (PR #18) assert on the rendered tree.
- **Vitest** — `RoadmapView` renders the pill when `artifact_ref` present, doesn't render it when absent, and clicking calls `navigate` with the right URL.
- **Playwright** — the E2E test (`roadmap.spec.js`) loads a junior-spring scenario, asserts the "Open MIT" pill is visible, and (in a future expansion) clicks it and verifies the Colleges tab is the destination.

## Risks

- **Stale `university_id`**. If the KB renames a school's ID, existing roadmap tasks would link to a missing target. Mitigation: KB ID changes are rare and would already break other systems; we'd handle it as a coordinated migration.
- **Empty college list with a translated task**. Can't happen — translation is gated on the college list being non-empty.
- **Pill click vs. task body click conflicts**. The task body itself isn't clickable in M1, so no conflict. If we add task-body clicks later, the pill will need `event.stopPropagation()`.

## Alternatives considered

- **Plain text in the task title** ("Submit MIT app, click here →"). Rejected: not as scannable, mixes content and navigation.
- **A dropdown listing every translated school** when one task covers multiple. Rejected: only the UC group task covers multiple, and even then the pill label conveys the set without an extra interaction.
- **Generic tasks remain untranslated** but add a "View on tab" button. Rejected: generic tasks aren't actionable until the student decides which school they refer to; the translation IS the point.
