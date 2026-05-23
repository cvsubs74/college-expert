# Scenario: launchpad_fit_modal_opens_with_bounds

## Objective

Verify that clicking the Fit/Explore/Analyze CTA on a saved school card in the
Launchpad opens the FitAnalysisModal, and that all factor scores and the match
percentage fall within the documented bounds from `fit_assertions.py`.

## Preconditions

- User is authenticated as `stratiaadmissions@gmail.com`.
- Account has at least one saved school with a computed fit analysis.
  (If no schools are saved, the test gracefully skips via `test.skip()`.)
- Fit analysis for the saved school(s) has been computed (not "Analyzing...").

## Step-by-step actions

1. Navigate to `https://stratiaadmissions.com/launchpad`.
2. Wait for greeting to appear.
3. Check if any school card is visible. If not, skip with message:
   "Account has no saved schools — cannot open FitAnalysisModal."
4. Click the first "Analyze Fit" / "Fit" / "Explore" button on a school card.
5. Wait up to 15 seconds for the FitAnalysisModal (role `dialog`) to open.
6. For each factor, locate its label and extract the numeric score:
   - **Academic**: assert value in [0, 40]
   - **Holistic**: assert value in [0, 30]
   - **Major Fit**: assert value in [0, 15]
   - **Selectivity**: assert value in [-15, +5]
7. Locate the match percentage (text matching `/\d+%/`).
8. Parse as float; assert value in [0, 100].
9. Identify the fit category label in the modal (SAFETY / TARGET / REACH / SUPER_REACH
   or Title Case equivalent).
10. Assert the match% falls in the category's documented range:
    - SAFETY: 75–100
    - TARGET: 55–74
    - REACH: 35–54
    - SUPER_REACH: 0–34

## Expected outcomes

- FitAnalysisModal opens without error.
- All four factor scores within documented bounds.
- Match% is a positive integer in [0, 100].
- Match% falls within the band for the displayed fit category.

## Fixtures referenced

None. Live production data (fit scores are computed by the backend).

## Known edge cases

- If the account has no saved schools, the test skips with a clear message.
  Add schools from Discover before re-running.
- If the fit analysis is still "Analyzing...", the modal may not show numeric
  scores. The spec waits 15 seconds for the modal; extend the timeout if the
  backend is slow on a cold start.
- Selectivity can be negative (down to -15). The numeric extraction regex
  handles negative numbers (`-?\d+`).
- Factor labels are extracted via text pattern. If the component renames a
  factor (e.g., "Major Fit" → "Major Match"), the regex must be updated.

## Related

- Test plan: `docs/qa-browser-test-plan.md` §7.3
- Ground truth: `cloud_functions/qa_agent/fit_assertions.py` lines 35-49
- Spec: `tests/playwright-prod/specs/launchpad.auth.spec.js` → `launchpad_fit_modal_opens_with_bounds`
- Iteration: 3
