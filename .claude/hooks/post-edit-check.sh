#!/usr/bin/env bash
# PostToolUse check (matcher: Edit|Write).
#
# Fast feedback after an edit, mirroring verify.sh's contract without paying
# full-CI cost:
#   *.py                 -> python3 -m py_compile  (exit 2 on failure so Claude sees it)
#   frontend *.{js,jsx,ts,tsx} -> prettier --check IF prettier is installed (advisory)
#
# Never blocks on a missing optional tool (ruff/prettier are not required deps).
set -u

INPUT=$(cat)

FILE=$(printf '%s' "$INPUT" | python3 -c '
import json, sys
try: d = json.load(sys.stdin)
except Exception: sys.exit(0)
print((d.get("tool_input") or {}).get("file_path", "") or "")
')

[ -z "$FILE" ] && exit 0
[ -f "$FILE" ] || exit 0

case "$FILE" in
  *.py)
    if ! err=$(python3 -m py_compile "$FILE" 2>&1); then
      {
        echo "py_compile failed for $FILE:"
        echo "$err"
        echo "Fix the syntax error before continuing."
      } >&2
      exit 2
    fi
    # Optional: ruff lint if the team adopts it later.
    if command -v ruff >/dev/null 2>&1; then
      ruff check "$FILE" 2>/dev/null || echo "ruff: lint findings in $FILE (advisory)." >&2
    fi
    ;;
  */frontend/*.js|*/frontend/*.jsx|*/frontend/*.ts|*/frontend/*.tsx)
    if command -v prettier >/dev/null 2>&1; then
      prettier --check "$FILE" >/dev/null 2>&1 || \
        echo "prettier: $FILE is not formatted (advisory; run 'prettier --write')." >&2
    fi
    ;;
esac

exit 0
