# RUNBOOK — Stratia connector go-live

Ordered steps to take the Stratia Admissions Claude connector
(`cloud_functions/stratia_connector/`) from merged code to a working connector
in Claude. Modeled on the proven ACP connector runbook.

Account/project: `cvsubs@gmail.com` / `college-counselling-478115`, region `us-east1`.
Service: Cloud Run `stratia-connector`. Base URL (current): `https://stratia-connector-pfnwjfp26a-ue.a.run.app`.

## 1. Ship code
Merge `cloud_functions/stratia_connector/` to `main`; CI auto-redeploys
(`detect_changed_targets` → `./deploy.sh stratia-connector`). Or deploy manually
from a clean `main`: `./deploy.sh stratia-connector`.

## 2. Create the Google OAuth client (one-time)
- **OAuth consent screen** (APIs & Services → OAuth consent screen): External;
  scopes `openid`, `email`, `profile`. Keep in Testing with your test users for
  a private beta, or publish.
- **Credentials → Create → OAuth client ID → Web application**:
  - Authorized redirect URI: `<BASE_URL>/auth/google/callback`
  - Copy the **client ID** and **client secret**.

## 3. Provision the secret + grant the runtime SA
```bash
PROJ=college-counselling-478115
gcloud secrets create stratia-google-oauth-secret --replication-policy=automatic --project=$PROJ   # (already created)
printf '%s' "<CLIENT_SECRET>" | gcloud secrets versions add stratia-google-oauth-secret --data-file=- --project=$PROJ
gcloud secrets add-iam-policy-binding stratia-google-oauth-secret \
  --member="serviceAccount:808989169388-compute@developer.gserviceaccount.com" \
  --role=roles/secretmanager.secretAccessor --project=$PROJ
```

## 4. Set config + redeploy
In `cloud_functions/stratia_connector/env.yaml`:
- `GOOGLE_CLIENT_ID: "<client id>"`
- `PUBLIC_BASE_URL:` must equal the exact Cloud Run URL from step 1 (it's the
  OAuth issuer + the audience the connector enforces). If it differs, update it
  AND the Google client's redirect URI, then redeploy.
- `CONNECTOR_ENABLED: "true"` (set `"false"` as the kill switch — see §7).
- `ALLOWED_EMAILS:` optional comma-separated private-beta allowlist.

Redeploy: `./deploy.sh stratia-connector`.

## 5. Verify the contract (before touching Claude)
```bash
BASE=https://stratia-connector-pfnwjfp26a-ue.a.run.app
curl -s $BASE/health                                            # {"status":"ok",...}
curl -s $BASE/.well-known/oauth-authorization-server | jq .     # authorize/token/registration_endpoint, scopes=["stratia"]
curl -s $BASE/.well-known/oauth-protected-resource   | jq .     # resource = $BASE
curl -s -o /dev/null -w '%{http_code}\n' -X POST $BASE/mcp \
  -H 'content-type: application/json' -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'   # -> 401
```
All four must pass. (DCR is exercised automatically by Claude; you can probe it
with `POST $BASE/register` and a JSON client metadata body.)

## 6. Add in Claude
- **claude.ai:** Settings → Connectors → Add custom connector → URL `<BASE>/mcp`.
  Leave OAuth id/secret blank (DCR handles registration). Sign in with Google.
- **Claude Code:** `claude mcp add --transport http stratia <BASE>/mcp`.

## 7. Smoke-test the tools
Sign in, then exercise: `get_college_list` → `search_universities` (e.g. low
acceptance, CA) → a write (`add_college`) → confirm the change appears in the
Stratia product for that account. Try `get_deadlines` and `get_fit_analysis`.

## 8. Kill switch / rollback
- **Disable without redeploy of code:** set `CONNECTOR_ENABLED=false` (env.yaml
  + redeploy, or `gcloud run services update stratia-connector --update-env-vars
  CONNECTOR_ENABLED=false --region=us-east1`). Everything except `/health`
  returns 404.
- **Revision rollback:** `gcloud run services update-traffic stratia-connector
  --to-revisions <PRIOR>=100 --region=us-east1`.

## 9. Pre-go-live security check (RESOLVED — #223)
The backends now verify callers (`request_auth.py` in each service): the
connector attaches a Google OIDC ID token minted by its runtime service
account, audience-bound per backend (`stratia_client._svc_auth_headers`); the
frontend attaches the signed-in user's Firebase ID token; the backends honor
`X-User-Email` only from a verified trusted service or when it matches a
verified user token. Rollout is governed by each backend's `AUTH_MODE` env
(`log` → dual-accept, `enforce` → 401/403 for unauthenticated/mismatched
callers). Design: `docs/design/DESIGN-backend-auth.md`.
