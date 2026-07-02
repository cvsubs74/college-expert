"""Put the stratia_connector source dir on sys.path for unit tests."""
import sys
from pathlib import Path

SOURCE_DIR = Path(__file__).resolve().parents[3] / "cloud_functions" / "stratia_connector"
if str(SOURCE_DIR) not in sys.path:
    sys.path.insert(0, str(SOURCE_DIR))

import pytest


@pytest.fixture(autouse=True)
def _hermetic_service_tokens(monkeypatch):
    """#223: _get/_post now attach a service OIDC token per call. Outside GCE
    that attempt hits credential discovery (network) — stub it suite-wide so
    tests stay fast and hermetic. Tests that exercise the real function use
    the `real_svc_auth_headers` fixture."""
    try:
        import stratia_client as sc
        monkeypatch.setattr(sc, "_svc_auth_headers", lambda url: {})
    except Exception:  # noqa: BLE001 — suites that never import the client
        pass


@pytest.fixture
def real_svc_auth_headers():
    import stratia_client as sc
    # The autouse stub replaced the module attr; recover the original from
    # the function object it still references via __wrapped__-free lookup.
    return _REAL_SVC_AUTH_HEADERS


try:
    import stratia_client as _sc_for_real
    _REAL_SVC_AUTH_HEADERS = _sc_for_real._svc_auth_headers
except Exception:  # noqa: BLE001
    _REAL_SVC_AUTH_HEADERS = None
