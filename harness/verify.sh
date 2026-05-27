#!/usr/bin/env bash
# verify.sh — fast smoke test for College Counselor.
#
# Contract:
#   - exit 0 only if every check below passes
#   - target runtime budget: under 3 minutes in CI
#   - no GCP / Firebase / Stripe credentials required
#
# What it checks:
#   1. Shell scripts under harness/ + scripts/ + bin/ have valid bash syntax.
#   2. Every cloud_functions/<svc>/main.py (LIVE only — skip legacy variants)
#      compiles to bytecode without import-time errors that pure syntax checks
#      would catch. Per-function deps are NOT resolved here.
#   3. The frontend builds (Vite production build catches missing imports,
#      broken JSX, dead module paths).
#
# What it does NOT check (deliberately):
#   - Backend integration against deployed cloud functions — that's
#     run_all_tests.sh, which needs deployed targets + GCP auth.
#   - Frontend E2E (Playwright). Heavy and flaky in CI without a backend.
#
# These deeper checks run on the deployed targets via qa_agent archetypes;
# see issue #179 (Expand qa_agent archetype coverage).

set -euo pipefail

echo "verify.sh: starting baseline smoke..."

# ---------- 1. shell syntax ----------
echo "verify.sh: [1/3] bash -n on shell scripts..."
SCRIPTS=$(find harness scripts bin -type f -name '*.sh' 2>/dev/null || true)
fail=0
for s in $SCRIPTS; do
  if ! bash -n "$s" 2>/dev/null; then
    echo "  FAIL: $s"
    bash -n "$s" || true
    fail=1
  fi
done
[ "$fail" = 0 ] || { echo "verify.sh: shell syntax FAILED"; exit 1; }
echo "  OK ($(echo "$SCRIPTS" | wc -w | tr -d ' ') scripts)"

# ---------- 2. python syntax on live cloud functions ----------
echo "verify.sh: [2/3] python syntax on live cloud_functions..."
LIVE_FUNCS="counselor_agent profile_manager_v2 payment_manager_v2 contact_form qa_agent knowledge_base_manager_universities_v2 knowledge_base_manager knowledge_base_manager_ES"
fail=0
checked=0
for fn in $LIVE_FUNCS; do
  if [ -f "cloud_functions/$fn/main.py" ]; then
    if ! python3 -m py_compile "cloud_functions/$fn/main.py" 2>&1; then
      echo "  FAIL: cloud_functions/$fn/main.py"
      fail=1
    fi
    checked=$((checked+1))
  else
    echo "  (skip) cloud_functions/$fn/main.py — not present"
  fi
done
[ "$fail" = 0 ] || { echo "verify.sh: python syntax FAILED"; exit 1; }
echo "  OK ($checked functions)"

# ---------- 3. frontend builds ----------
echo "verify.sh: [3/3] frontend production build..."
if [ ! -d frontend/node_modules ]; then
  echo "  frontend/node_modules missing — run harness/init.sh first." >&2
  exit 1
fi
(cd frontend && npm run build --silent 2>&1 | tail -20)
echo "  OK"

echo "verify.sh: PASS"
