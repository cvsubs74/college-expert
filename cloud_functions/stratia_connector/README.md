# Stratia Admissions — Claude connector (remote MCP server)

A [Model Context Protocol](https://modelcontextprotocol.io) server that lets a
student use **Claude** (claude.ai / Claude Code) to work with their Stratia
Admissions data: college list, college-fit analyses, application & scholarship
deadlines, profile, plus university search and a few safe write actions.

- **Transport:** Streamable HTTP (FastMCP / `mcp` SDK), deployed to **Cloud Run**.
- **Auth:** OAuth 2.1 + Dynamic Client Registration, **federated to Google**.
  The verified Google email is the Stratia user identity. The connector is the
  trusted layer that maps a verified email → the existing backend `user_email`
  (the backends are unchanged for v1).
- **MCP endpoint:** `<PUBLIC_BASE_URL>/mcp` — this is the URL you add in Claude.

## Tools

Read: `search_universities`, `get_university`, `get_college_list`,
`get_fit_analysis`, `get_deadlines`, `get_profile`.
Write (safe): `add_college`, `remove_college`, `recompute_fit` (costs 1 credit),
`update_profile_field`.

All per-student tools operate on the authenticated user only.

## Files

| File | Purpose |
|---|---|
| `server.py` | FastMCP app, tool definitions, Google callback + health routes, ASGI `app` |
| `auth_provider.py` | Google-federated OAuth authorization server + token verifier |
| `store.py` | OAuth state store (Firestore in prod, in-memory for dev/tests) |
| `stratia_client.py` | `requests` wrapper over counselor_agent / profile_manager_v2 / KB |
| `pkce.py` | PKCE (S256) + opaque token helpers |
| `settings.py` | env-driven config |
| `Procfile` | `web: uvicorn server:app ...` (Cloud Run buildpack entrypoint) |
| `env.yaml` | non-secret runtime config |

Tests: `tests/cloud_functions/stratia_connector/` (pkce/store/client run in CI;
the OAuth-provider + server-boot tests need `mcp`+`google-auth` and skip in the
lightweight CI image — run them locally).

## One-time setup (owner)

The code is complete; these are the credential/console steps that can't be
scripted. Run as `cvsubs@gmail.com` on project `college-counselling-478115`.

1. **OAuth consent screen** (APIs & Services → OAuth consent screen): External,
   add the app name + your support email. Add scopes `openid`, `email`,
   `profile`. (Keep in "Testing" with your account(s) as test users for a
   private beta, or publish.)

2. **OAuth web client** (APIs & Services → Credentials → Create credentials →
   OAuth client ID → Web application):
   - Authorized redirect URI: `<PUBLIC_BASE_URL>/auth/google/callback`
   - Copy the **client ID** and **client secret**.

3. **Store the secret + grant access:**
   ```bash
   gcloud secrets create stratia-google-oauth-secret --replication-policy=automatic \
     --project=college-counselling-478115
   printf '%s' "<CLIENT_SECRET>" | gcloud secrets versions add stratia-google-oauth-secret \
     --data-file=- --project=college-counselling-478115
   # grant the Cloud Run runtime SA read access (default compute SA shown):
   gcloud secrets add-iam-policy-binding stratia-google-oauth-secret \
     --member="serviceAccount:<PROJECT_NUMBER>-compute@developer.gserviceaccount.com" \
     --role=roles/secretmanager.secretAccessor --project=college-counselling-478115
   ```

4. **Set `GOOGLE_CLIENT_ID` and `PUBLIC_BASE_URL`** in `env.yaml`, then deploy:
   ```bash
   ./deploy.sh stratia-connector
   ```
   `PUBLIC_BASE_URL` must equal the Cloud Run URL the deploy prints. It's
   chicken-and-egg: the first deploy assigns the URL — set it (and the Google
   redirect URI) to that value and redeploy. After merge to `main`, CI
   auto-redeploys on changes under `cloud_functions/stratia_connector/`.

## Add it in Claude

claude.ai → **Settings → Connectors → Add custom connector** → URL
`<PUBLIC_BASE_URL>/mcp`. Claude registers via DCR, you sign in with Google, and
the tools appear. (Claude Code: `claude mcp add --transport http stratia
<PUBLIC_BASE_URL>/mcp`.)

## Local dev

```bash
cd cloud_functions/stratia_connector
pip install -r requirements.txt
OAUTH_USE_FIRESTORE=false PUBLIC_BASE_URL=http://localhost:8080 \
  GOOGLE_CLIENT_ID=... GOOGLE_CLIENT_SECRET=... \
  uvicorn server:app --port 8080
# inspect: npx @modelcontextprotocol/inspector  (point it at http://localhost:8080/mcp)
```
