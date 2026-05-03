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


def _good_poster(seq):
    """Returns a poster that hands out the next response in `seq` per call."""
    seq = list(seq)

    def _poster(url, body, **kwargs):
        if not seq:
            raise AssertionError(f'no canned response for {url}')
        ctx = seq.pop(0)
        ctx.setdefault('url', url)
        ctx.setdefault('method', 'POST')
        ctx.setdefault('request_body', body)
        ctx.setdefault('elapsed_ms', 50)
        ctx.setdefault('response_excerpt', '')
        ctx.setdefault('network_error', None)
        return ctx

    return _poster


def _ok(json_body):
    return {
        'status_code': 200,
        'response_json': json_body,
        'response_excerpt': str(json_body)[:200],
    }


def test_runner_happy_path_all_pass():
    """Every step returns 2xx + the expected body shape — overall pass."""
    scenario = _scenario()
    cfg = _make_cfg()

    # Sequence: setup, profile, add MIT, add Stanford, roadmap, work-feed,
    # deadlines, teardown.
    canned = [
        _ok({'ok': True, 'deleted': {}}),                    # setup
        _ok({'success': True}),                              # profile
        _ok({'success': True}),                              # add mit
        _ok({'success': True}),                              # add stanford
        _ok({                                                # roadmap
            'success': True,
            'metadata': {
                'template_used': 'junior_spring',
                'resolution_source': 'profile',
            },
            'roadmap': {'phases': [{'id': 'p1', 'name': 'Phase 1', 'tasks': []}]},
        }),
        _ok({'success': True, 'items': []}),                 # work-feed
        _ok({'success': True, 'deadlines': []}),             # deadlines
        _ok({'ok': True, 'deleted': {}}),                    # final teardown
    ]

    result = runner.run_scenario(scenario, cfg, poster=_good_poster(canned))
    assert result['passed'] is True
    assert result['scenario_id'] == 'demo'
    assert len(result['steps']) == 8
    for step in result['steps']:
        assert step['passed'], f"{step['name']} failed: {step['assertions']}"


def test_runner_records_failures_without_aborting():
    """A step that returns 500 should fail but the rest of the steps still run."""
    scenario = _scenario()
    cfg = _make_cfg()
    canned = [
        _ok({'ok': True, 'deleted': {}}),
        # Profile call fails
        {'status_code': 500, 'response_json': {'error': 'kaboom'},
         'response_excerpt': 'kaboom'},
        _ok({'success': True}),
        _ok({'success': True}),
        _ok({  # roadmap still runs
            'success': True,
            'metadata': {
                'template_used': 'junior_spring',
                'resolution_source': 'profile',
            },
            'roadmap': {'phases': [{'id': 'p', 'name': 'p', 'tasks': []}]},
        }),
        _ok({'success': True, 'items': []}),
        _ok({'success': True}),
        _ok({'ok': True, 'deleted': {}}),
    ]

    result = runner.run_scenario(scenario, cfg, poster=_good_poster(canned))
    assert result['passed'] is False
    profile_step = next(s for s in result['steps'] if s['name'] == 'profile_build')
    assert profile_step['passed'] is False
    # Roadmap step still ran
    roadmap_step = next(s for s in result['steps'] if s['name'] == 'roadmap_generate')
    assert roadmap_step['passed'] is True


def test_runner_includes_scenario_id_and_variation():
    scenario = _scenario()
    cfg = _make_cfg()
    # Fresh dict per call — `[_ok(...)] * 8` would share state via setdefault.
    canned = [_ok({'ok': True}) for _ in range(8)]
    result = runner.run_scenario(scenario, cfg, poster=_good_poster(canned))
    assert result['variation'] == {'student_name': 'Test User'}
    assert result['scenario_id'] == 'demo'
    assert 'started_at' in result and 'ended_at' in result


def test_runner_redacts_full_names_in_request_logs():
    """Request bodies in the report should not carry full names from the
    LLM variation — the test student name is reduced to first initial."""
    scenario = _scenario()
    scenario['profile_template']['full_name'] = 'Sam Adler'
    cfg = _make_cfg()
    canned = [_ok({}) for _ in range(8)]
    result = runner.run_scenario(scenario, cfg, poster=_good_poster(canned))
    profile_step = next(s for s in result['steps'] if s['name'] == 'profile_build')
    # In the redacted request: full_name became 'S.'
    inner_profile = (profile_step['request'] or {}).get('profile') or {}
    assert inner_profile.get('full_name') == 'S.'


def test_runner_passes_admin_token_on_teardown():
    scenario = _scenario()
    cfg = _make_cfg()
    captured = []

    def _poster(url, body, **kwargs):
        captured.append({'url': url, 'kwargs': kwargs})
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
            'request_body': body,
            'url': url,
            'method': 'POST',
        }

    runner.run_scenario(scenario, cfg, poster=_poster)
    teardown_calls = [c for c in captured if 'clear-test-data' in c['url']]
    assert len(teardown_calls) == 2  # setup + final
    for c in teardown_calls:
        assert c['kwargs'].get('admin_token') == 'test-admin-token'


def test_runner_network_error_marks_step_failed():
    scenario = _scenario()
    cfg = _make_cfg()

    def _poster(url, body, **kwargs):
        return {
            'status_code': 0,
            'response_json': None,
            'response_excerpt': '',
            'elapsed_ms': 0,
            'network_error': 'ConnectionError: refused',
            'request_body': body,
            'url': url,
            'method': 'POST',
        }

    result = runner.run_scenario(scenario, cfg, poster=_poster)
    assert result['passed'] is False
    # First step should record the network error
    setup_step = result['steps'][0]
    assert any('refused' in a['message'] for a in setup_step['assertions']
               if not a['passed'])
