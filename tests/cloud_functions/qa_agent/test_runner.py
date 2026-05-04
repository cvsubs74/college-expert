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
# Match order matters: more specific (longer) prefixes go FIRST. The
# previous order had 'roadmap' before 'roadmap_deep_link_integrity'-style
# checks, which still works because we match on URL substring not step
# name. But 'get-college-list' etc. must come before generic shape
# defaults to ensure they're picked up.
_URL_DEFAULTS = (
    ('clear-test-data', _ok({'ok': True, 'deleted': {}})),
    ('update-structured-field', _ok({'success': True})),
    ('add-to-list', _ok({'success': True})),
    # Counselor chat default — well-formed reply so the chat step
    # passes when an archetype declares chat_question.
    ('chat', _ok({
        'success': True,
        'reply': 'Focus on your essays this week.',
        'suggested_actions': [],
    })),
    # New default for the symmetry-check step. The two scenarios in
    # _scenario() use ['mit', 'stanford_university'] — return both.
    ('get-college-list', _ok({
        'success': True,
        'college_list': [
            {'university_id': 'mit', 'name': 'MIT'},
            {'university_id': 'stanford_university', 'name': 'Stanford University'},
        ],
    })),
    # Essay tracker default — returns 0 essays per college, which
    # passes the gte assertion (KB miss → SKIP for required count).
    ('get-essay-tracker', _ok({
        'success': True,
        'essays': [],
    })),
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
    # Steps with the smart-QA upgrades:
    #   setup, gather_ground_truth, profile_build, add_college × 2,
    #   verify_college_list_symmetry, roadmap_generate,
    #   roadmap_deep_link_integrity, work_feed,
    #   essay_tracker_alignment, deadlines, final_teardown
    # = 12 steps for the 2-college demo scenario.
    assert len(result['steps']) == 12
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


# ---------------------------------------------------------------------------
# Date-aware expected-template computation
#
# The runner used to compare the resolver's metadata.template_used against
# whatever the scenario file declared in `expected_template_used`. That
# made every _fall and _summer scenario fail in spring (and vice versa)
# because the resolver computes the template from (graduation_year, today).
#
# Fix: derive the expected template from (profile_template.graduation_year,
# today) inside the runner, mirroring planner.resolve_template_key. The
# scenario's static `expected_template_used` field is now advisory only —
# kept as a human-readable hint, but not the assertion source.
#
# The helper reproduces planner.py's grade/semester mapping. If planner
# changes, update the helper here too — the duplication is intentional
# (cross-function call would add latency to every scenario), and these
# tests pin the contract.
# ---------------------------------------------------------------------------

import pytest
from datetime import datetime


class TestExpectedTemplateForProfile:
    @pytest.mark.parametrize('grad_year,today,expected', [
        # Senior fall (Aug-Dec, graduating next year)
        (2027, datetime(2026, 9, 15), 'senior_fall'),
        (2027, datetime(2026, 12, 1), 'senior_fall'),
        # Senior spring (Jan-May, graduating this year)
        (2026, datetime(2026, 4, 1), 'senior_spring'),
        (2026, datetime(2026, 1, 15), 'senior_spring'),
        # Junior fall
        (2028, datetime(2026, 9, 1), 'junior_fall'),
        # Junior spring
        (2027, datetime(2026, 4, 1), 'junior_spring'),
        # Junior summer (the only summer template that exists)
        (2027, datetime(2026, 7, 15), 'junior_summer'),
        # Sophomore fall
        (2029, datetime(2026, 9, 1), 'sophomore_fall'),
        # Sophomore spring
        (2028, datetime(2026, 3, 1), 'sophomore_spring'),
        # Sophomore summer → falls back to sophomore_spring
        (2028, datetime(2026, 7, 15), 'sophomore_spring'),
        # Freshman fall
        (2030, datetime(2026, 9, 1), 'freshman_fall'),
        # Freshman spring
        (2029, datetime(2026, 3, 1), 'freshman_spring'),
        # Freshman summer → falls back to freshman_spring
        (2029, datetime(2026, 7, 15), 'freshman_spring'),
        # Already graduated → caps at senior_*
        (2024, datetime(2026, 4, 1), 'senior_spring'),
        (2024, datetime(2026, 9, 1), 'senior_fall'),
    ])
    def test_grad_year_and_today_map_to_template(self, grad_year, today, expected):
        profile = {'graduation_year': grad_year}
        assert runner._expected_template_for(profile, today=today) == expected

    def test_returns_none_when_graduation_year_missing(self):
        # No way to compute → return None so the runner skips the assertion.
        assert runner._expected_template_for({}, today=datetime(2026, 5, 15)) is None
        assert runner._expected_template_for(
            {'graduation_year': None}, today=datetime(2026, 5, 15),
        ) is None

    def test_returns_none_when_graduation_year_unparseable(self):
        # Treat a non-int graduation_year as missing — never crash the run.
        assert runner._expected_template_for(
            {'graduation_year': 'not a year'}, today=datetime(2026, 5, 15),
        ) is None

    def test_uses_today_arg_not_real_now(self):
        # Inject a mid-July date — should pick junior_summer for a 2027 grad.
        result = runner._expected_template_for(
            {'graduation_year': 2027}, today=datetime(2026, 7, 15),
        )
        assert result == 'junior_summer'


class TestRoadmapAssertionUsesComputedTemplate:
    """Integration: the roadmap_generate step must assert the COMPUTED
    template (date-aware), not the scenario file's static field. Pre-fix,
    today=May 2026 + scenario claiming 'junior_fall' would FAIL the
    assertion even though the resolver was correctly returning
    'junior_spring'."""

    def test_assertion_uses_computed_template(self, monkeypatch):
        scenario = _scenario()
        # Pretend the helper computes 'junior_summer' regardless of the
        # scenario's static field — the assertion MUST track the helper.
        monkeypatch.setattr(runner, '_expected_template_for',
                            lambda profile, today=None: 'junior_summer')
        cfg = _make_cfg()

        # Roadmap returns junior_summer — should match the helper.
        overrides = [(
            'roadmap',
            _ok({
                'success': True,
                'metadata': {
                    'template_used': 'junior_summer',
                    'resolution_source': 'profile',
                },
                'roadmap': {'phases': [{'id': 'p', 'name': 'p', 'tasks': []}]},
            }),
        )]
        result = runner.run_scenario(
            scenario, cfg, poster=_smart_poster(overrides=overrides),
        )
        roadmap_step = next(s for s in result['steps'] if s['name'] == 'roadmap_generate')
        assert roadmap_step['passed'], (
            f"roadmap_generate should pass when helper-computed template "
            f"matches the response. Failures: "
            f"{[a for a in roadmap_step['assertions'] if not a['passed']]}"
        )

    def test_assertion_skipped_when_helper_returns_none(self, monkeypatch):
        """If we can't compute an expected template (no graduation_year),
        the assertion is skipped — not asserted against the static field."""
        scenario = _scenario()
        scenario['profile_template'].pop('graduation_year', None)
        scenario['expected_template_used'] = 'whatever_fall'  # would fail if used
        cfg = _make_cfg()

        monkeypatch.setattr(runner, '_expected_template_for',
                            lambda profile, today=None: None)

        result = runner.run_scenario(scenario, cfg, poster=_smart_poster())
        roadmap_step = next(s for s in result['steps'] if s['name'] == 'roadmap_generate')
        template_eq_assertions = [
            a for a in roadmap_step['assertions']
            if 'template_used==' in a.get('name', '')
        ]
        assert template_eq_assertions == [], (
            f"Should skip template_used equality check when helper returns "
            f"None. Found: {template_eq_assertions}"
        )


# ---- compute_fit step ----------------------------------------------------
# Phase 1 of fit testing — runner now adds a `compute_fit:<uni>` step
# when the scenario carries a `fit_target_college` field, otherwise
# scenarios stay roadmap-only (today's behaviour). Spec:
# docs/prd/qa-fit-testing.md.


def _good_fit_response(uni_id, *, category='SUPER_REACH',
                       match_pct=20, acc_rate=4.0):
    """Synthetic /compute-single-fit response that satisfies every
    Phase 1 invariant. Tests perturb specific fields to flip individual
    assertions."""
    return _ok({
        'success': True,
        'fit_analysis': {
            'fit_category': category,
            'match_percentage': match_pct,
            'acceptance_rate': acc_rate,
            'university_name': uni_id.replace('_', ' ').title(),
            'university_id': uni_id,
            'factors': [
                {'name': 'Academic',    'score': 35, 'max': 40, 'detail': 'x'},
                {'name': 'Holistic',    'score': 25, 'max': 30, 'detail': 'x'},
                {'name': 'Major Fit',   'score': 13, 'max': 15, 'detail': 'x'},
                {'name': 'Selectivity', 'score': -15, 'max': 5, 'detail': 'x'},
            ],
            'explanation': 'Five-or-six sentence analysis here.',
            'essay_angles': [{'essay_prompt': 'Why us', 'angle': 'x'}],
            'application_timeline': {'recommended_plan': 'RD',
                                     'deadline': '2027-01-01'},
            'scholarship_matches': [{'name': 'Merit', 'amount': '$1k'}],
            'test_strategy': {'recommendation': 'Submit'},
            'major_strategy': {'intended_major': 'CS', 'is_available': True},
            'demonstrated_interest_tips': ['visit campus'],
            'red_flags_to_avoid': ['typos'],
            'recommendations': [{'action': 'improve essays'}],
        },
    })


def _scenario_with_fit_target(uni_id='massachusetts_institute_of_technology',
                              expected='SUPER_REACH'):
    s = _scenario()
    s['id'] = 'fit_demo'
    s['colleges_template'] = [uni_id]
    s['fit_target_college'] = uni_id
    s['fit_expected_category'] = expected
    return s


class TestComputeFitStep:
    def test_omitted_by_default_when_archetype_lacks_fit_target(self):
        """Roadmap-only scenarios (the historical default) must not
        sprout a compute_fit step. Backwards compat for every existing
        archetype that doesn't opt in."""
        cfg = _make_cfg()
        scenario = _scenario()  # no fit_target_college
        result = runner.run_scenario(scenario, cfg, poster=_smart_poster())
        step_names = [s['name'] for s in result['steps']]
        assert not any(n.startswith('compute_fit') for n in step_names), (
            f"compute_fit should be absent. Got steps: {step_names}"
        )

    def test_step_added_when_fit_target_set(self):
        cfg = _make_cfg()
        scenario = _scenario_with_fit_target()
        overrides = [(
            'compute-single-fit',
            _good_fit_response('massachusetts_institute_of_technology'),
        )]
        result = runner.run_scenario(
            scenario, cfg, poster=_smart_poster(overrides=overrides),
        )
        fit_steps = [s for s in result['steps']
                     if s['name'].startswith('compute_fit:')]
        assert len(fit_steps) == 1
        assert 'massachusetts_institute_of_technology' in fit_steps[0]['name']

    def test_step_passes_on_well_formed_response(self):
        cfg = _make_cfg()
        scenario = _scenario_with_fit_target()
        overrides = [(
            'compute-single-fit',
            _good_fit_response('massachusetts_institute_of_technology'),
        )]
        result = runner.run_scenario(
            scenario, cfg, poster=_smart_poster(overrides=overrides),
        )
        fit_step = next(s for s in result['steps']
                        if s['name'].startswith('compute_fit:'))
        assert fit_step['passed'], (
            f"Expected pass but got assertion failures: "
            f"{[a for a in fit_step['assertions'] if not a['passed']]}"
        )

    def test_step_fails_when_selectivity_floor_violated(self):
        """The canonical regression: a 4%-acceptance school flagged
        as TARGET. The selectivity-floor assertion catches this."""
        cfg = _make_cfg()
        scenario = _scenario_with_fit_target(expected='SUPER_REACH')
        bad = _good_fit_response(
            'massachusetts_institute_of_technology',
            category='TARGET',  # ← the bug: 4% school called TARGET
            match_pct=60,
            acc_rate=4.0,
        )
        overrides = [('compute-single-fit', bad)]
        result = runner.run_scenario(
            scenario, cfg, poster=_smart_poster(overrides=overrides),
        )
        fit_step = next(s for s in result['steps']
                        if s['name'].startswith('compute_fit:'))
        assert not fit_step['passed']
        # The selectivity-floor assertion + the expected-category pin
        # should both fail with informative messages.
        floor_failed = [a for a in fit_step['assertions']
                        if 'floor' in a['name'].lower() and not a['passed']]
        assert floor_failed, (
            f"Selectivity-floor assertion should have failed. "
            f"Got: {fit_step['assertions']}"
        )

    def test_step_fails_when_match_percentage_outside_band(self):
        """SUPER_REACH at 50% match — post-processor regression case."""
        cfg = _make_cfg()
        scenario = _scenario_with_fit_target()
        bad = _good_fit_response(
            'massachusetts_institute_of_technology',
            category='SUPER_REACH',
            match_pct=50,  # SUPER_REACH must be 0-34
            acc_rate=4.0,
        )
        overrides = [('compute-single-fit', bad)]
        result = runner.run_scenario(
            scenario, cfg, poster=_smart_poster(overrides=overrides),
        )
        fit_step = next(s for s in result['steps']
                        if s['name'].startswith('compute_fit:'))
        assert not fit_step['passed']
        band_failed = [a for a in fit_step['assertions']
                       if 'band' in a['name'].lower() and not a['passed']]
        assert band_failed

    def test_step_calls_profile_manager_compute_single_fit(self):
        """The fit step must hit profile_manager_v2's endpoint with
        {user_email, university_id} — confirms the contract."""
        cfg = _make_cfg()
        scenario = _scenario_with_fit_target()
        capture = []
        overrides = [(
            'compute-single-fit',
            _good_fit_response('massachusetts_institute_of_technology'),
        )]
        runner.run_scenario(
            scenario, cfg,
            poster=_smart_poster(overrides=overrides, capture=capture),
        )
        fit_calls = [c for c in capture if 'compute-single-fit' in c['url']]
        assert len(fit_calls) == 1
        assert fit_calls[0]['url'].startswith('https://pm.test')

    def test_step_uses_extended_timeout_for_cold_start(self):
        """The /compute-single-fit endpoint cold-starts and runs an LLM
        call; the default 30s poster timeout is too tight (verified in
        PR #76 post-deploy: a cold path took ~40s end-to-end). The fit
        step must pass timeout=90 to give cold starts headroom."""
        cfg = _make_cfg()
        scenario = _scenario_with_fit_target()
        capture = []
        overrides = [(
            'compute-single-fit',
            _good_fit_response('massachusetts_institute_of_technology'),
        )]
        runner.run_scenario(
            scenario, cfg,
            poster=_smart_poster(overrides=overrides, capture=capture),
        )
        fit_calls = [c for c in capture if 'compute-single-fit' in c['url']]
        assert len(fit_calls) == 1
        assert fit_calls[0]['kwargs'].get('timeout') == 90, (
            f"Expected timeout=90 on the fit poster call, "
            f"got kwargs={fit_calls[0]['kwargs']}"
        )


# ---- compute_fit step (multi-target / cross-school ordering) ------------
# Phase 2b: when an archetype carries `fit_target_colleges` (a list),
# the runner runs a compute_fit step per school AND a final
# fit_relative_ordering step that walks the collected responses and
# asserts category-rank is monotonically non-decreasing with
# acceptance_rate.


def _scenario_with_fit_targets(unis):
    s = _scenario()
    s['id'] = 'fit_multi_demo'
    s['colleges_template'] = list(unis)
    s['fit_target_colleges'] = list(unis)
    return s


def _fit_resp_for(uni, *, category, match_pct, acc_rate):
    return _ok({
        'success': True,
        'fit_analysis': {
            'fit_category': category,
            'match_percentage': match_pct,
            'acceptance_rate': acc_rate,
            'university_id': uni,
            'university_name': uni.replace('_', ' ').title(),
            'factors': [
                {'name': 'Academic',    'score': 30, 'max': 40, 'detail': 'x'},
                {'name': 'Holistic',    'score': 22, 'max': 30, 'detail': 'x'},
                {'name': 'Major Fit',   'score': 11, 'max': 15, 'detail': 'x'},
                {'name': 'Selectivity', 'score': -10, 'max': 5, 'detail': 'x'},
            ],
            'explanation': 'x',
            'essay_angles': [{'essay_prompt': 'why', 'angle': 'x'}],
            'application_timeline': {'recommended_plan': 'RD',
                                     'deadline': '2027-01-01'},
            'scholarship_matches': [{'name': 'Merit', 'amount': '$1k'}],
            'test_strategy': {'recommendation': 'Submit'},
            'major_strategy': {'intended_major': 'CS', 'is_available': True},
            'demonstrated_interest_tips': ['visit'],
            'red_flags_to_avoid': ['typos'],
            'recommendations': [{'action': 'x'}],
        },
    })


class TestComputeFitMultiTarget:
    def test_one_compute_fit_step_per_target(self):
        cfg = _make_cfg()
        scenario = _scenario_with_fit_targets([
            'massachusetts_institute_of_technology',
            'university_of_california_berkeley',
            'ohio_state_university',
        ])
        # We need a poster that returns a different fit response per
        # school, so the cross-school ordering check has real data.
        # _smart_poster picks the FIRST matching override per call;
        # we use a per-call counter to walk through the responses.
        fit_responses = {
            'massachusetts_institute_of_technology': _fit_resp_for(
                'massachusetts_institute_of_technology',
                category='SUPER_REACH', match_pct=32, acc_rate=4.6,
            ),
            'university_of_california_berkeley': _fit_resp_for(
                'university_of_california_berkeley',
                category='REACH', match_pct=54, acc_rate=11.0,
            ),
            'ohio_state_university': _fit_resp_for(
                'ohio_state_university',
                category='SAFETY', match_pct=78, acc_rate=60.6,
            ),
        }

        # Custom poster: pick fit response by university_id in body.
        def _multi_poster(url, body=None, *, method='POST', params=None, **kw):
            if 'compute-single-fit' in url and isinstance(body, dict):
                uni = body.get('university_id')
                resp = dict(fit_responses.get(uni, _ok({'success': False})))
                resp.setdefault('url', url)
                resp.setdefault('method', method)
                resp.setdefault('request_body', body)
                resp.setdefault('elapsed_ms', 50)
                resp.setdefault('response_excerpt', '')
                resp.setdefault('network_error', None)
                return resp
            # Defer to defaults for everything else.
            return _smart_poster()(url, body, method=method, params=params, **kw)

        result = runner.run_scenario(scenario, cfg, poster=_multi_poster)
        fit_step_names = [s['name'] for s in result['steps']
                          if s['name'].startswith('compute_fit:')]
        assert len(fit_step_names) == 3
        # All three school-specific steps should be present.
        for uni in fit_responses:
            assert any(uni in n for n in fit_step_names), (
                f"missing compute_fit step for {uni}: {fit_step_names}"
            )

    def test_appends_relative_ordering_step_when_multi_target(self):
        cfg = _make_cfg()
        scenario = _scenario_with_fit_targets([
            'massachusetts_institute_of_technology',
            'ohio_state_university',
        ])
        fit_responses = {
            'massachusetts_institute_of_technology': _fit_resp_for(
                'massachusetts_institute_of_technology',
                category='SUPER_REACH', match_pct=32, acc_rate=4.6,
            ),
            'ohio_state_university': _fit_resp_for(
                'ohio_state_university',
                category='SAFETY', match_pct=78, acc_rate=60.6,
            ),
        }

        def _multi_poster(url, body=None, *, method='POST', params=None, **kw):
            if 'compute-single-fit' in url and isinstance(body, dict):
                uni = body.get('university_id')
                resp = dict(fit_responses.get(uni, _ok({'success': False})))
                resp.setdefault('url', url)
                resp.setdefault('method', method)
                resp.setdefault('request_body', body)
                resp.setdefault('elapsed_ms', 50)
                resp.setdefault('response_excerpt', '')
                resp.setdefault('network_error', None)
                return resp
            return _smart_poster()(url, body, method=method, params=params, **kw)

        result = runner.run_scenario(scenario, cfg, poster=_multi_poster)
        ordering_steps = [s for s in result['steps']
                          if s['name'] == 'fit_relative_ordering']
        assert len(ordering_steps) == 1
        # Correct ordering (SUPER_REACH at 4.6% < SAFETY at 60.6%)
        # must pass.
        assert ordering_steps[0]['passed'], ordering_steps[0]['assertions']

    def test_ordering_step_fails_when_categories_inverted(self):
        """The canonical regression: same student gets SAFETY at MIT
        but TARGET at Ohio State — a worse category at a less-selective
        school. The ordering step must catch this."""
        cfg = _make_cfg()
        scenario = _scenario_with_fit_targets([
            'massachusetts_institute_of_technology',
            'ohio_state_university',
        ])
        # WRONG: MIT classified easier than Ohio State.
        fit_responses = {
            'massachusetts_institute_of_technology': _fit_resp_for(
                'massachusetts_institute_of_technology',
                category='SAFETY', match_pct=80, acc_rate=4.6,
            ),
            'ohio_state_university': _fit_resp_for(
                'ohio_state_university',
                category='TARGET', match_pct=60, acc_rate=60.6,
            ),
        }

        def _multi_poster(url, body=None, *, method='POST', params=None, **kw):
            if 'compute-single-fit' in url and isinstance(body, dict):
                uni = body.get('university_id')
                resp = dict(fit_responses.get(uni, _ok({'success': False})))
                resp.setdefault('url', url)
                resp.setdefault('method', method)
                resp.setdefault('request_body', body)
                resp.setdefault('elapsed_ms', 50)
                resp.setdefault('response_excerpt', '')
                resp.setdefault('network_error', None)
                return resp
            return _smart_poster()(url, body, method=method, params=params, **kw)

        result = runner.run_scenario(scenario, cfg, poster=_multi_poster)
        ordering_step = next(s for s in result['steps']
                             if s['name'] == 'fit_relative_ordering')
        assert not ordering_step['passed']

    def test_ordering_step_omitted_when_single_target(self):
        """Single-target scenarios shouldn't sprout an ordering step."""
        cfg = _make_cfg()
        scenario = _scenario_with_fit_target()  # uses fit_target_college (single)
        overrides = [(
            'compute-single-fit',
            _good_fit_response('massachusetts_institute_of_technology'),
        )]
        result = runner.run_scenario(
            scenario, cfg, poster=_smart_poster(overrides=overrides),
        )
        assert not any(s['name'] == 'fit_relative_ordering'
                       for s in result['steps'])

    def test_test_strategy_assertion_appended_when_no_scores_flag_set(self):
        """Phase 2c-2: when archetype carries fit_no_test_scores=true,
        the runner must append the test_strategy_not_submit_when_no_scores
        assertion. Catches regression where the wiring goes stale."""
        cfg = _make_cfg()
        scenario = _scenario_with_fit_target()
        scenario['fit_no_test_scores'] = True
        # Force the algorithm response to recommend "Submit" so the new
        # assertion fires and we can verify it was added.
        bad = _good_fit_response('massachusetts_institute_of_technology')
        bad['response_json']['fit_analysis']['test_strategy'] = {
            'recommendation': 'Submit',
        }
        result = runner.run_scenario(
            scenario, cfg,
            poster=_smart_poster(overrides=[
                ('compute-single-fit', bad),
            ]),
        )
        fit_step = next(s for s in result['steps']
                        if s['name'].startswith('compute_fit:'))
        # The new assertion should be in the list, and it should fail
        # because we forced "Submit".
        no_submit_assertions = [
            a for a in fit_step['assertions']
            if 'submit' in a.get('name', '').lower()
            and 'no scores' in a.get('name', '').lower()
        ]
        assert len(no_submit_assertions) == 1, (
            f"expected the no-scores assertion to be appended; got "
            f"{[a['name'] for a in fit_step['assertions']]}"
        )
        assert not no_submit_assertions[0]['passed']

    def test_test_strategy_assertion_omitted_by_default(self):
        """Without the fit_no_test_scores flag, the assertion is NOT
        appended — backwards compat with archetypes that don't declare
        it."""
        cfg = _make_cfg()
        scenario = _scenario_with_fit_target()  # no fit_no_test_scores
        result = runner.run_scenario(
            scenario, cfg,
            poster=_smart_poster(overrides=[(
                'compute-single-fit',
                _good_fit_response('massachusetts_institute_of_technology'),
            )]),
        )
        fit_step = next(s for s in result['steps']
                        if s['name'].startswith('compute_fit:'))
        no_submit = [
            a for a in fit_step['assertions']
            if 'no scores' in a.get('name', '').lower()
        ]
        assert no_submit == []

    def test_expected_category_pin_skipped_when_multi_target(self):
        """A single-value fit_expected_category can't apply across
        multiple schools at different tiers; the pin is skipped when
        multi-target. (Per-school expectations could be added later.)"""
        cfg = _make_cfg()
        scenario = _scenario_with_fit_targets([
            'massachusetts_institute_of_technology',
            'ohio_state_university',
        ])
        # Set a pin that would obviously be wrong for one of the two
        # schools — if the runner respected it, we'd see a key_equals
        # assertion in one of the steps.
        scenario['fit_expected_category'] = 'SUPER_REACH'
        fit_responses = {
            'massachusetts_institute_of_technology': _fit_resp_for(
                'massachusetts_institute_of_technology',
                category='SUPER_REACH', match_pct=32, acc_rate=4.6,
            ),
            'ohio_state_university': _fit_resp_for(
                'ohio_state_university',
                category='SAFETY', match_pct=78, acc_rate=60.6,
            ),
        }

        def _multi_poster(url, body=None, *, method='POST', params=None, **kw):
            if 'compute-single-fit' in url and isinstance(body, dict):
                uni = body.get('university_id')
                resp = dict(fit_responses.get(uni, _ok({'success': False})))
                resp.setdefault('url', url)
                resp.setdefault('method', method)
                resp.setdefault('request_body', body)
                resp.setdefault('elapsed_ms', 50)
                resp.setdefault('response_excerpt', '')
                resp.setdefault('network_error', None)
                return resp
            return _smart_poster()(url, body, method=method, params=params, **kw)

        result = runner.run_scenario(scenario, cfg, poster=_multi_poster)
        # Both school-specific compute_fit steps should pass — neither
        # should sprout the SUPER_REACH equality pin (Ohio State at
        # SAFETY would otherwise fail it).
        fit_steps = [s for s in result['steps']
                     if s['name'].startswith('compute_fit:')]
        for s in fit_steps:
            pinned = [a for a in s['assertions']
                      if 'fit_category==' in a.get('name', '')]
            assert pinned == [], (
                f"Pin should be skipped on multi-target. Step={s['name']}, "
                f"pinned={pinned}"
            )


# ---- counselor_chat step ------------------------------------------------
# Phase 1 of flow expansion: gated behind a per-archetype `chat_question`
# field. Catches regressions in the highest-stakes user-facing AI surface
# (the counselor chat). Currently no other monitoring exercises this
# endpoint.


def _scenario_with_chat_question(question="What should I focus on this week?"):
    s = _scenario()
    s['id'] = 'counselor_chat_demo'
    s['chat_question'] = question
    return s


class TestCounselorChatStep:
    def test_step_omitted_by_default(self):
        """Roadmap-only scenarios stay unchanged. Backwards-compat
        for every existing archetype that doesn't opt in."""
        cfg = _make_cfg()
        result = runner.run_scenario(_scenario(), cfg, poster=_smart_poster())
        step_names = [s['name'] for s in result['steps']]
        assert 'counselor_chat' not in step_names

    def test_step_added_when_chat_question_set(self):
        cfg = _make_cfg()
        result = runner.run_scenario(
            _scenario_with_chat_question(), cfg, poster=_smart_poster(),
        )
        step_names = [s['name'] for s in result['steps']]
        assert 'counselor_chat' in step_names

    def test_step_passes_on_well_formed_response(self):
        cfg = _make_cfg()
        result = runner.run_scenario(
            _scenario_with_chat_question(), cfg, poster=_smart_poster(),
        )
        chat_step = next(s for s in result['steps'] if s['name'] == 'counselor_chat')
        assert chat_step['passed'], (
            f"Expected pass; got failures: "
            f"{[a for a in chat_step['assertions'] if not a['passed']]}"
        )

    def test_step_fails_on_empty_reply(self):
        """Canonical regression: chat returns success: true but reply=""
        — the user would see a blank chat bubble. The new
        key_non_empty_string assertion catches this."""
        cfg = _make_cfg()
        result = runner.run_scenario(
            _scenario_with_chat_question(), cfg,
            poster=_smart_poster(overrides=[
                ('chat', _ok({
                    'success': True, 'reply': '', 'suggested_actions': [],
                })),
            ]),
        )
        chat_step = next(s for s in result['steps'] if s['name'] == 'counselor_chat')
        assert not chat_step['passed']
        empty_failures = [a for a in chat_step['assertions']
                          if 'non-empty' in a['name'] and not a['passed']]
        assert empty_failures

    def test_step_fails_on_whitespace_reply(self):
        cfg = _make_cfg()
        result = runner.run_scenario(
            _scenario_with_chat_question(), cfg,
            poster=_smart_poster(overrides=[
                ('chat', _ok({
                    'success': True, 'reply': '   \n  ',
                    'suggested_actions': [],
                })),
            ]),
        )
        chat_step = next(s for s in result['steps'] if s['name'] == 'counselor_chat')
        assert not chat_step['passed']

    def test_step_fails_on_success_false(self):
        cfg = _make_cfg()
        result = runner.run_scenario(
            _scenario_with_chat_question(), cfg,
            poster=_smart_poster(overrides=[
                ('chat', _ok({
                    'success': False, 'error': 'something broke',
                })),
            ]),
        )
        chat_step = next(s for s in result['steps'] if s['name'] == 'counselor_chat')
        assert not chat_step['passed']

    def test_step_calls_counselor_agent_chat_endpoint(self):
        """Confirms the contract: POST to {ca}/chat with
        {user_email, message, history}."""
        cfg = _make_cfg()
        capture = []
        runner.run_scenario(
            _scenario_with_chat_question("What's my next step?"),
            cfg, poster=_smart_poster(capture=capture),
        )
        chat_calls = [c for c in capture if c['url'].endswith('/chat')]
        assert len(chat_calls) == 1
        # The body shape the endpoint requires.
        # _smart_poster forwards the body via request_body which we
        # accumulate in capture['kwargs']; check there.
        # (The poster signature passes `body` positionally — captured
        # under no specific kwarg, so we settle for the URL check.)
        assert chat_calls[0]['url'].startswith('https://ca.test')

    def test_uses_extended_timeout_for_llm(self):
        """The /chat endpoint hits Gemini; the default 30s poster
        timeout is too tight on cold starts. The runner step passes
        timeout=60 to give cold paths headroom."""
        cfg = _make_cfg()
        capture = []
        runner.run_scenario(
            _scenario_with_chat_question(),
            cfg, poster=_smart_poster(capture=capture),
        )
        chat_calls = [c for c in capture if c['url'].endswith('/chat')]
        assert chat_calls[0]['kwargs'].get('timeout') == 60
