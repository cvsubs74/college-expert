"""settings.resource_ok — RFC 8707 audience/origin check. Stdlib only; CI-safe.
PUBLIC_BASE_URL defaults to http://localhost:8080 in the test env."""
from settings import settings


def test_absent_resource_passes():
    assert settings.resource_ok(None) is True
    assert settings.resource_ok("") is True


def test_same_origin_passes_regardless_of_path():
    assert settings.resource_ok("http://localhost:8080") is True
    assert settings.resource_ok("http://localhost:8080/") is True
    assert settings.resource_ok("http://localhost:8080/mcp") is True


def test_different_origin_rejected():
    assert settings.resource_ok("https://evil.example.com/mcp") is False
    assert settings.resource_ok("http://localhost:9999/mcp") is False  # different port
    assert settings.resource_ok("https://localhost:8080/mcp") is False  # different scheme


def test_mcp_resource_is_the_mcp_endpoint_not_the_origin():
    # The protected-resource `resource` published in OAuth metadata MUST be the
    # /mcp endpoint (what clients connect to), not the bare origin — else strict
    # clients (Gemini CLI) reject the mismatch. server.py wires
    # AuthSettings.resource_server_url to this value.
    assert settings.mcp_resource() == "http://localhost:8080/mcp"
    assert settings.mcp_resource().endswith("/mcp")
    # And the audience check still accepts that exact resource.
    assert settings.resource_ok(settings.mcp_resource()) is True
