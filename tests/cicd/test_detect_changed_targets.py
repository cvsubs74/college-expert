"""
Unit tests for the auto-deploy path detector.

Spec: docs/prd/auto-deploy-on-main.md + docs/design/auto-deploy-on-main.md.

The detector maps changed files in a git diff to deploy.sh targets, deduplicates,
sorts, and prints them. The tests exercise the pure mapping function so we don't
have to spin up a real git repo for every case. A separate end-to-end test
shells out to a temp git repo to confirm the CLI wires up the diff correctly.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest


# ---- Pure mapping ---------------------------------------------------------


class TestTargetsForFiles:
    """Tests for `detect_changed_targets.targets_for_files()` — the pure
    function that the CLI wraps. Each test passes a list of file paths and
    asserts the deploy targets the function emits."""

    def test_qa_agent_backend_change_maps_to_qa_agent(self):
        import detect_changed_targets as d
        assert d.targets_for_files(["cloud_functions/qa_agent/main.py"]) == [
            "qa-agent",
        ]

    def test_qa_agent_scenario_json_maps_to_qa_agent(self):
        """Scenario JSON files are baked into the deploy package — they must
        trigger a redeploy when edited."""
        import detect_changed_targets as d
        assert d.targets_for_files([
            "cloud_functions/qa_agent/scenarios/all_uc_only.json",
        ]) == ["qa-agent"]

    def test_profile_v2_and_frontend_both_picked_up(self):
        import detect_changed_targets as d
        out = d.targets_for_files([
            "cloud_functions/profile_manager_v2/main.py",
            "frontend/src/App.tsx",
        ])
        assert out == ["frontend", "profile-v2"]

    def test_docs_only_change_emits_no_targets(self):
        import detect_changed_targets as d
        assert d.targets_for_files([
            "docs/prd/foo.md",
            "docs/design/foo.md",
            "README.md",
        ]) == []

    def test_tests_only_change_emits_no_targets(self):
        """A pure test-suite change doesn't touch any deployable. The CI
        gate already ran the tests; no deploy needed."""
        import detect_changed_targets as d
        assert d.targets_for_files([
            "tests/cloud_functions/qa_agent/test_runner.py",
            "tests/cicd/test_detect_changed_targets.py",
        ]) == []

    def test_cloudbuild_yaml_change_emits_no_targets(self):
        """Editing cloudbuild config changes the trigger logic itself — the
        next runtime-touching PR redeploys with the latest config. We
        deliberately don't auto-deploy on infrastructure-only changes."""
        import detect_changed_targets as d
        assert d.targets_for_files([
            "cloudbuild.yaml",
            "cloudbuild-main.yaml",
        ]) == []

    def test_deploy_script_edit_emits_no_targets(self):
        """Same reasoning as cloudbuild: deploy.sh is infrastructure code,
        not a runtime."""
        import detect_changed_targets as d
        assert d.targets_for_files(["deploy.sh", "deploy_frontend.sh"]) == []

    def test_legacy_dead_code_emits_no_targets(self):
        """profile_manager (no _v2) is replaced by profile_manager_v2 and
        is dead. Editing it must not trigger a deploy."""
        import detect_changed_targets as d
        assert d.targets_for_files([
            "cloud_functions/profile_manager/main.py",
            "cloud_functions/payment_manager/main.py",
            "cloud_functions/knowledge_base_manager_vertexai/main.py",
        ]) == []

    def test_legacy_universities_v1_emits_no_targets(self):
        """The non-_v2 universities knowledge base is ES-backed; the cluster
        is offline. Path detector excludes it deliberately."""
        import detect_changed_targets as d
        assert d.targets_for_files([
            "cloud_functions/knowledge_base_manager_universities/main.py",
        ]) == []

    def test_legacy_agents_emit_no_targets(self):
        """ADK + standalone tools (sourcery, source_curator, etc.) aren't
        part of the live app — exclude."""
        import detect_changed_targets as d
        assert d.targets_for_files([
            "agents/college_expert_adk/main.py",
            "agents/source_curator/main.py",
            "agents/sourcery/main.py",
            "agents/uniminer/main.py",
            "agents/university_profile_collector/main.py",
        ]) == []

    def test_live_agent_changes_map_correctly(self):
        import detect_changed_targets as d
        assert d.targets_for_files([
            "agents/college_expert_hybrid/main.py",
        ]) == ["agent-hybrid"]
        assert d.targets_for_files([
            "agents/college_expert_rag/main.py",
        ]) == ["agent-rag"]
        assert d.targets_for_files([
            "agents/college_expert_es/main.py",
        ]) == ["agent-es"]

    def test_dedup_and_sort(self):
        """Multiple files in the same target collapse; output is alphabetical
        so the deploy-step order is deterministic."""
        import detect_changed_targets as d
        out = d.targets_for_files([
            "frontend/src/x.ts",
            "cloud_functions/qa_agent/main.py",
            "cloud_functions/qa_agent/runner.py",
            "cloud_functions/qa_agent/scenarios/x.json",
        ])
        assert out == ["frontend", "qa-agent"]

    def test_each_live_function_maps(self):
        """Smoke-test every live mapping in one place — if someone deletes
        a row from PATH_TARGET_MAP this test catches it."""
        import detect_changed_targets as d
        cases = {
            "cloud_functions/profile_manager_v2/x.py": "profile-v2",
            "cloud_functions/payment_manager_v2/x.py": "payment-v2",
            "cloud_functions/counselor_agent/x.py": "counselor-agent",
            "cloud_functions/contact_form/x.py": "contact",
            "cloud_functions/knowledge_base_manager_universities_v2/x.py":
                "knowledge-universities-v2",
            "cloud_functions/knowledge_base_manager/x.py": "knowledge-rag",
            "cloud_functions/knowledge_base_manager_ES/x.py": "knowledge-es",
            "cloud_functions/qa_agent/x.py": "qa-agent",
            "agents/college_expert_hybrid/x.py": "agent-hybrid",
            "agents/college_expert_rag/x.py": "agent-rag",
            "agents/college_expert_es/x.py": "agent-es",
            "frontend/x.ts": "frontend",
        }
        for path, expected in cases.items():
            got = d.targets_for_files([path])
            assert got == [expected], f"{path} → {got}, expected [{expected!r}]"

    def test_ignores_top_level_misc_files(self):
        import detect_changed_targets as d
        assert d.targets_for_files([
            "package.json",
            "requirements-test.txt",
            "pytest.ini",
            ".gitignore",
        ]) == []

    def test_handles_empty_input(self):
        import detect_changed_targets as d
        assert d.targets_for_files([]) == []


