#!/usr/bin/env bash
# PreToolUse guard (matcher: Edit|Write).
#
# Blocks edits to secrets, credential material, operational config, and large
# generated artifacts that should never be hand-authored by an agent.
#
#   exit 2 = block the tool call and feed the message back to Claude.
#   exit 0 = allow.
#
# The user can always make the change manually or explicitly approve it.
set -u

INPUT=$(cat)

FILE=$(printf '%s' "$INPUT" | python3 -c '
import json, sys
try: d = json.load(sys.stdin)
except Exception: sys.exit(0)
print((d.get("tool_input") or {}).get("file_path", "") or "")
')

[ -z "$FILE" ] && exit 0

ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
BASE=$(basename "$FILE")
REL=${FILE#"$ROOT"/}

block() {
  {
    echo "BLOCKED edit to: $REL"
    echo "$1"
    echo "If this change is genuinely intended, ask the user to edit the file manually or to explicitly approve it."
  } >&2
  exit 2
}

case "$BASE" in
  .env|.env.*|*.env)
    block "Environment files hold secrets and are environment-specific — never agent-edited." ;;
  *.pem|*.key|*.p12|*.keystore)
    block "Private key / credential material must not be touched by an agent." ;;
  *secret*.json|*secret*.txt|*secret*.yaml|*secret*.yml|secrets.*|*.secrets.*)
    block "This looks like a secrets file." ;;
  stripe_*.json)
    block "Stripe product/price config is operational data, not source to hand-edit." ;;
  firestore.rules)
    block "Security rules govern data access — they need deliberate review, not an incidental edit." ;;
  setup_secrets.sh|setup_firebase_env.sh)
    block "Secret-provisioning scripts should be changed deliberately by a human." ;;
esac

# Large generated artifacts (data dumps, vendored text) — produced by ingest /
# scripts, not authored. Only guards EXISTING files (new files are fine).
if [ -f "$FILE" ]; then
  SIZE=$(wc -c < "$FILE" 2>/dev/null | tr -d ' ')
  if [ "${SIZE:-0}" -gt 262144 ]; then
    KB=$(( SIZE / 1024 ))
    block "This file is ${KB} KB — a generated/data artifact, not hand-authored source."
  fi
fi

exit 0
