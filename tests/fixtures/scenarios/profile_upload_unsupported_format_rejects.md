# Scenario: profile_upload_unsupported_format_rejects

**Test plan section:** §6.9  
**Auth required:** Yes (storageState + Firebase IndexedDB bridge)  
**Spec file:** `tests/playwright-prod/specs/profile.auth.spec.js`  
**Iteration:** 2

## Objective

Verify that the Profile page's file input restricts uploads to supported formats via its HTML `accept` attribute. The attribute is the actual user-protection mechanism on this surface — `Profile.jsx` has no JavaScript-side file-format validation, so this static check validates the layer the user actually depends on for safety against accidental unsupported uploads.

**Why a static check, not a behavioral test:** the original design (set a synthetic `.exe` via `setInputFiles`, expect a rejection banner) does not work in automation. Browsers don't enforce the `accept` attribute on `setInputFiles` programmatic calls — they only honor it for the OS file picker dialog. And `Profile.jsx` has no JS validation to fall back on. So a behavioral negative-path test is unreliable; a static-check on the `accept` attribute correctly validates the safety mechanism that's in place.

## Preconditions

- Authenticated as `stratiaadmissions@gmail.com` (via `auth-state/storageState.json` + Firebase IndexedDB bridge).
- No precondition on profile content — the file input exists on the Upload Documents tab regardless of profile state.

## Step-by-step actions

1. Navigate to `https://stratiaadmissions.com/profile`.
2. Assert URL is `/profile` (auth state correctly applied).
3. Click the "Upload Documents" tab if not already active.
4. Locate the file input (`input[type="file"]`).
5. Read its `accept` attribute via `getAttribute('accept')`.

## Expected outcomes

The `accept` attribute on the file input must be present and (case-insensitively) contain:

- `.pdf` (supported format — must be allowed)
- `.docx` (supported format — must be allowed)
- `.txt` (supported format — must be allowed)

The `accept` attribute must NOT contain:

- `.exe` (user-facing safety guarantee — must be rejected by the OS file picker)

Per `Profile.jsx` ~line 1499, the live value is expected to be:

```
.pdf,.docx,.txt,.doc,.md,.markdown
```

(Other supported formats like `.doc`, `.md`, `.markdown` are not asserted explicitly — only that they're listed is a soft expectation. If the live value contracts to a subset that omits one of `.pdf`, `.docx`, `.txt`, this scenario fails and the change should be surfaced as either a deliberate UX change or a regression.)

## Fixtures referenced

None — pure DOM attribute read; no file is uploaded.

## Known edge cases

- If `Profile.jsx` adds JavaScript-side file-format validation in the future (e.g. a try/catch that surfaces a "Sorry, only PDF/DOCX/TXT supported" banner when a non-matching file is selected via drag-and-drop), this scenario should be expanded to also cover the JS-validation branch behaviorally. As long as the only safety mechanism is the `accept` attribute, the static check is the right test.
- The `accept` attribute is a UA HINT, not a security boundary. A motivated user can still upload anything by manipulating the input. Server-side validation in `profile_manager_v2` is what actually protects against malicious payloads — but that's out-of-scope for this browser-level scenario.

## Related

- Test plan reference: `docs/qa-browser-test-plan.md` §6.9
- Spec implementation: `tests/playwright-prod/specs/profile.auth.spec.js` (describe block `profile_upload_unsupported_format_rejects`)
- Prior run: PASS (the static check executed correctly against the live `accept` attribute)
