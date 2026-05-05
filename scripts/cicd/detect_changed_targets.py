#!/usr/bin/env python3
"""
Map a git diff to deploy.sh targets for the auto-deploy CI stage.

Usage (from repo root):

    python3 scripts/cicd/detect_changed_targets.py [--rev-range REV1..REV2]

Default rev range is `HEAD^..HEAD` — appropriate for the squash-merge style
this repo uses where every PR becomes one commit on main. Cloud Build passes
`${COMMIT_SHA}^..${COMMIT_SHA}` explicitly to be deterministic.

Output: newline-separated deploy targets, deduplicated, sorted alphabetically,
on stdout. Empty output (zero bytes) means "no live component changed; skip
deploy."

Example:

    $ git diff --name-only HEAD^..HEAD
    cloud_functions/qa_agent/main.py
    docs/prd/foo.md
    $ python3 scripts/cicd/detect_changed_targets.py
    qa-agent

Spec: docs/prd/auto-deploy-on-main.md + docs/design/auto-deploy-on-main.md.

The PATH_TARGET_MAP below is the SINGLE source of truth for "which path
prefix maps to which `./deploy.sh <target>` arm." When you add a new live
cloud function or agent, update this list AND
`docs/design/auto-deploy-on-main.md` AND add a row to
`tests/cicd/test_detect_changed_targets.py::test_each_live_function_maps`.
"""

from __future__ import annotations

import argparse
import subprocess
import sys


# Path-prefix → deploy.sh target. Order is irrelevant because the prefixes
# don't overlap (each cloud function lives in a unique directory). We match
# greedily on the first prefix a file path startswith().
#
# Live components only — see CLAUDE memory `project_live_components_scope.md`.
# Excluded paths (legacy variants, tools, docs, tests, infra) produce no
# target, which means the deploy step exits 0 without touching anything.
PATH_TARGET_MAP: list[tuple[str, str]] = [
    # cloud functions ------------------------------------------------------
    ("cloud_functions/profile_manager_v2/",                       "profile-v2"),
    ("cloud_functions/payment_manager_v2/",                       "payment-v2"),
    ("cloud_functions/counselor_agent/",                          "counselor-agent"),
    ("cloud_functions/contact_form/",                             "contact"),
    ("cloud_functions/knowledge_base_manager_universities_v2/",   "knowledge-universities-v2"),
    # NOTE: order matters here — the v2 path above is checked first so the
    # generic "knowledge_base_manager_universities/" prefix below would
    # otherwise swallow it. We avoid that by listing v2 first AND making
    # the v1 row absent (it's deliberately excluded as legacy ES-backed code).
    ("cloud_functions/knowledge_base_manager_ES/",                "knowledge-es"),
    ("cloud_functions/knowledge_base_manager/",                   "knowledge-rag"),
    ("cloud_functions/qa_agent/",                                 "qa-agent"),
    # agents ---------------------------------------------------------------
    ("agents/college_expert_hybrid/",                             "agent-hybrid"),
    ("agents/college_expert_rag/",                                "agent-rag"),
    ("agents/college_expert_es/",                                 "agent-es"),
    # frontend -------------------------------------------------------------
    ("frontend/",                                                 "frontend"),
]


# Path prefixes that look like they could match the live mappings but are
# explicitly out of scope. We list them here so a future grep finds the
# rationale next to the data, even though the mapper handles them by virtue
# of "no row in PATH_TARGET_MAP."
_EXCLUDED_FOR_REFERENCE: list[str] = [
    "cloud_functions/profile_manager/",                  # replaced by _v2
    "cloud_functions/profile_manager_es/",               # replaced by _v2
    "cloud_functions/profile_manager_vertexai/",         # vertexai removed
    "cloud_functions/payment_manager/",                  # replaced by _v2
    "cloud_functions/knowledge_base_manager_universities/",  # ES cluster offline
    "cloud_functions/knowledge_base_manager_vertexai/",  # vertexai removed
    "cloud_functions/scheduled_notifications/",          # cron-only, no deploy.sh target
    "agents/college_expert_adk/",                        # vertexai removed
    "agents/source_curator/",                            # standalone tool
    "agents/sourcery/",                                  # standalone tool
    "agents/uniminer/",                                  # standalone tool
    "agents/university_profile_collector/",              # standalone tool
]


def targets_for_files(files: list[str]) -> list[str]:
    """Pure mapping: changed-file paths → sorted deduplicated deploy targets.

    Files that don't match any prefix are silently ignored (docs, tests,
    cloudbuild.yaml, deploy.sh, top-level misc files).
    """
    seen: set[str] = set()
    for path in files or []:
        if not path:
            continue
        for prefix, target in PATH_TARGET_MAP:
            if path.startswith(prefix):
                seen.add(target)
                break
    return sorted(seen)


def _git_diff_files(rev_range: str) -> list[str]:
    """Run `git diff --name-only <rev_range>` and return the list of paths.
    Errors propagate — a bad rev range means the CI step fails loudly,
    which is what we want."""
    out = subprocess.check_output(
        ["git", "diff", "--name-only", rev_range],
        text=True,
    )
    return [line.strip() for line in out.splitlines() if line.strip()]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--rev-range",
        default="HEAD^..HEAD",
        help="Git rev range to diff (default: HEAD^..HEAD).",
    )
    args = parser.parse_args(argv)

    files = _git_diff_files(args.rev_range)
    for target in targets_for_files(files):
        print(target)
    return 0


if __name__ == "__main__":
    sys.exit(main())
