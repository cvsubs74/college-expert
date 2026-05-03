"""
Unit tests for the scenario runner.

The runner makes real-looking HTTP calls; we inject a fake `poster` to
record what the runner WOULD have called and return canned responses.
This exercises the assertion + step-record logic without network.
"""

import runner


def _make_cfg():
    return runner.RunConfig(
        profile_manager_url='https://pm.test',
        counselor_agent_url='https://ca.test',
        admin_token='test-admin-token',
        id_token='test-id-token',
        test_user_email='duser8531@gmail.com',
    )


def _scenario():
    return {
        'id': 'demo',
        'description': 'demo scenario',
        'profile_template': {
            'grade_level': '11th Grade',
            'graduation_year': 2027,
            'gpa': 3.7,
        },
        'colleges_template': ['mit', 'stanford_university'],
        'expected_template_used': 'junior_spring',
        '_variation': {'student_name': 'Test User'},
    }


def _ok(json_body):
    return {
        'status_code': 200,
        'response_json': json_body,
        'response_excerpt': str(json_body)[:200],
    }


# Default response shapes by URL substring — the runner now makes a
# variable number of HTTP calls per scenario (profile_build alone is one
# call per profile_template field), so a positional canned-list approach
# is brittle. URL-aware defaults match the real prod responses; tests
# that need failure injection pass `overrides`.
_URL_DEFAULTS = (
    ('clear-test-data', _ok({'ok': True, 'deleted': {}})),
    ('update-structured-field', _ok({'success': True})),
    ('add-to-list', _ok({'success': True})),
    ('roadmap', _ok({
        'success': True,
        'metadata': {
            'template_used': 'junior_spring',
            'resolution_source': 'profile',
        },
        'roadmap': {'phases': [{'id': 'p1', 'name': 'Phase 1', 'tasks': []}]},
    })),
    ('work-feed', _ok({'success': True, 'items': []})),
    ('deadlines', _ok({'success': True, 'deadlines': []})),
)


def _smart_poster(overrides=None, capture=None):
    """A URL-aware fake poster.

    `overrides` is a list of (url_substring, response_dict) — first match
    wins, used to inject failures.

    `capture`, if provided, is a list the poster appends each call's
    metadata into for tests that need to assert on call kwargs.

    Mirrors `_post`'s signature so the runner's GET-mode work-feed call
    works without a TypeError.
    """
    overrides = list(overrides or [])

    def _poster(url, body=None, *, method='POST', params=None, **kwargs):
        if capture is not None:
            capture.append({'url': url, 'method': method, 'kwargs': kwargs})

        # Pick a response: explicit override first, else URL default.
        chosen = None
        for pattern, resp in overrides:
            if pattern in url:
                chosen = resp
                break
        if chosen is None:
            for pattern, resp in _URL_DEFAULTS:
                if pattern in url:
                    chosen = resp
                    break
        if chosen is None:
            chosen = _ok({'success': True, 'ok': True})

        # Copy because the runner-side `_step` mutates request_body etc.
        ctx = dict(chosen)
        ctx.setdefault('url', url)
        ctx.setdefault('method', method)
        ctx.setdefault('request_body', body if body is not None else (params or {}))
        ctx.setdefault('elapsed_ms', 50)
        ctx.setdefault('response_excerpt', '')
        ctx.setdefault('network_error', None)
        return ctx

    return _poster


def test_runner_happy_path_all_pass():
    """Every step returns 2xx + the expected body shape — overall pass.

    URL-aware defaults (in _smart_poster) yield the response shape each
    endpoint actually produces, so we don't have to hand-curate one
    canned response per HTTP call (and we don't break when the runner's
    call count changes — e.g. profile_build now makes one call per
    profile_template field)."""
    scenario = _scenario()
    cfg = _make_cfg()

    result = runner.run_scenario(scenario, cfg, poster=_smart_poster())
    assert result['passed'] is True
    assert result['scenario_id'] == 'demo'
    # Steps: setup, profile_build (rolled-up), add_college × 2,
    # roadmap, work_feed, deadlines, final_teardown.
    assert len(result['steps']) == 8
    for step in result['steps']:
        assert step['passed'], f"{step['name']} failed: {step['assertions']}"


