"""Test discovery for the CI/CD path-detector.

The script under test lives at scripts/cicd/detect_changed_targets.py and is
plain stdlib Python — no requirements.txt to satisfy. We add the script's
parent dir to sys.path so tests can `import detect_changed_targets`.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT_DIR = _REPO_ROOT / "scripts" / "cicd"

if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))
