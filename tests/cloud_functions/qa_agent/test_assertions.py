"""
Unit tests for the assertion library.

Each built-in assertion gets exercised against pass and fail cases. The
shape of AssertionResult is part of the report contract — any change to
field names will surface here.
"""

import assertions


def _ctx(**kwargs):
    base = {
        'status_code': 200,
        'response_json': {},
        'request_body': {},
        'elapsed_ms': 100,
    }
    base.update(kwargs)
    return base


def test_status_is_pass():
    r = assertions.status_is(200)(_ctx(status_code=200))
    assert r.passed
    assert r.message == ''


def test_status_is_fail():
    r = assertions.status_is(200)(_ctx(status_code=500))
    assert not r.passed
    assert '500' in r.message


def test_status_is_2xx():
    assert assertions.status_is_2xx()(_ctx(status_code=204)).passed
    assert assertions.status_is_2xx()(_ctx(status_code=299)).passed
    assert not assertions.status_is_2xx()(_ctx(status_code=300)).passed
    assert not assertions.status_is_2xx()(_ctx(status_code=199)).passed


def test_has_key_dotted_path_present():
    body = {'metadata': {'template_used': 'junior_spring'}}
    r = assertions.has_key('metadata.template_used')(_ctx(response_json=body))
    assert r.passed


def test_has_key_dotted_path_missing():
    body = {'metadata': {}}
    r = assertions.has_key('metadata.template_used')(_ctx(response_json=body))
    assert not r.passed
    assert 'metadata.template_used' in r.message


def test_key_equals_match():
    body = {'metadata': {'template_used': 'junior_spring'}}
    r = assertions.key_equals('metadata.template_used', 'junior_spring')(
        _ctx(response_json=body)
    )
    assert r.passed


def test_key_equals_mismatch():
    body = {'metadata': {'template_used': 'senior_fall'}}
    r = assertions.key_equals('metadata.template_used', 'junior_spring')(
        _ctx(response_json=body)
    )
    assert not r.passed
    assert 'senior_fall' in r.message


def test_key_in():
    body = {'status': 'pending'}
    assert assertions.key_in('status', ['pending', 'final'])(_ctx(response_json=body)).passed
    assert not assertions.key_in('status', ['final'])(_ctx(response_json=body)).passed


def test_list_non_empty():
    body = {'roadmap': {'phases': [{'id': 'p1'}]}}
    assert assertions.list_non_empty('roadmap.phases')(_ctx(response_json=body)).passed

    body = {'roadmap': {'phases': []}}
    assert not assertions.list_non_empty('roadmap.phases')(_ctx(response_json=body)).passed


def test_latency_under():
    assert assertions.latency_under(1000)(_ctx(elapsed_ms=500)).passed
    fail = assertions.latency_under(1000)(_ctx(elapsed_ms=2500))
    assert not fail.passed
    assert '2500' in fail.message


def test_run_all_keeps_going_on_failure():
    body = {'a': 1, 'b': 2}
    fns = [
        assertions.has_key('a'),
        assertions.has_key('missing'),
        assertions.has_key('b'),
    ]
    results = assertions.run_all(fns, _ctx(response_json=body))
    assert [r.passed for r in results] == [True, False, True]


def test_run_all_catches_assertion_crash():
    def crashy(_ctx):
        raise RuntimeError('boom')
    crashy.__name__ = 'crashy'
    results = assertions.run_all([crashy], _ctx())
    assert len(results) == 1
    assert not results[0].passed
    assert 'boom' in results[0].message


def test_all_passed_helper():
    r1 = assertions.AssertionResult(name='ok1', passed=True)
    r2 = assertions.AssertionResult(name='ok2', passed=True)
    r3 = assertions.AssertionResult(name='nope', passed=False, message='x')
    assert assertions.all_passed([r1, r2])
    assert not assertions.all_passed([r1, r2, r3])


# ---- key_non_empty_string ----------------------------------------------
# Stricter than has_key — catches regressions where an endpoint returns
# the right shape but with an empty/null/whitespace value. Critical for
# AI-generated text fields like the counselor chat /chat endpoint's
# `reply` field where shape-only checks would let a degraded LLM
# response pass.


class TestKeyNonEmptyString:
    def _ctx(self, body):
        return {"status_code": 200, "response_json": body, "elapsed_ms": 10}

    def test_passes_on_normal_string(self):
        check = assertions.key_non_empty_string("reply")
        r = check(self._ctx({"reply": "Hello, here is your roadmap."}))
        assert r.passed

    def test_fails_on_empty_string(self):
        """The canonical regression: LLM returns success: true with
        reply="" — passes status + has_key but is degraded UX."""
        check = assertions.key_non_empty_string("reply")
        r = check(self._ctx({"reply": ""}))
        assert not r.passed
        assert (
            "empty" in (r.message or "").lower()
            or "whitespace" in (r.message or "").lower()
        )

    def test_fails_on_whitespace_only(self):
        check = assertions.key_non_empty_string("reply")
        r = check(self._ctx({"reply": "   \n  "}))
        assert not r.passed

    def test_fails_on_null(self):
        check = assertions.key_non_empty_string("reply")
        r = check(self._ctx({"reply": None}))
        assert not r.passed
        assert "str" in (r.message or "")

    def test_fails_on_non_string(self):
        check = assertions.key_non_empty_string("reply")
        r = check(self._ctx({"reply": 42}))
        assert not r.passed
        assert "int" in (r.message or "")

    def test_fails_on_missing_key(self):
        check = assertions.key_non_empty_string("reply")
        r = check(self._ctx({"other_key": "x"}))
        assert not r.passed
        assert "missing" in (r.message or "").lower()

    def test_supports_dotted_path(self):
        check = assertions.key_non_empty_string("data.reply")
        r = check(self._ctx({"data": {"reply": "Hi there"}}))
        assert r.passed
