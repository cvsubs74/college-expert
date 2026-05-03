# Design: Legacy route redirects

Status: Approved (shipped in PR #10, doc backfilled 2026-05-03)
Last updated: 2026-05-03
Related PRD: [docs/prd/legacy-route-redirects.md](../prd/legacy-route-redirects.md)

## Mapping

| Legacy URL | Redirects to |
|---|---|
| `/counselor` | `/roadmap?tab=plan` |
| `/progress` | `/roadmap?tab=essays` |
| `/essays` | `/roadmap?tab=essays` |
| `/applications` | `/roadmap?tab=colleges` |

Query params from the legacy URL pass through. `/applications?school=stanford` becomes `/roadmap?tab=colleges&school=stanford`.

## Implementation

In `frontend/src/App.jsx`, each legacy `<Route>` element is replaced with a `<Navigate replace>` that's parameterized to preserve query params:

```jsx
function LegacyRedirect({ tab }) {
  const [params] = useSearchParams();
  const next = new URLSearchParams(params);
  next.set('tab', tab);
  return <Navigate to={`/roadmap?${next.toString()}`} replace />;
}

// in the Routes block:
<Route path="/counselor"    element={<LegacyRedirect tab="plan" />} />
<Route path="/progress"     element={<LegacyRedirect tab="essays" />} />
<Route path="/essays"       element={<LegacyRedirect tab="essays" />} />
<Route path="/applications" element={<LegacyRedirect tab="colleges" />} />
```

The `replace` flag means the legacy URL never enters the browser history — back button skips it.

## Nav update

The header's `navLinks` array drops the four legacy entries and adds a single "Roadmap" entry pointing at `/roadmap`. Active-link highlight uses `react-router`'s `NavLink` so the entry stays highlighted across all four tabs.

## Testing strategy

- **Vitest**: `LegacyRedirect` renders a `<Navigate>` to the right destination given different `tab` props and URL params.
- **Playwright**: each legacy URL is loaded; the browser ends up on `/roadmap?tab=…` with the right tab content.
- **Manual**: verify `/applications?school=stanford` lands on the Colleges tab with the school param survived.

## Risks

- **A future tab name collision** with a legacy URL pattern. Unlikely (we own both sides) but worth watching if a new tab is named with a single word like `essays` or `colleges`.
- **Query param leakage** — a legacy URL with a `tab=` param would conflict with our injected one. Acceptable: we override it (the legacy URLs never had `tab=`, so this is a synthetic concern).
- **Cache headers / service worker**. The frontend doesn't ship with a service worker today; if we add one, we'd need to make sure cached HTML for the legacy URLs doesn't bypass the SPA bootstrap. Out of scope for now.

## Alternatives considered

- **Server-side redirects** (Firebase Hosting `rewrites`). Rejected: this is a SPA — every URL serves the same `index.html` and react-router handles the rest. Server rules wouldn't see the SPA-internal routing.
- **Keep the legacy routes alive in parallel.** Rejected: that's the world we just left. Splits user state across surfaces.
- **HTTP 301s.** N/A — no server-side routing for SPA paths.
