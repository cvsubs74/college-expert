#!/usr/bin/env bash
#
# verify-allowlist-kb.sh — audit the QA agent's colleges allowlist
# against the universities knowledge base.
#
# The allowlist (cloud_functions/qa_agent/scenarios/colleges_allowlist.json)
# tells the synthesizer which schools it may produce in archetypes.
# Every entry MUST have a corresponding KB profile, otherwise the
# synthesizer can pick a school that /compute-single-fit will 404 on
# downstream — exactly what bit run_20260505T033041Z_92fd32 with
# university_of_chicago (in allowlist, missing from KB).
#
# This script hits the KB for every allowlist entry and reports any
# orphans. Exit code 0 if all hit, 1 if any miss.
#
# Run periodically (e.g., before adding new schools, after KB ingestion
# changes) to catch drift early.
#
# Usage:
#   ./scripts/verify-allowlist-kb.sh
#
# Prerequisites: curl + jq.

set -euo pipefail

KB_URL="${KB_URL:-https://knowledge-base-manager-universities-v2-pfnwjfp26a-ue.a.run.app}"
ALLOWLIST="cloud_functions/qa_agent/scenarios/colleges_allowlist.json"

if [ ! -f "$ALLOWLIST" ]; then
    echo "ERROR: $ALLOWLIST not found. Run from repo root." >&2
    exit 2
fi

orphans=()
hits=0

echo "Auditing $ALLOWLIST against $KB_URL ..."
echo

while read -r uni; do
    [ -z "$uni" ] && continue
    if curl -sS "$KB_URL/get-university?university_id=$uni" 2>/dev/null \
        | jq -e '.success == true' >/dev/null 2>&1; then
        printf "  %-44s HIT\n" "$uni"
        hits=$((hits + 1))
    else
        printf "  %-44s MISS  ← orphan\n" "$uni"
        orphans+=("$uni")
    fi
done < <(jq -r '.colleges[]' "$ALLOWLIST")

echo
total=$((hits + ${#orphans[@]}))
echo "  total=$total  hits=$hits  orphans=${#orphans[@]}"

if [ ${#orphans[@]} -gt 0 ]; then
    echo
    echo "ACTION: either add KB profiles for these schools, OR remove them"
    echo "        from the allowlist:"
    for o in "${orphans[@]}"; do
        echo "  - $o"
    done
    echo
    echo "If keeping in the allowlist, update any static archetype that"
    echo "references them too (grep cloud_functions/qa_agent/scenarios/)."
    exit 1
fi

echo
echo "OK — every allowlist entry has a KB profile."
