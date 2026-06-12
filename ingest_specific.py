#!/usr/bin/env python3
"""DEPRECATED — use scripts/ingest_universities.py.

This script predates KB year-versioning (ADR 0002) and pointed at the
retired v1 Elasticsearch-backed function. It now forwards to the canonical
CLI so existing muscle memory keeps working:

    python ingest_specific.py file1.json file2.json
        ≡ python scripts/ingest_universities.py --file file1.json (per file)

For directories, --year, --dry-run, see scripts/ingest_universities.py.
"""
import subprocess
import sys
from pathlib import Path

if __name__ == "__main__":
    files = sys.argv[1:]
    if not files:
        print("Usage: python ingest_specific.py file1.json file2.json ...")
        print("(deprecated — prefer scripts/ingest_universities.py)")
        sys.exit(1)

    print("ingest_specific.py is deprecated; forwarding to scripts/ingest_universities.py\n")
    script = Path(__file__).parent / 'scripts' / 'ingest_universities.py'
    failed = 0
    for f in files:
        rc = subprocess.call([sys.executable, str(script), '--file', f])
        failed += 1 if rc else 0
    sys.exit(1 if failed else 0)
