"""Google-federated OAuth 2.1 Authorization Server for the Stratia connector.

Implements the MCP `OAuthAuthorizationServerProvider` interface and doubles as
the `TokenVerifier` for the resource server. Sign-in is delegated to Google;
the verified Google email becomes the Stratia user identity carried by every
issued access token.

Flow:
  Claude  --/authorize-->  authorize() builds a Google consent URL
  Google  --callback---->  complete_google_login() verifies the id_token,
                            mints a one-time MCP auth code, redirects to Claude
  Claude  --/token------>  exchange_authorization_code() returns access+refresh
  Claude  --tools------->  verify_token() resolves the bearer token -> email
"""
import logging
import time
from urllib.parse import urlencode

import requests
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token

from mcp.server.auth.provider import (
    AccessToken,
    AuthorizationCode,
    AuthorizationParams,
    OAuthAuthorizationServerProvider,
    RefreshToken,
    TokenError,
    construct_redirect_uri,
)
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken

import pkce
from settings import settings
from store import OAuthStore

logger = logging.getLogger("stratia_connector.auth")


class GoogleOAuthProvider(OAuthAuthorizationServerProvider):
    def __init__(self, store: OAuthStore):
        self.store = store

    # -- Dynamic Client Registration ---------------------------------------
    async def get_client(self, client_id: str):
        rec = self.store.get_client(client_id)
        return OAuthClientInformationFull.model_validate(rec) if rec else None

    async def register_client(self, client_info: OAuthClientInformationFull):
        self.store.put_client(client_info.client_id, client_info.model_dump(mode="json"),
                             ttl=settings.CLIENT_TTL)

    # -- Authorization: redirect the user to Google ------------------------
    async def authorize(self, client: OAuthClientInformationFull, params: AuthorizationParams) -> str:
        state = pkce.new_token("st_")
        self.store.put_state(state, {
            "client_id": client.client_id,
            "redirect_uri": str(params.redirect_uri),
            "redirect_uri_provided_explicitly": params.redirect_uri_provided_explicitly,
            "code_challenge": params.code_challenge,
            "scopes": params.scopes or [settings.MCP_SCOPE],
            "client_state": params.state,
            "resource": getattr(params, "resource", None),
        }, ttl=settings.STATE_TTL)

        q = urlencode({
            "client_id": settings.GOOGLE_CLIENT_ID,
            "redirect_uri": settings.google_redirect_uri(),
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "access_type": "online",
            "prompt": "select_account",
        })
        return f"{settings.GOOGLE_AUTH_URL}?{q}"

    # -- Google callback: verify identity, mint our auth code --------------
    def complete_google_login(self, google_code: str, state: str) -> str:
        """Called by the /auth/google/callback route. Returns the redirect URL
        back to the MCP client (Claude) carrying our authorization code."""
        ctx = self.store.pop_state(state)
        if not ctx:
            raise ValueError("invalid or expired state")

        email = self._verify_google_email(google_code)
        if not settings.email_allowed(email):
            raise PermissionError(f"{email} is not permitted to use this connector")

        code = pkce.new_token("mcp_")
        self.store.put_code(code, {
            "client_id": ctx["client_id"],
            "redirect_uri": ctx["redirect_uri"],
            "redirect_uri_provided_explicitly": ctx["redirect_uri_provided_explicitly"],
            "code_challenge": ctx["code_challenge"],
            "scopes": ctx["scopes"],
            "resource": ctx.get("resource"),
            "email": email,
        }, ttl=settings.CODE_TTL)

        redirect_params = {"code": code}
        if ctx.get("client_state"):
            redirect_params["state"] = ctx["client_state"]
        return construct_redirect_uri(ctx["redirect_uri"], **redirect_params)

    def _verify_google_email(self, google_code: str) -> str:
        resp = requests.post(settings.GOOGLE_TOKEN_URL, data={
            "code": google_code,
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uri": settings.google_redirect_uri(),
            "grant_type": "authorization_code",
        }, timeout=30)
        resp.raise_for_status()
        tok = resp.json()
        claims = google_id_token.verify_oauth2_token(
            tok["id_token"], google_requests.Request(), settings.GOOGLE_CLIENT_ID
        )
        if not claims.get("email") or not claims.get("email_verified"):
            raise ValueError("Google account has no verified email")
        return claims["email"].lower()

    # -- Authorization code -> tokens --------------------------------------
    async def load_authorization_code(self, client: OAuthClientInformationFull, authorization_code: str):
        rec = self.store.get_code(authorization_code)
        if not rec or rec["client_id"] != client.client_id:
            return None
        return AuthorizationCode(
            code=authorization_code,
            scopes=rec["scopes"],
            expires_at=rec["_exp"],
            client_id=rec["client_id"],
            code_challenge=rec["code_challenge"],
            redirect_uri=rec["redirect_uri"],
            redirect_uri_provided_explicitly=rec["redirect_uri_provided_explicitly"],
        )

    async def exchange_authorization_code(self, client, authorization_code: AuthorizationCode) -> OAuthToken:
        rec = self.store.get_code(authorization_code.code)
        if not rec:
            raise TokenError("invalid_grant", "authorization code expired or already used")
        self.store.delete_code(authorization_code.code)  # one-time use
        # RFC 8707 audience binding: refuse to mint a token whose requested
        # resource targets a different server (confused-deputy protection).
        if not settings.resource_ok(rec.get("resource")):
            raise TokenError("invalid_request", "resource/audience mismatch")
        return self._issue_tokens(rec["client_id"], rec["scopes"], rec["email"],
                                 rec.get("resource"))

    # -- Refresh -----------------------------------------------------------
    async def load_refresh_token(self, client, refresh_token: str):
        rec = self.store.get_refresh(refresh_token)
        if not rec or rec["client_id"] != client.client_id:
            return None
        return RefreshToken(token=refresh_token, client_id=rec["client_id"],
                           scopes=rec["scopes"], expires_at=int(rec["_exp"]),
                           subject=rec.get("email"))

    async def exchange_refresh_token(self, client, refresh_token: RefreshToken, scopes) -> OAuthToken:
        rec = self.store.get_refresh(refresh_token.token)
        if not rec:
            raise TokenError("invalid_grant", "invalid or expired refresh token")
        self.store.delete_refresh(refresh_token.token)  # rotate
        return self._issue_tokens(rec["client_id"], scopes or rec["scopes"], rec["email"],
                                 rec.get("resource"))

    # -- Token verification (resource server) ------------------------------
    async def load_access_token(self, token: str):
        rec = self.store.get_access(token)
        if not rec:
            return None
        # Resource-server audience check: the token must be bound to THIS
        # connector (it always is, since we only mint our own resource).
        if not settings.resource_ok(rec.get("resource")):
            return None
        return AccessToken(token=token, client_id=rec["client_id"],
                          scopes=rec["scopes"], expires_at=int(rec["_exp"]),
                          resource=rec.get("resource"), subject=rec.get("email"))

    async def verify_token(self, token: str):
        return await self.load_access_token(token)

    async def revoke_token(self, token, token_type_hint=None):
        # `token` may be an AccessToken/RefreshToken object or a raw string.
        raw = getattr(token, "token", token)
        self.store.delete_access(raw)
        self.store.delete_refresh(raw)

    # -- helpers -----------------------------------------------------------
    def _issue_tokens(self, client_id, scopes, email, resource=None) -> OAuthToken:
        # Bind the token to this connector's resource (RFC 8707). When the
        # client omitted `resource`, bind to our own so the token is never
        # audience-unconstrained.
        aud = resource or settings.mcp_resource()
        access = pkce.new_token("at_")
        refresh = pkce.new_token("rt_")
        ctx = {"client_id": client_id, "scopes": scopes, "email": email, "resource": aud}
        self.store.put_access(access, ctx, ttl=settings.ACCESS_TOKEN_TTL)
        self.store.put_refresh(refresh, ctx, ttl=settings.REFRESH_TOKEN_TTL)
        return OAuthToken(access_token=access, token_type="Bearer",
                         expires_in=settings.ACCESS_TOKEN_TTL, scope=" ".join(scopes),
                         refresh_token=refresh)

    def email_for_token(self, token: str):
        """Resolve the Stratia email behind a bearer token (used by tools)."""
        rec = self.store.get_access(token)
        return rec["email"] if rec else None
