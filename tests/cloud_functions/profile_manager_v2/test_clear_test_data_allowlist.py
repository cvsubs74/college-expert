"""
Unit tests for the clear-test-data endpoint's email allow-list gate
(cloud_functions/profile_manager_v2/main.py).

The gate at line ~1753 validates that the request body email is in
QA_TEST_USER_EMAIL (a comma-separated list of allowed emails).  These
tests exercise the validation logic in isolation via a minimal Flask
request stub — no live GCP dependency required.

Issue: #128 — widen allow-list to include stratiaadmissions@gmail.com.
"""

import os
import types
import importlib
import sys
from pathlib import Path
import pytest


# ---------------------------------------------------------------------------
# Helpers — extract the allow-list logic without importing the full Cloud
# Function (which has heavyweight GCP deps).  We inline the same logic here
# and test the same invariants.  If main.py drifts from this helper the
# integration smoke test (curl example in the PR) catches it.
# ---------------------------------------------------------------------------


def _email_ok(user_email: str, qa_test_user_email_env: str) -> bool:
    """Mirror of the allow-list check in main.py clear-test-data handler."""
    allowed = [e.strip() for e in qa_test_user_email_env.split(",") if e.strip()]
    return bool(user_email) and user_email in allowed


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestClearTestDataAllowList:
    """Verify the email allow-list gate behaves correctly for both old and
    new test accounts, and rejects arbitrary addresses."""

    # --- positive cases ---

    def test_original_test_account_is_permitted(self):
        env = "duser8531@gmail.com"
        assert _email_ok("duser8531@gmail.com", env) is True

    def test_qa_loop_account_is_permitted_in_multi_value_env(self):
        """stratiaadmissions@gmail.com must be permitted when the env var
        holds both accounts (comma-separated) — this is the fix for #128."""
        env = "duser8531@gmail.com,stratiaadmissions@gmail.com"
        assert _email_ok("stratiaadmissions@gmail.com", env) is True

    def test_original_account_still_permitted_in_multi_value_env(self):
        env = "duser8531@gmail.com,stratiaadmissions@gmail.com"
        assert _email_ok("duser8531@gmail.com", env) is True

    def test_extra_whitespace_in_env_is_tolerated(self):
        env = "duser8531@gmail.com , stratiaadmissions@gmail.com"
        assert _email_ok("stratiaadmissions@gmail.com", env) is True

    # --- negative cases ---

    def test_random_email_is_rejected(self):
        env = "duser8531@gmail.com,stratiaadmissions@gmail.com"
        assert _email_ok("attacker@evil.com", env) is False

    def test_empty_email_is_rejected(self):
        env = "duser8531@gmail.com,stratiaadmissions@gmail.com"
        assert _email_ok("", env) is False

    def test_qa_loop_account_rejected_when_only_original_in_env(self):
        """Demonstrates the pre-fix regression: with a single-value env var
        the qa-loop account returns False.  After #128 the env var is widened
        so this scenario no longer occurs in production — but the test
        documents the before-state for clarity."""
        env = "duser8531@gmail.com"  # old single-value env
        assert _email_ok("stratiaadmissions@gmail.com", env) is False

    def test_single_value_env_still_works_for_that_account(self):
        """Single-value env var (no comma) continues to work — backward compat."""
        env = "stratiaadmissions@gmail.com"
        assert _email_ok("stratiaadmissions@gmail.com", env) is True

    # --- main.py parity check ---

    def test_main_py_uses_list_membership_check(self):
        """Reads the actual source of main.py and asserts the equality
        operator has been replaced with an 'in' membership check.

        This is a canary: if someone reverts the fix accidentally this
        test will catch it on the next run, even without changing env vars."""
        # parents[3] == worktree root (feat-128-allowlist/)
        # regardless of whether the test runs from the primary repo or a
        # worktree — the relative structure is always
        # <root>/tests/cloud_functions/profile_manager_v2/<file>
        source_path = (
            Path(__file__).resolve().parents[3]
            / "cloud_functions"
            / "profile_manager_v2"
            / "main.py"
        )
        source = source_path.read_text()
        # The old single-equality pattern must not be present.
        assert "user_email == allowed_email" not in source, (
            "main.py still uses equality check; expected list-membership check "
            "(user_email in allowed_emails). See issue #128."
        )
        # The new membership pattern must be present.
        assert "user_email in allowed_emails" in source, (
            "main.py does not contain 'user_email in allowed_emails'; "
            "the allow-list widening fix may be missing. See issue #128."
        )
