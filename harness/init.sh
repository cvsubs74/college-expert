#!/usr/bin/env bash
# init.sh — bring up the dev environment for College Counselor.
#
# Contract:
#   - exit 0 on success, non-zero on failure
#   - safe to run twice in a row (idempotent)
#   - prints what it's doing
#
# What it does:
#   1. Verifies required tools (python3, node, npm).
#   2. Installs frontend npm deps (if frontend/node_modules is missing).
#   3. Ensures pytest is on PATH for backend tests.
#
# What it does NOT do (deliberately):
#   - Start cloud functions locally — that's ./start_local.sh, not the
#     baseline. CI doesn't need a live backend.
#   - Touch GCP / Firebase auth. CI runs without those credentials.
#   - Install per-cloud-function venvs. Each function manages its own
#     deps under cloud_functions/<name>/requirements.txt; verify.sh
#     does Python-syntax checks that don't need them resolved.

set -euo pipefail

echo "init.sh: bringing up dev environment..."

# ---------- tool checks ----------
need() {
  local bin="$1" hint="$2"
  command -v "$bin" >/dev/null 2>&1 || { echo "init.sh: missing '$bin'. $hint" >&2; exit 1; }
}
need python3 "Install Python 3.11+ (brew install python@3.11)."
need node    "Install Node 20+ (brew install node)."
need npm     "npm ships with Node; reinstall Node."

# ---------- frontend deps ----------
if [ ! -d frontend/node_modules ]; then
  echo "init.sh: installing frontend npm deps (frontend/node_modules missing)..."
  (cd frontend && npm ci --no-audit --no-fund --prefer-offline)
else
  echo "init.sh: frontend/node_modules present — skipping npm ci."
fi

# ---------- pytest availability ----------
if ! command -v pytest >/dev/null 2>&1; then
  if python3 -m pytest --version >/dev/null 2>&1; then
    echo "init.sh: pytest available via 'python3 -m pytest'."
  else
    echo "init.sh: pytest not found; installing into the active Python env..."
    python3 -m pip install --quiet pytest
  fi
else
  echo "init.sh: pytest on PATH."
fi

echo "init.sh: OK"
