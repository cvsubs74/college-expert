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
