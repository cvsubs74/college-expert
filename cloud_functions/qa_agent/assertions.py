"""
Pluggable assertion library for QA agent step results.

Each assertion is a small function that takes the response context and
returns an AssertionResult. The runner collects these per step and rolls
them up into pass/fail.

Why functions instead of pytest? The agent needs:
  - Structured pass/fail records suitable for serialization to Firestore.
  - Soft failures — one assertion failing should not abort the rest of
    the step's checks.
  - Plain-English failure messages a human reviewing the report can act
    on without running a debugger.

Adding a new assertion = drop a function with this signature:
    def my_assertion(ctx) -> AssertionResult: ...
where ctx is a dict with keys: status_code, response_json, request_body,
elapsed_ms.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Callable, Dict, List, Optional


@dataclass
class AssertionResult:
    name: str
    passed: bool
    message: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


AssertionFn = Callable[[Dict[str, Any]], AssertionResult]


# ---- Built-in assertions ----------------------------------------------------


def status_is(expected: int) -> AssertionFn:
    def _check(ctx):
        actual = ctx.get("status_code")
        return AssertionResult(
            name=f"status=={expected}",
            passed=actual == expected,
            message=f"got status {actual}" if actual != expected else "",
        )
    return _check


def status_is_2xx() -> AssertionFn:
    def _check(ctx):
        actual = ctx.get("status_code", 0)
        ok = 200 <= actual < 300
        return AssertionResult(
            name="status=2xx",
            passed=ok,
            message=f"got status {actual}" if not ok else "",
        )
    return _check


def has_key(path: str) -> AssertionFn:
    """Asserts response_json contains `path` (dot-notation: "metadata.template_used")."""
    def _check(ctx):
        body = ctx.get("response_json") or {}
        present, _ = _walk(body, path)
        return AssertionResult(
            name=f"has key '{path}'",
            passed=present,
            message=f"missing key '{path}'" if not present else "",
        )
    return _check


def key_equals(path: str, expected: Any) -> AssertionFn:
    def _check(ctx):
        body = ctx.get("response_json") or {}
        present, value = _walk(body, path)
        if not present:
            return AssertionResult(
                name=f"{path}=={expected!r}",
                passed=False,
                message=f"missing key '{path}'",
            )
        return AssertionResult(
            name=f"{path}=={expected!r}",
            passed=value == expected,
            message=f"got {value!r}" if value != expected else "",
        )
    return _check


def key_in(path: str, allowed: List[Any]) -> AssertionFn:
    def _check(ctx):
        body = ctx.get("response_json") or {}
        present, value = _walk(body, path)
        if not present:
            return AssertionResult(
                name=f"{path} in {allowed}",
                passed=False,
                message=f"missing key '{path}'",
            )
        return AssertionResult(
            name=f"{path} in {allowed}",
            passed=value in allowed,
            message=f"got {value!r}" if value not in allowed else "",
        )
    return _check


def list_non_empty(path: str) -> AssertionFn:
    def _check(ctx):
        body = ctx.get("response_json") or {}
        present, value = _walk(body, path)
        if not present:
            return AssertionResult(
                name=f"{path} is non-empty list",
                passed=False,
                message=f"missing key '{path}'",
            )
        ok = isinstance(value, list) and len(value) > 0
        return AssertionResult(
            name=f"{path} is non-empty list",
            passed=ok,
            message=(
                f"got {type(value).__name__} with len={len(value) if hasattr(value, '__len__') else '?'}"
                if not ok else ""
            ),
        )
    return _check


def latency_under(max_ms: int) -> AssertionFn:
    def _check(ctx):
        elapsed = ctx.get("elapsed_ms", 0)
        return AssertionResult(
            name=f"latency<{max_ms}ms",
            passed=elapsed <= max_ms,
            message=f"took {elapsed}ms" if elapsed > max_ms else "",
        )
    return _check


# ---- Helpers ----------------------------------------------------------------


def _walk(obj: Any, dot_path: str):
    """Walks `obj` along dot-separated path. Returns (present, value)."""
    cur = obj
    for part in dot_path.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return False, None
    return True, cur


def run_all(assertions: List[AssertionFn], ctx: Dict[str, Any]) -> List[AssertionResult]:
    """Run all assertions against ctx, never raising."""
    results: List[AssertionResult] = []
    for fn in assertions:
        try:
            results.append(fn(ctx))
        except Exception as exc:  # noqa: BLE001 — assertion failures are data
            results.append(
                AssertionResult(
                    name=getattr(fn, "__name__", "anonymous"),
                    passed=False,
                    message=f"assertion crashed: {type(exc).__name__}: {exc}",
                )
            )
    return results


def all_passed(results: List[AssertionResult]) -> bool:
    return all(r.passed for r in results)
