# DESIGN — Verified caller identity for the Stratia backends

- Status: implemented (issue #223)
- Date: 2026-07-02
- Related: `docs/RUNBOOK-stratia-connector-go-live.md` §9 (the pre-go-live
  caveat this closes), #285/#296 (server-side billing — deductions now ride a
  verified identity), #298/#299 (ledger safety)

## Problem

The live backends (`profile-manager-v2`, `counselor-agent`,
`knowledge-base-manager-universities-v2`) are public `*.run.app` URLs deployed
`--allow-unauthenticated`, and every per-user route derived identity from a
caller-supplied `X-User-Email` header / `user_email` field. Anyone on the
internet could read or mutate **any** student's data — profile, essays, fits,
credits — by setting a header (IDOR). The connector and frontend both verify
the human (Google OAuth / Firebase), but nothing downstream checked anything.

## Design

One verification module, `request_auth.py`, an identical copy in each backend
(repo doctrine: no shared packages across independently-deployed functions).
Two credential classes, routed by the token's issuer and verified with
`google.oauth2.id_token` against Google's published keys:

1. **User tokens** — Firebase ID tokens (issuer
   `securetoken.google.com/<project>`, audience = the Firebase project id).
   The token's own verified email **is** the identity. The frontend attaches
   it via an axios interceptor on every profile-manager/counselor call
   (registered on both the default axios object and the created instance —
   instances don't inherit global interceptors); the QA agent already minted
   real Firebase tokens for its test user, so it needed zero changes.
2. **Service tokens** — Google-signed OIDC tokens minted by a caller's
   runtime service account (`fetch_id_token` from the metadata server),
   **audience-bound to the callee's URL**. Accepted only when the token's
   `email` is in `TRUSTED_SERVICE_EMAILS` AND its `aud` is in the callee's
   `SELF_AUDIENCES` — a token minted for service A can never be replayed
   against service B (confused-deputy guard). A verified service caller
   vouches for the `X-User-Email` it forwards, because it verified the human
   upstream (connector: Google OAuth + DCR; counselor: this same gate).

**The verified identity scopes access** (AC3): when a user token is present,
a claimed email that doesn't match it is rejected — the raw header can never
widen access beyond the credential.

### Per-service policy

| Service | Gate |
|---|---|
| profile_manager_v2 | Every route except `health` and `clear-test-data` (which keeps its own X-Admin-Token gate). CORS now allows `Authorization`. |
| counselor_agent | Every route except `health`. Outbound PM calls attach its own service OIDC token (`svc_auth.py`, cached ~55 min). |
| KB universities v2 | **Reads stay public** (no PII — issue non-goal). Writes (ingest, delete) require a trusted-service token **or** the `KB_WRITE_TOKEN` shared secret used by `scripts/ingest_universities.py` (`export KB_WRITE_TOKEN=$(gcloud secrets versions access latest --secret kb-write-token)`). |

### Rollout (AC4): AUTH_MODE = off | log | enforce

- `log` (deploy default): verify when a credential is present; log
  anonymous/invalid callers and identity mismatches; allow everything. The
  dual-accept window — callers migrate with zero downtime, and the logs
  prove cleanliness before the flip.
- `enforce`: no valid credential → 401; user-token identity mismatch → 403.
- `off`: emergency valve back to legacy behavior.

Flip procedure (per service, no code change):
```
AUTH_MODE=enforce ./deploy.sh profile-v2   # or:
gcloud functions deploy … --update-env-vars AUTH_MODE=enforce
```
Order: connector + frontend + counselor deploy first (they now send
credentials), watch `[AUTH] (log mode)` warnings until clean, then flip
profile-manager-v2 → counselor-agent → KB writes. Stale browser tabs from
before the frontend deploy re-authenticate on refresh (Firebase tokens are
attached per request; only never-refreshed sessions 401).

### Operational details

- Cert fetches honor Google's cache headers via `cachecontrol` (falls back to
  a plain session); tokens verified with 10s clock skew.
- Callers fail **open** on their side: if a caller can't mint a token (local
  dev, no metadata server), it sends none and the callee's AUTH_MODE decides.
  Callee failures fail **closed** in enforce mode.
- All caller SAs today: the default compute SA (connector, counselor) and
  `qa-agent@…` (which sends user tokens anyway). Set in deploy.sh.
- Env per backend: `AUTH_MODE`, `FIREBASE_PROJECT_ID`,
  `TRUSTED_SERVICE_EMAILS`, `SELF_AUDIENCES` (both the run.app and
  cloudfunctions.net URL forms — callers use whichever base they're
  configured with).

## Explicitly out of scope

- Reworking frontend Firebase auth (non-goal; we only attach the token).
- Public KB reads/search/batch/university-chat (no PII).
- payment_manager_v2 (Stripe webhooks are signature-verified; separate
  surface).
- Firestore security rules (frontend reads qa_runs only; backends use the
  Admin SDK path).

## Threat notes

- `/deduct-credit`, `/add-credits`, `/reset-all-profile` etc. were all
  anonymous-writable before this; in enforce mode they demand a matching
  user token or a trusted service.
- A compromised trusted service can still impersonate users (it vouches for
  X-User-Email) — inherent to the BFF pattern; the SA allowlist and audience
  binding keep that set to our own runtimes.
- Firebase ID tokens in the browser are bearer tokens scoped to this Firebase
  project; XSS remains the residual risk there, unchanged by this work.
