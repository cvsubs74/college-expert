"""Runtime configuration for the Stratia Admissions MCP connector.

All values come from environment variables (env.yaml for non-secrets;
GOOGLE_CLIENT_SECRET injected from Secret Manager at deploy time).
"""
import os


def _clean(url: str) -> str:
    return (url or "").rstrip("/")


class Settings:
    # Public HTTPS base URL of THIS connector (the OAuth issuer + resource
    # server identifier). Must match the deployed Cloud Run URL exactly.
    PUBLIC_BASE_URL = _clean(os.environ.get("PUBLIC_BASE_URL", "http://localhost:8080"))

    # Upstream Google OAuth (identity). The connector federates sign-in to
    # Google and treats the verified email as the Stratia user.
    GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
    GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"

    # Stratia backend services the tools call (see ARCHITECTURE.md).
    COUNSELOR_AGENT_URL = _clean(os.environ.get(
        "COUNSELOR_AGENT_URL",
        "https://us-east1-college-counselling-478115.cloudfunctions.net/counselor-agent",
    ))
    PROFILE_MANAGER_V2_URL = _clean(os.environ.get(
        "PROFILE_MANAGER_V2_URL",
        "https://profile-manager-v2-pfnwjfp26a-ue.a.run.app",
    ))
    KNOWLEDGE_BASE_UNIVERSITIES_URL = _clean(os.environ.get(
        "KNOWLEDGE_BASE_UNIVERSITIES_URL",
        "https://knowledge-base-manager-universities-v2-pfnwjfp26a-ue.a.run.app",
    ))

    # Single OAuth scope the connector grants/requires.
    MCP_SCOPE = os.environ.get("MCP_SCOPE", "stratia")

    # Optional comma-separated allowlist of emails permitted to connect. Empty
    # = any Google account with a verified email. (Set this for a private beta.)
    ALLOWED_EMAILS = frozenset(
        e.strip().lower() for e in os.environ.get("ALLOWED_EMAILS", "").split(",") if e.strip()
    )

    # Lifetimes (seconds).
    CODE_TTL = int(os.environ.get("OAUTH_CODE_TTL", "300"))           # 5 min
    ACCESS_TOKEN_TTL = int(os.environ.get("OAUTH_ACCESS_TOKEN_TTL", "3600"))   # 1 h
    STATE_TTL = int(os.environ.get("OAUTH_STATE_TTL", "600"))         # 10 min

    # Persist OAuth state in Firestore (required on multi-instance Cloud Run).
    # Falls back to in-memory when false (local/dev/tests).
    USE_FIRESTORE = os.environ.get("OAUTH_USE_FIRESTORE", "true").lower() == "true"
    FIRESTORE_PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT", "college-counselling-478115")

    GOOGLE_REDIRECT_PATH = "/auth/google/callback"

    @classmethod
    def google_redirect_uri(cls) -> str:
        return f"{cls.PUBLIC_BASE_URL}{cls.GOOGLE_REDIRECT_PATH}"

    @classmethod
    def email_allowed(cls, email: str) -> bool:
        return (not cls.ALLOWED_EMAILS) or (email or "").lower() in cls.ALLOWED_EMAILS


settings = Settings()
