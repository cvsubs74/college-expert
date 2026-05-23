# Scenario: profile_upload_pdf_processes_to_completion

**Test plan section:** §6.2  
**Auth required:** Yes (storageState)  
**Spec file:** `tests/playwright-prod/specs/profile.auth.spec.js`  
**Fixture:** `tests/fixtures/profile-samples/sample-junior-comprehensive.pdf`  
**Iteration:** 2

## Objective

Verify that uploading a supported PDF profile fixture completes successfully: the upload API call succeeds, processing finishes, and a success status message is visible. Does NOT assert specific extracted attribute values.

## Preconditions

- Authenticated as `stratiaadmissions@gmail.com` (via `auth-state/storageState.json`).
- Fixture file `sample-junior-comprehensive.pdf` exists at the path above.
- Profile may have existing data — this test does not require a reset account.

## Step-by-step actions

1. Navigate to `https://stratiaadmissions.com/profile`.
2. Click the "Upload Documents" tab if not already active.
3. Locate the file input (hidden behind the drag-drop zone).
4. Set the file input to `sample-junior-comprehensive.pdf` (3.32 KB).
5. If a separate "Upload" button is present, click it.
6. Wait up to 60 seconds for processing to complete.

## Expected outcomes

- A success message appears: "Successfully uploaded 1 file(s)" or similar text matching `/successfully uploaded/i`, `/complete/i`, or `/upload.*success/i`.
- No error banner is visible: text matching `/all uploads failed/i` or `/upload.*error/i` is absent.
- The page does not crash.

## Why attribute assertions are excluded

Finding F-9 from `docs/qa-runs/2026-05-23-stratia-browser-run.md` documented that the profile merge logic is asymmetric: scalar fields (name, school, GPA, test scores) are NOT overwritten when uploading to a populated account — only list fields (courses, AP exams, activities, awards) grow. This makes attribute-value assertions unreliable on an account with pre-existing data.

Verifying specific extracted values (the §6.3 attribute table for Alex Rivera) requires a freshly-reset account, which in turn requires either:
- The `/reset-all-profile` endpoint (manual UI reset — see §2.4 of the test plan).
- The `clear-test-data` endpoint widened to accept `stratiaadmissions@gmail.com` (follow-up issue filed).

Until a reliable reset path is in place, upload-success assertion is the correct scope for this scenario.

## Fixtures referenced

- `tests/fixtures/profile-samples/sample-junior-comprehensive.pdf` — Grade 11 student "Alex Rivera", full attribute coverage.

## Known edge cases

- Upload timeout: Gemini extraction on the backend can take 15–30 seconds. The spec uses a 60-second timeout.
- If the account has no profile at all, "Upload Documents" is the default active tab (no click needed). The spec clicks it regardless to be safe.
