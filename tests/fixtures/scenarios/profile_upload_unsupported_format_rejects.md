# Scenario: profile_upload_unsupported_format_rejects

**Test plan section:** §6.9  
**Auth required:** Yes (storageState)  
**Spec file:** `tests/playwright-prod/specs/profile.auth.spec.js`  
**Iteration:** 2

## Objective

Verify that attempting to upload a file with an unsupported format (`.exe`) is rejected client-side before any API call is made. The upload zone should remain functional after the rejection.

## Preconditions

- Authenticated as `stratiaadmissions@gmail.com` (via `auth-state/storageState.json`).
- Supported formats per `Profile.jsx` line 1499: `.pdf`, `.docx`, `.txt`, `.doc`, `.md`, `.markdown`.
- No precondition on profile content.

## Step-by-step actions

1. Navigate to `https://stratiaadmissions.com/profile`.
2. Click the "Upload Documents" tab if not already active.
3. Locate the file input.
4. Set the file input to a synthetic `.exe` file: `malware.exe` (2 bytes, `MZ` magic bytes, `application/octet-stream` MIME type).
5. Observe the response within 5 seconds.

## Expected outcomes

- A client-side rejection message appears, matching one of:
  - `/unsupported.*format/i`
  - `/not supported/i`
  - `/invalid.*file/i`
  - `/file type/i`
- No "Successfully uploaded" message appears (no API call should have been made).
- The page does not crash.
- The file input remains attached (upload zone is still functional after rejection).

## Why client-side only

The Profile.jsx upload zone applies an `accept=".pdf,.docx,.txt,.doc,.md,.markdown"` MIME filter (line 1499). For browsers that enforce the `accept` attribute, `.exe` files are filtered before they reach the upload handler. The client-side rejection is the expected behavior — this scenario is a smoke test that the filter is in place.

If a browser bypasses the `accept` filter (some do), the file might reach the API. In that case the upload would likely fail with a server-side error. The spec's assertion pattern is broad enough to catch either path.

## Fixtures referenced

None — the test constructs a synthetic `.exe` buffer in-process using `Buffer.from('MZ')`.

## Known edge cases

- Different browsers handle `accept` attribute violations differently. Chromium (which this spec uses) typically fires the `change` event but the UI validation fires before the upload call.
- If the app adds a specific "unsupported file type" error message in the future, update this scenario's assertion pattern to match it exactly.
