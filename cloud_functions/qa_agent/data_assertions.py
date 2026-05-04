"""
Cross-reference assertion library for the QA agent.

Standard assertions (in assertions.py) check shape: status_is_2xx,
key_equals, list_non_empty. These cross-reference assertions go a layer
deeper — they compare a response against a "ground truth" bag the
runner gathered before the scenario ran.

The principle: it's not enough for an endpoint to return 200. The data
it returns has to match what the source-of-truth (the knowledge base)
said it should be. Catches "API returns 200 but the data is wrong."

Each assertion returns a CrossRefResult — extends AssertionResult with
`expected` and `actual` fields, so the dashboard can render side-by-side
diffs when an assertion fails.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict, field
from typing import Any, Callable, Dict, List, Optional


# ---- Result ---------------------------------------------------------------


@dataclass
class CrossRefResult:
    """Cross-reference assertion result. Carries expected + actual so the
    dashboard can show a diff. `skipped` means the assertion couldn't run
    (typically: KB didn't have a record for the college we're checking)
    — distinct from passed/failed."""
    name: str
    passed: bool = False
    skipped: bool = False
    message: str = ""
    expected: Any = None
    actual: Any = None

    def to_dict(self) -> dict:
        return asdict(self)


AssertionFn = Callable[[Dict[str, Any]], CrossRefResult]


# ---- Helpers --------------------------------------------------------------


def _walk(obj: Any, dot_path: str):
    """Walk a dotted path. Returns (present, value)."""
    if not dot_path:
        return True, obj
    cur = obj
    for part in dot_path.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return False, None
    return True, cur


def _flatten(obj: Any, path: str) -> List[Any]:
    """Walk a path containing [*] wildcards. Returns the matched items.

    Example: path 'phases[*].tasks[*]' applied to
        {phases: [{tasks: [{a:1}, {a:2}]}, {tasks: [{a:3}]}]}
    yields [{a:1}, {a:2}, {a:3}].
    """
    if "[*]" not in path:
        present, value = _walk(obj, path)
        return [value] if present else []
    head, rest = path.split("[*]", 1)
    rest = rest.lstrip(".")
    present, list_val = _walk(obj, head)
    if not present or not isinstance(list_val, list):
        return []
    out = []
    for item in list_val:
        if rest:
            out.extend(_flatten(item, rest))
        else:
            out.append(item)
    return out


# ---- value_equals_truth ---------------------------------------------------


def value_equals_truth(response_path: str, truth_path: str) -> AssertionFn:
    """Asserts ctx['response_json'][response_path] equals
    ctx['truth_bag'][truth_path] (both dot paths).

    The truth_path's first segment is the college_id; subsequent segments
    address fields within the KB record. If the truth lookup misses, the
    assertion is SKIPPED (not failed).
    """
    name = f"{response_path} == truth.{truth_path}"

    def _check(ctx):
        response = ctx.get("response_json") or {}
        truth = ctx.get("truth_bag") or {}

        head, *rest = truth_path.split(".", 1)
        truth_record = truth.get(head)
        if not truth_record:
            return CrossRefResult(name=name, skipped=True,
                                  message=f"truth missing key '{head}'")
        truth_present, truth_val = _walk(truth_record, rest[0] if rest else "")
        if not truth_present:
            return CrossRefResult(name=name, skipped=True,
                                  message=f"truth missing field '{truth_path}'")

        resp_present, resp_val = _walk(response, response_path)
        if not resp_present:
            return CrossRefResult(
                name=name, passed=False,
                message=f"response missing path '{response_path}'",
                expected=truth_val, actual=None,
            )

        passed = resp_val == truth_val
        return CrossRefResult(
            name=name, passed=passed,
            expected=truth_val, actual=resp_val,
            message="" if passed else f"expected {truth_val!r}, got {resp_val!r}",
        )

    return _check


# ---- list_matches_truth_set ----------------------------------------------


def list_matches_truth_set(
    list_path: str,
    *,
    id_key: str,
    expected_ids: List[str],
) -> AssertionFn:
    """Asserts the list at response_json[list_path] contains exactly the
    same set of IDs as `expected_ids` — no missing entries, no orphans."""
    name = f"{list_path} matches expected id set"

    def _check(ctx):
        response = ctx.get("response_json") or {}
        present, list_val = _walk(response, list_path)
        if not present or not isinstance(list_val, list):
            return CrossRefResult(
                name=name, passed=False,
                message=f"response missing list at '{list_path}'",
                expected=sorted(expected_ids), actual=None,
            )
        actual_ids = sorted([item.get(id_key) for item in list_val if isinstance(item, dict)])
        expected_sorted = sorted(expected_ids)

        missing = sorted(set(expected_ids) - set(actual_ids))
        extra = sorted(set(actual_ids) - set(expected_ids))

        passed = (not missing) and (not extra)
        msg_parts = []
        if missing:
            msg_parts.append(f"missing: {missing}")
        if extra:
            msg_parts.append(f"orphans: {extra}")
        return CrossRefResult(
            name=name, passed=passed,
            expected=expected_sorted, actual=actual_ids,
            message="; ".join(msg_parts),
        )

    return _check


# ---- per_university_count_matches ----------------------------------------


def per_university_count_matches(
    *,
    list_path: str,
    id_key: str,
    truth_count_path: str,
    comparison: str = "gte",
) -> AssertionFn:
    """For each university_id present in either response or truth, count
    items in the response keyed to that id and compare against the truth
    count.

    `comparison` is 'gte' (response count >= truth count, useful for
    essay tracker — required + optional essays) or 'eq' (exact match).
    """
    name = f"{list_path} per-id count {comparison} truth.{truth_count_path}"

    def _check(ctx):
        response = ctx.get("response_json") or {}
        truth = ctx.get("truth_bag") or {}

        present, list_val = _walk(response, list_path)
        if not present or not isinstance(list_val, list):
            return CrossRefResult(
                name=name, passed=False,
                message=f"response missing list at '{list_path}'",
            )

        actual_counts: Dict[str, int] = {}
        for item in list_val:
            if isinstance(item, dict):
                cid = item.get(id_key)
                if cid:
                    actual_counts[cid] = actual_counts.get(cid, 0) + 1

        mismatches = []
        for college_id, truth_record in truth.items():
            if not truth_record:  # KB miss — skip this id
                continue
            tpresent, expected_count = _walk(truth_record, truth_count_path)
            if not tpresent:
                continue
            if not isinstance(expected_count, int):
                continue
            actual = actual_counts.get(college_id, 0)
            ok = (actual >= expected_count) if comparison == "gte" else (actual == expected_count)
            if not ok:
                mismatches.append(
                    f"{college_id}: actual={actual}, expected{'>=' if comparison == 'gte' else '=='}{expected_count}"
                )

        passed = not mismatches
        return CrossRefResult(
            name=name, passed=passed,
            expected={k: _walk(v, truth_count_path)[1] for k, v in truth.items() if v},
            actual=actual_counts,
            message="; ".join(mismatches),
        )

    return _check


# ---- deep_link_resolves --------------------------------------------------


def deep_link_resolves(
    *,
    list_path: str,
    id_path: str,
    valid_ids: List[str],
) -> AssertionFn:
    """Walks list_path (with [*] wildcards), reads each item's id_path,
    asserts it's in valid_ids. Items without the id_path (e.g., tasks
    without artifact_ref) are ignored — this catches *broken* links, not
    *missing* ones."""
    name = f"deep links resolve into {len(valid_ids)} known ids"
    valid_set = set(valid_ids)

    def _check(ctx):
        response = ctx.get("response_json") or {}
        items = _flatten(response, list_path)

        seen = []
        orphans = []
        for item in items:
            if not isinstance(item, dict):
                continue
            present, ref_id = _walk(item, id_path)
            if not present or ref_id is None:
                continue
            seen.append(ref_id)
            if ref_id not in valid_set:
                orphans.append(ref_id)

        passed = not orphans
        return CrossRefResult(
            name=name, passed=passed,
            expected=sorted(valid_ids), actual=sorted(set(seen)),
            message=f"orphan refs: {sorted(set(orphans))}" if orphans else "",
        )

    return _check


# ---- runner integration ---------------------------------------------------


def run_all(
    assertions: List[AssertionFn],
    ctx: Dict[str, Any],
) -> List[CrossRefResult]:
    """Run every assertion against ctx; never raise."""
    out = []
    for fn in assertions:
        try:
            out.append(fn(ctx))
        except Exception as exc:  # noqa: BLE001
            out.append(CrossRefResult(
                name=getattr(fn, "__name__", "anonymous"),
                passed=False,
                message=f"assertion crashed: {type(exc).__name__}: {exc}",
            ))
    return out


def all_passed(results: List[CrossRefResult]) -> bool:
    """Skipped doesn't count as failed."""
    return all(r.passed or r.skipped for r in results)