# ---- CLI integration ------------------------------------------------------
# A single end-to-end test that verifies the script wires up `git diff` and
# emits the right targets for a known commit. We construct a throwaway repo
# in a tmp dir and make two commits — the second adds files in two live dirs
# plus one out-of-scope dir.


class TestCli:
    def test_cli_prints_targets_for_diff(self, tmp_path: Path):
        if shutil.which("git") is None:
            pytest.skip("git not on PATH")

        repo = tmp_path / "fake_repo"
        repo.mkdir()
        env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
               "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}

        def run(*args, check=True, capture=False):
            return subprocess.run(
                args, cwd=repo, env=env, check=check,
                capture_output=capture, text=True,
            )

        run("git", "init", "-q", "-b", "main")
        # commit 1 — empty baseline
        run("git", "commit", "-q", "--allow-empty", "-m", "init")

        # commit 2 — touch one live cloud function + frontend + a doc
        for rel in (
            "cloud_functions/qa_agent/main.py",
            "frontend/src/App.tsx",
            "docs/prd/foo.md",
            "cloud_functions/profile_manager/main.py",  # legacy → ignored
        ):
            full = repo / rel
            full.parent.mkdir(parents=True, exist_ok=True)
            full.write_text("# stub\n")
        run("git", "add", "-A")
        run("git", "commit", "-q", "-m", "feat")

        script = (
            Path(__file__).resolve().parents[2]
            / "scripts" / "cicd" / "detect_changed_targets.py"
        )
        proc = subprocess.run(
            [sys.executable, str(script), "--rev-range", "HEAD^..HEAD"],
            cwd=repo, env=env, capture_output=True, text=True, check=True,
        )
        targets = [t for t in proc.stdout.strip().splitlines() if t]
        assert targets == ["frontend", "qa-agent"], proc.stdout

    def test_cli_emits_nothing_on_docs_only_diff(self, tmp_path: Path):
        if shutil.which("git") is None:
            pytest.skip("git not on PATH")

        repo = tmp_path / "fake_repo_docs"
        repo.mkdir()
        env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
               "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}

        def run(*args):
            return subprocess.run(args, cwd=repo, env=env, check=True)

        run("git", "init", "-q", "-b", "main")
        run("git", "commit", "-q", "--allow-empty", "-m", "init")
        (repo / "docs").mkdir()
        (repo / "docs" / "x.md").write_text("hi\n")
        run("git", "add", "-A")
        run("git", "commit", "-q", "-m", "doc")

        script = (
            Path(__file__).resolve().parents[2]
            / "scripts" / "cicd" / "detect_changed_targets.py"
        )
        proc = subprocess.run(
            [sys.executable, str(script), "--rev-range", "HEAD^..HEAD"],
            cwd=repo, env=env, capture_output=True, text=True, check=True,
        )
        assert proc.stdout.strip() == "", proc.stdout