def test_runner_records_failures_without_aborting():
    """A profile call returning 500 should mark profile_build as failed
    but every subsequent step should still run."""
    scenario = _scenario()
    cfg = _make_cfg()

    # Inject a 500 on the per-field profile-update endpoint. Every other
    # URL falls through to its default success response.
    overrides = [(
        'update-structured-field',
        {
            'status_code': 500,
            'response_json': {'error': 'kaboom'},
            'response_excerpt': 'kaboom',
        },
    )]
    result = runner.run_scenario(
        scenario, cfg, poster=_smart_poster(overrides=overrides),
    )

    assert result['passed'] is False
    profile_step = next(s for s in result['steps'] if s['name'] == 'profile_build')
    assert profile_step['passed'] is False
    # Roadmap step still ran (default success URL response).
    roadmap_step = next(s for s in result['steps'] if s['name'] == 'roadmap_generate')
    assert roadmap_step['passed'] is True
    # Final teardown still ran (last step).
    teardown = next(s for s in result['steps'] if s['name'] == 'final_teardown')
    assert teardown['passed'] is True


def test_runner_includes_scenario_id_and_variation():
    scenario = _scenario()
    cfg = _make_cfg()
    result = runner.run_scenario(scenario, cfg, poster=_smart_poster())
    assert result['variation'] == {'student_name': 'Test User'}
    assert result['scenario_id'] == 'demo'
    assert 'started_at' in result and 'ended_at' in result


def test_runner_redacts_full_names_in_request_logs():
    """Request bodies in the report should not carry full names from the
    LLM variation — the test student name is reduced to first initial.

    With profile_build now hitting /update-structured-field per-field,
    the runner only logs `{fields: [...]}` at the step level — but the
    redaction guard still has to apply to any captured body. Verify by
    checking that NO step's recorded request leaks 'Sam Adler' verbatim.
    """
    scenario = _scenario()
    scenario['profile_template']['full_name'] = 'Sam Adler'
    cfg = _make_cfg()

    result = runner.run_scenario(scenario, cfg, poster=_smart_poster())
    # No step's serialized request should leak the full name.
    for step in result['steps']:
        request_str = str(step.get('request') or {})
        assert 'Sam Adler' not in request_str, (
            f"step {step['name']} leaked full name: {request_str}"
        )


def test_runner_passes_admin_token_on_teardown():
    scenario = _scenario()
    cfg = _make_cfg()
    captured = []

    def _poster(url, body=None, *, method='POST', params=None, **kwargs):
        captured.append({'url': url, 'method': method, 'kwargs': kwargs})
        return {
            'status_code': 200,
            'response_json': {
                'ok': True, 'success': True,
                'metadata': {
                    'template_used': 'junior_spring',
                    'resolution_source': 'profile',
                },
                'roadmap': {'phases': [{'id': 'p', 'name': 'p', 'tasks': []}]},
                'items': [],
            },
            'response_excerpt': '',
            'elapsed_ms': 10,
            'network_error': None,
            'request_body': body if body is not None else (params or {}),
            'url': url,
            'method': method,
        }

    runner.run_scenario(scenario, cfg, poster=_poster)
    teardown_calls = [c for c in captured if 'clear-test-data' in c['url']]
    assert len(teardown_calls) == 2  # setup + final
    for c in teardown_calls:
        assert c['kwargs'].get('admin_token') == 'test-admin-token'


def test_runner_network_error_marks_step_failed():
    scenario = _scenario()
    cfg = _make_cfg()

    def _poster(url, body=None, *, method='POST', params=None, **kwargs):
        return {
            'status_code': 0,
            'response_json': None,
            'response_excerpt': '',
            'elapsed_ms': 0,
            'network_error': 'ConnectionError: refused',
            'request_body': body if body is not None else (params or {}),
            'url': url,
            'method': method,
        }

    result = runner.run_scenario(scenario, cfg, poster=_poster)
    assert result['passed'] is False
    # First step should record the network error
    setup_step = result['steps'][0]
    assert any('refused' in a['message'] for a in setup_step['assertions']
               if not a['passed'])
