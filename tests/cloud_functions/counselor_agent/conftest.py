"""
Shared test setup for counselor_agent unit tests.

Two responsibilities:

1. Put the function source dir on sys.path so tests can `import planner`
   etc. without packaging the cloud function as a real Python package.
2. Stub heavy Google deps (genai, cloud.firestore) before any test imports
   a module that references them, so tests run fast and don't need those
   packages installed in CI.
"""

import os
import sys
import types
from pathlib import Path

# Source dir → sys.path. ROOT/cloud_functions/counselor_agent/
SOURCE_DIR = Path(__file__).resolve().parents[3] / 'cloud_functions' / 'counselor_agent'
if str(SOURCE_DIR) not in sys.path:
    sys.path.insert(0, str(SOURCE_DIR))


def _ensure_module(name):
    """Create or return a stub module under `name` in sys.modules."""
    if name in sys.modules:
        return sys.modules[name]
    mod = types.ModuleType(name)
    sys.modules[name] = mod
    # Make it look like a package so submodule imports work.
    mod.__path__ = []
    return mod


# Stub google.generativeai — counselor_chat.py imports it at module load.
# We don't exercise chat in unit tests, but planner.py and work_feed.py
# don't trigger it; this stub just keeps any incidental imports inert.
_genai = _ensure_module('google.generativeai')
_genai.configure = lambda *a, **k: None
class _StubGenerativeModel:
    def __init__(self, *a, **k):
        pass
    def generate_content(self, *a, **k):
        return types.SimpleNamespace(text='')
_genai.GenerativeModel = _StubGenerativeModel

# google.genai (the newer SDK alias) sometimes also gets imported.
_ensure_module('google.genai')


# A stable "today" the tests can override per-test via the fixture below.
# Anchored to a junior-spring date for the example user, so default mappings
# behave like a real student session.
import pytest
from datetime import datetime, date


@pytest.fixture
def fixed_today_jan():
    """Mid-January date — junior spring window for a student graduating 2027."""
    return datetime(2026, 1, 15)


@pytest.fixture
def fixed_today_sep():
    """Mid-September date — fall semester."""
    return datetime(2026, 9, 15)


@pytest.fixture
def fixed_today_jul():
    """Mid-July date — summer between junior and senior year."""
    return datetime(2026, 7, 15)


@pytest.fixture
def make_college_context():
    """
    Factory for a college_context dict matching planner.get_college_context's
    output shape. Pass colleges as a list of dicts with at least id/name; the
    factory fills in is_uc / deadline / deadline_type defaults.
    """
    def _make(colleges=None, uc_schools=None, has_ed=False, has_ea=False):
        cleaned = []
        for c in (colleges or []):
            cleaned.append({
                'id': c['id'],
                'name': c.get('name', c['id']),
                'deadline': c.get('deadline', '2027-01-05'),
                'deadline_type': c.get('deadline_type', 'Regular Decision'),
                'is_uc': c.get('is_uc', False),
            })
        return {
            'colleges': cleaned,
            'uc_schools': sorted(uc_schools or []),
            'has_early_decision': has_ed,
            'has_early_action': has_ea,
        }
    return _make
