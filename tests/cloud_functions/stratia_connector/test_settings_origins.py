"""allowed_origins must include ChatGPT (not just Claude) so DNS-rebinding /
Origin checks don't block ChatGPT's web client; env override still wins."""
import importlib


def _settings(monkeypatch, **env):
    for k in ("ALLOWED_ORIGINS", "PUBLIC_BASE_URL"):
        monkeypatch.delenv(k, raising=False)
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    import settings as settings_mod
    importlib.reload(settings_mod)
    return settings_mod.settings


def test_default_origins_cover_claude_and_chatgpt(monkeypatch):
    s = _settings(monkeypatch, PUBLIC_BASE_URL="https://stratia-connector-pfnwjfp26a-ue.a.run.app")
    origins = s.allowed_origins()
    assert "https://claude.ai" in origins
    assert "https://chatgpt.com" in origins
    assert "https://chat.openai.com" in origins
    assert "https://stratia-connector-pfnwjfp26a-ue.a.run.app" in origins


def test_env_override_replaces_defaults(monkeypatch):
    s = _settings(monkeypatch, ALLOWED_ORIGINS="https://example.com, https://foo.test")
    assert s.allowed_origins() == ["https://example.com", "https://foo.test"]
