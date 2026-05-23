# Scenario: cross_cutting_no_console_errors_authenticated_pass

## Objective

Verify that no unfiltered error-level browser console events occur while navigating
through the main authenticated surfaces: Profile, Discover, Launchpad, Roadmap
(Essays only), and Resources. Captures console errors across the full navigation pass
and reports any that don't match known/expected error patterns.

## Preconditions

- User is authenticated as `stratiaadmissions@gmail.com`.
- Auth storageState and Firebase IndexedDB tokens are loaded.
- Roadmap Plan tab is EXCLUDED from this pass (issue #123 is a known console error
  source). Once #123 is fixed, add `/roadmap?tab=plan` to the route list.

## Step-by-step actions

1. Register a `page.on('console', ...)` listener for `error`-level messages before
   any navigation.
2. Navigate sequentially through:
   - `/profile`
   - `/universities`
   - `/launchpad`
   - `/roadmap?tab=essays`
   - `/resources`
3. After each navigation, wait for `networkidle` (or fallback: 1,500 ms) to capture
   deferred errors.
4. After all navigations, filter out known/expected error patterns:
   - Firebase SDK auth token refresh noise (pattern: includes "firebase" AND "auth")
   - OAuth handler iframe errors (pattern: includes "firebaseapp.com")
   - React DevTools warnings (pattern: includes "react-devtools")
5. Assert the filtered error list is empty.

## Expected outcomes

- Zero unfiltered error-level console events across all 5 routes.
- Any errors matching the known filter patterns are silently excluded (not failures).

## Fixtures referenced

None. Live production state.

## Known edge cases

- Auth-related Firebase SDK console errors are expected during session restore.
  They are filtered out and do not cause test failure.
- The Roadmap Plan tab (#123) is excluded. Once #123 is resolved, add the Plan
  tab route and remove the Plan-tab exclusion note.
- `networkidle` may not resolve cleanly on SPAs with long-polling or WebSocket
  connections. The fallback 1,500 ms wait accommodates this.
- Prior run (2026-05-23): 4 console errors during OAuth flow + 2 during landing
  reload. Most are Firebase auth noise. These are covered by the filter.

## Related

- Test plan: `docs/qa-browser-test-plan.md` §11.1
- Issue #123: Roadmap Plan tab JS error (excluded from this pass)
- Spec: `tests/playwright-prod/specs/cross-cutting.auth.spec.js` → `cross_cutting_no_console_errors_authenticated_pass`
- Iteration: 3
