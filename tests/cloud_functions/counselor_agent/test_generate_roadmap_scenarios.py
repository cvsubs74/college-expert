"""
Integration tests for the full /roadmap response pipeline.

These exercise generate_roadmap() end-to-end with controlled fixtures —
profile, college list, and current date — to verify that students at
every grade × semester combination get the right roadmap, and that the
resolver edges (caller-wins, caller-grade-only, default) all work.

These complement test_planner.py (which unit-tests resolve_template_key,
translate_*, etc. in isolation). Here we drive the function the API
endpoint calls and assert on the response shape clients actually see.

Mocking strategy:
  - planner.get_student_profile     → controlled profile dict
  - planner.get_college_context     → controlled context (matches the
                                       output shape of the real function)
  - planner.datetime.now()          → fixed "today" so resolver paths
                                       produce deterministic templates

Nothing else is mocked — resolve_template_key, translate_task, the
TEMPLATES dict, and the response builder all run for real.
"""

from contextlib import contextmanager
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

import planner
from planner import generate_roadmap


# ---------------------------------------------------------------------------
# Fixtures + helpers
# ---------------------------------------------------------------------------


@contextmanager
def fixed_today(year, month, day):
    """Freeze datetime.now() inside planner so resolver math is deterministic."""
    fake_now = datetime(year, month, day, 12, 0, 0)
    with patch.object(planner, 'datetime') as mock_dt:
        mock_dt.now.return_value = fake_now
        yield


def make_request(**body):
    """Lightweight Flask-request stand-in for generate_roadmap's get_json()."""
    req = MagicMock()
    req.get_json.return_value = body
    return req


def empty_college_context():
    """Matches get_college_context() shape when the user has no colleges."""
    return {
        'colleges': [],
        'uc_schools': [],
        'has_early_decision': False,
        'has_early_action': False,
    }


def college_context(*colleges, uc_schools=None, has_ed=False, has_ea=False):
    """Build a college context dict from a positional list of college dicts.

    Each college needs at minimum {id, name, is_uc, deadline, deadline_type}.
    Helper fills sensible defaults so call sites stay readable.
    """
    cleaned = []
    for c in colleges:
        cleaned.append({
            'id': c['id'],
            'name': c.get('name', c['id']),
            'deadline': c.get('deadline', '2027-01-05'),
            'deadline_type': c.get('deadline_type', 'Regular Decision'),
            'is_uc': c.get('is_uc', False),
        })
    return {
        'colleges': cleaned,
        'uc_schools': sorted(uc_schools or []),
        'has_early_decision': has_ed,
        'has_early_action': has_ea,
    }


def stub_student(*, profile=None, context=None):
    """
    Patch planner's profile + college-context lookups for one test.
    Returns a context manager applying both patches.
    """
    return _StubContext(profile=profile, context=context)


class _StubContext:
    def __init__(self, profile, context):
        self.profile = profile
        self.context = context if context is not None else empty_college_context()
        self._patches = []

    def __enter__(self):
        self._patches = [
            patch.object(planner, 'get_student_profile', return_value=self.profile),
            patch.object(planner, 'get_college_context', return_value=self.context),
        ]
        for p in self._patches:
            p.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        for p in self._patches:
            p.stop()


# ---------------------------------------------------------------------------
# Scenario tests — one per grade × semester combo (profile-driven path)
# ---------------------------------------------------------------------------


class TestProfileDrivenScenarios:
    """
    Each test models a real student onboarding at a specific point in time.
    The profile carries graduation_year; today's date determines semester;
    the resolver picks the template; we assert on the visible result.
    """

    def test_freshman_fall(self):
        # Sept 2026, graduating 2030 → 4 years out, fall semester → freshman_fall
        with fixed_today(2026, 9, 15), stub_student(
            profile={'graduation_year': 2030},
            context=empty_college_context(),
        ):
            result = generate_roadmap(make_request(user_email='ninth@example.com'))

        assert result['success'] is True
        assert result['metadata']['template_used'] == 'freshman_fall'
        assert result['metadata']['grade_used'] == 'freshman'
        assert result['metadata']['semester_used'] == 'fall'
        assert result['metadata']['resolution_source'] == 'profile'
        assert result['metadata']['personalized'] is False
        assert result['metadata']['colleges_count'] == 0
        # Roadmap structure should be intact even with no college list
        assert isinstance(result['roadmap']['phases'], list)
        assert len(result['roadmap']['phases']) > 0

    def test_freshman_spring(self):
        # March 2026, graduating 2029 → 3 years out, spring → freshman_spring
        with fixed_today(2026, 3, 1), stub_student(
            profile={'graduation_year': 2029},
        ):
            result = generate_roadmap(make_request(user_email='x@y.z'))
        assert result['metadata']['template_used'] == 'freshman_spring'
        assert result['metadata']['resolution_source'] == 'profile'

    def test_sophomore_fall(self):
        # Sept 2026, graduating 2029 → fall sophomore year
        with fixed_today(2026, 9, 1), stub_student(profile={'graduation_year': 2029}):
            result = generate_roadmap(make_request(user_email='x@y.z'))
        assert result['metadata']['template_used'] == 'sophomore_fall'
        assert result['metadata']['resolution_source'] == 'profile'

    def test_sophomore_spring(self):
        with fixed_today(2026, 3, 1), stub_student(profile={'graduation_year': 2028}):
            result = generate_roadmap(make_request(user_email='x@y.z'))
        assert result['metadata']['template_used'] == 'sophomore_spring'

    def test_junior_fall(self):
        with fixed_today(2026, 9, 1), stub_student(profile={'graduation_year': 2028}):
            result = generate_roadmap(make_request(user_email='x@y.z'))
        assert result['metadata']['template_used'] == 'junior_fall'

    def test_junior_spring(self):
        # Apr 2026, graduating 2027 → spring semester of junior year
        with fixed_today(2026, 4, 1), stub_student(profile={'graduation_year': 2027}):
            result = generate_roadmap(make_request(user_email='x@y.z'))
        assert result['metadata']['template_used'] == 'junior_spring'

    def test_junior_summer_rising_senior(self):
        # July 2026, grad 2027 → critical summer-before-senior phase. Has its
        # own dedicated template (the only summer template that exists).
        with fixed_today(2026, 7, 15), stub_student(profile={'graduation_year': 2027}):
            result = generate_roadmap(make_request(user_email='x@y.z'))
        assert result['metadata']['template_used'] == 'junior_summer'
        assert result['metadata']['semester_used'] == 'summer'

    def test_senior_fall(self):
        # Oct 2026, grad 2027 → senior fall — application crunch time
        with fixed_today(2026, 10, 15), stub_student(profile={'graduation_year': 2027}):
            result = generate_roadmap(make_request(user_email='x@y.z'))
        assert result['metadata']['template_used'] == 'senior_fall'

    def test_senior_spring(self):
        # Apr 2026, grad 2026 → spring of senior year, decisions arriving
        with fixed_today(2026, 4, 1), stub_student(profile={'graduation_year': 2026}):
            result = generate_roadmap(make_request(user_email='x@y.z'))
        assert result['metadata']['template_used'] == 'senior_spring'


# ---------------------------------------------------------------------------
# Edge-case grade computations
# ---------------------------------------------------------------------------


class TestGradeEdges:
    def test_already_graduated_clamps_to_senior_spring(self):
        # Profile says grad 2024, today is 2026 — student has already graduated.
        # We don't have a "post-grad" template; resolver should clamp to senior
        # and pick the appropriate semester template.
        with fixed_today(2026, 4, 1), stub_student(profile={'graduation_year': 2024}):
            result = generate_roadmap(make_request(user_email='x@y.z'))
        assert result['metadata']['grade_used'] == 'senior'

    def test_far_future_graduation_clamps_to_freshman(self):
        # 6 years out — student is in middle school but signed up early.
        # Resolver caps the grade at freshman.
        with fixed_today(2026, 9, 1), stub_student(profile={'graduation_year': 2032}):
            result = generate_roadmap(make_request(user_email='x@y.z'))
        assert result['metadata']['grade_used'] == 'freshman'

    def test_sophomore_summer_falls_back_to_sophomore_spring(self):
        # No sophomore_summer template — resolver's fallback table maps it to
        # sophomore_spring so the user still gets a coherent roadmap.
        with fixed_today(2026, 7, 15), stub_student(profile={'graduation_year': 2028}):
            result = generate_roadmap(make_request(user_email='x@y.z'))
        # sophomore_summer would have been the literal pick, but it falls back.
        assert result['metadata']['template_used'] == 'sophomore_spring'


# ---------------------------------------------------------------------------
# Resolver-source coverage (caller / caller-grade-only / default)
# ---------------------------------------------------------------------------


class TestResolverSources:
    def test_caller_wins_when_both_grade_and_semester_provided(self):
        # Profile says senior, caller insists on junior+spring → caller wins.
        # Locks in the contract: a frontend that computes its own (grade, sem)
        # gets honored.
        with fixed_today(2026, 9, 1), stub_student(
            profile={'graduation_year': 2027},
        ):
            result = generate_roadmap(make_request(
                user_email='x@y.z',
                grade_level='11th Grade',
                semester='spring',
            ))
        assert result['metadata']['template_used'] == 'junior_spring'
        assert result['metadata']['resolution_source'] == 'caller'

    def test_caller_grade_only_when_no_profile_grade(self):
        # No profile → caller's grade hint is used with computed semester.
        # source='caller-grade-only' (distinct from 'caller' which requires both).
        with fixed_today(2026, 9, 1), stub_student(profile=None):
            result = generate_roadmap(make_request(
                user_email='x@y.z',
                grade_level='12th Grade',
                # no semester
            ))
        assert result['metadata']['template_used'] == 'senior_fall'
        assert result['metadata']['resolution_source'] == 'caller-grade-only'

    def test_default_when_nothing_resolves(self):
        # No profile, no caller hints → conservative default of senior_fall.
        with fixed_today(2026, 9, 1), stub_student(profile=None):
            result = generate_roadmap(make_request(user_email='x@y.z'))
        assert result['metadata']['template_used'] == 'senior_fall'
        assert result['metadata']['resolution_source'] == 'default'

    def test_only_semester_provided_overrides_computed_semester(self):
        # Asymmetry worth documenting: caller's `semester` IS used even
        # without a `grade_level`, but caller's `grade_level` ALONE is
        # ignored (per the safety constraint that protects against the
        # legacy frontend's hardcoded '11th Grade'). Concretely: today
        # is Sept 2026 (computed semester='fall'), but caller says
        # 'spring' — the resolver uses 'spring' even though grade comes
        # from the profile. Source is 'profile' because the GRADE came
        # from there.
        with fixed_today(2026, 9, 1), stub_student(profile={'graduation_year': 2027}):
            result = generate_roadmap(make_request(
                user_email='x@y.z',
                semester='spring',
            ))
        assert result['metadata']['resolution_source'] == 'profile'
        # Caller's spring + profile-derived senior → senior_spring (NOT
        # senior_fall as the date alone would suggest).
        assert result['metadata']['template_used'] == 'senior_spring'


# ---------------------------------------------------------------------------
# College-context translation — UC grouping + per-school RD tasks +
# verification, all stamped with artifact_ref where applicable.
# ---------------------------------------------------------------------------


class TestCollegeContextTranslation:
    """
    senior_fall is the template that exercises every translate_* path:
      - "Submit RD Applications" → per-school + UC group submission tasks
      - "Complete Essays/Supplements" → per-school + UC PIQs
      - "Verify Materials Received" → tab-level
    These tests use the senior_fall template and a richly populated college
    list so we can assert on each translation outcome.
    """

    SENIOR_FALL_PROFILE = {'graduation_year': 2027}
    SENIOR_FALL_TODAY = (2026, 10, 15)

    def _senior_fall_with_colleges(self, ctx):
        with fixed_today(*self.SENIOR_FALL_TODAY), stub_student(
            profile=self.SENIOR_FALL_PROFILE,
            context=ctx,
        ):
            return generate_roadmap(make_request(user_email='x@y.z'))

    def test_metadata_reflects_personalization(self):
        result = self._senior_fall_with_colleges(college_context(
            {'id': 'mit', 'name': 'MIT', 'is_uc': False, 'deadline': '2027-01-05'},
            {'id': 'stanford', 'name': 'Stanford', 'is_uc': False, 'deadline': '2026-11-01'},
        ))
        assert result['metadata']['template_used'] == 'senior_fall'
        assert result['metadata']['personalized'] is True
        assert result['metadata']['colleges_count'] == 2

    def test_per_school_rd_submission_tasks_with_artifact_ref(self):
        result = self._senior_fall_with_colleges(college_context(
            {'id': 'mit', 'name': 'MIT', 'is_uc': False, 'deadline': '2027-01-05'},
            {'id': 'stanford', 'name': 'Stanford', 'is_uc': False, 'deadline': '2027-01-05'},
        ))
        all_tasks = [t for phase in result['roadmap']['phases'] for t in phase['tasks']]
        # Look for tasks that came out of translate_rd_submission — they have
        # 'Submit ' in the title and an artifact_ref tying them to a college.
        submit_tasks = [t for t in all_tasks if 'Submit MIT' in t.get('title', '')]
        assert submit_tasks, 'expected a "Submit MIT" task from RD translation'
        assert submit_tasks[0]['artifact_ref']['type'] == 'college'
        assert submit_tasks[0]['artifact_ref']['university_id'] == 'mit'
        assert submit_tasks[0]['artifact_ref']['deep_link'] == '/roadmap?tab=colleges&school=mit'

    def test_uc_group_task_combines_school_names_in_label(self):
        result = self._senior_fall_with_colleges(college_context(
            {'id': 'university_of_california_berkeley', 'name': 'UC Berkeley', 'is_uc': True, 'deadline': '2026-11-30'},
            {'id': 'university_of_california_los_angeles', 'name': 'UCLA', 'is_uc': True, 'deadline': '2026-11-30'},
            {'id': 'university_of_california_san_diego', 'name': 'UCSD', 'is_uc': True, 'deadline': '2026-11-30'},
            uc_schools=['UC Berkeley', 'UCLA', 'UCSD'],
        ))
        all_tasks = [t for phase in result['roadmap']['phases'] for t in phase['tasks']]
        uc_task = next(
            (t for t in all_tasks if 'UC Application' in t.get('title', '')),
            None,
        )
        assert uc_task is not None, 'expected a UC group submission task'
        # All three school names are reflected in the badge label, not just
        # the anchor school.
        assert uc_task['artifact_ref']['label'] == 'Open UC Berkeley, UCLA, UCSD'
        assert uc_task['artifact_ref']['type'] == 'college'
        # The university_id anchors at one of the UC schools (cheap-pick of
        # the first; the label override carries the full list).
        assert 'university_of_california' in uc_task['artifact_ref']['university_id']

    def test_essay_translation_produces_uc_piqs_and_per_school_supplements(self):
        result = self._senior_fall_with_colleges(college_context(
            {'id': 'university_of_california_berkeley', 'name': 'UC Berkeley', 'is_uc': True},
            {'id': 'mit', 'name': 'MIT', 'is_uc': False},
            uc_schools=['UC Berkeley'],
        ))
        all_tasks = [t for phase in result['roadmap']['phases'] for t in phase['tasks']]
        uc_piq_task = next((t for t in all_tasks if 'UC PIQs' in t.get('title', '')), None)
        mit_essays_task = next(
            (t for t in all_tasks if 'MIT' in t.get('title', '') and 'supplemental' in t.get('title', '').lower()),
            None,
        )
        assert uc_piq_task is not None
        # UC PIQs go to the Essays tab (no canonical per-essay row).
        assert uc_piq_task['artifact_ref']['type'] == 'tab'
        assert uc_piq_task['artifact_ref']['tab'] == 'essays'

        assert mit_essays_task is not None
        assert mit_essays_task['artifact_ref']['type'] == 'college'
        assert mit_essays_task['artifact_ref']['university_id'] == 'mit'

    def test_verify_materials_task_routes_to_colleges_tab(self):
        result = self._senior_fall_with_colleges(college_context(
            {'id': 'mit', 'name': 'MIT', 'is_uc': False},
            {'id': 'stanford', 'name': 'Stanford', 'is_uc': False},
        ))
        all_tasks = [t for phase in result['roadmap']['phases'] for t in phase['tasks']]
        verify_task = next((t for t in all_tasks if 'Verify' in t.get('title', '')), None)
        assert verify_task is not None
        assert verify_task['artifact_ref']['type'] == 'tab'
        assert verify_task['artifact_ref']['tab'] == 'colleges'

    def test_overdue_marker_prepended_when_deadline_in_past(self):
        # If the student missed a deadline (or the date is just in the past),
        # the RD submission task picks up an OVERDUE marker so it can be
        # surfaced prominently. We verify the flag travels through.
        result = self._senior_fall_with_colleges(college_context(
            {'id': 'mit', 'name': 'MIT', 'is_uc': False, 'deadline': '2020-01-01'},
        ))
        all_tasks = [t for phase in result['roadmap']['phases'] for t in phase['tasks']]
        mit_task = next((t for t in all_tasks if 'MIT' in t.get('title', '') and 'Submit' in t.get('title', '')), None)
        assert mit_task is not None
        assert mit_task.get('is_overdue') is True
        assert mit_task['title'].startswith('⚠️ OVERDUE')

    def test_template_isolation_across_calls(self):
        # Regression test for a real bug: generate_roadmap used a SHALLOW
        # copy of the template, so translating phase['tasks'] mutated the
        # global TEMPLATES dict. Subsequent calls (for different users)
        # would see the previous caller's translated tasks. Now uses
        # deepcopy; this test pins that down.
        ctx_a = college_context(
            {'id': 'mit', 'name': 'MIT', 'is_uc': False, 'deadline': '2027-01-05'},
        )
        ctx_b = college_context(
            {'id': 'stanford', 'name': 'Stanford', 'is_uc': False, 'deadline': '2027-01-05'},
        )
        # First call: only MIT in the list.
        with fixed_today(*self.SENIOR_FALL_TODAY), stub_student(
            profile=self.SENIOR_FALL_PROFILE, context=ctx_a,
        ):
            result_a = generate_roadmap(make_request(user_email='a@a.a'))

        # Second call: a different user with only Stanford.
        with fixed_today(*self.SENIOR_FALL_TODAY), stub_student(
            profile=self.SENIOR_FALL_PROFILE, context=ctx_b,
        ):
            result_b = generate_roadmap(make_request(user_email='b@b.b'))

        a_tasks = [t['title'] for phase in result_a['roadmap']['phases'] for t in phase['tasks']]
        b_tasks = [t['title'] for phase in result_b['roadmap']['phases'] for t in phase['tasks']]

        # User A's tasks reference MIT, NOT Stanford.
        assert any('MIT' in t for t in a_tasks)
        assert not any('Stanford' in t for t in a_tasks)
        # User B's tasks reference Stanford, NOT MIT — proves the template
        # wasn't corrupted by user A's call.
        assert any('Stanford' in t for t in b_tasks)
        assert not any('MIT' in t for t in b_tasks)

    def test_empty_college_list_keeps_template_tasks_generic(self):
        # No colleges → translate_task returns the original template task
        # unchanged. Sanity-check that the senior_fall template's "Submit RD
        # Applications" stays generic when there's nothing to translate it to.
        result = self._senior_fall_with_colleges(empty_college_context())
        all_tasks = [t for phase in result['roadmap']['phases'] for t in phase['tasks']]
        # Generic RD submission task title (whatever it is in the template)
        # should still be present and SHOULD NOT have an artifact_ref since
        # we never translated.
        rd_tasks = [t for t in all_tasks if 'Submit' in t.get('title', '') and 'RD' in t.get('title', '').upper()]
        if rd_tasks:
            # Untranslated task — no artifact_ref expected (template tasks don't carry one).
            assert 'artifact_ref' not in rd_tasks[0]


# ---------------------------------------------------------------------------
# Response shape sanity (every scenario should produce a usable response)
# ---------------------------------------------------------------------------


class TestResponseShape:
    @pytest.mark.parametrize('grad_year,today,expected_template', [
        (2030, (2026, 9, 1), 'freshman_fall'),
        (2027, (2026, 4, 1), 'junior_spring'),
        (2027, (2026, 10, 15), 'senior_fall'),
        (2026, (2026, 4, 1), 'senior_spring'),
    ])
    def test_response_keys_always_present(self, grad_year, today, expected_template):
        with fixed_today(*today), stub_student(profile={'graduation_year': grad_year}):
            result = generate_roadmap(make_request(user_email='x@y.z'))

        # Top-level contract
        assert 'success' in result
        assert 'roadmap' in result
        assert 'metadata' in result

        # Metadata contract — every field a frontend might read
        meta = result['metadata']
        for key in ('template_used', 'grade_used', 'semester_used',
                    'resolution_source', 'colleges_count', 'personalized', 'last_updated'):
            assert key in meta, f"metadata.{key} missing"

        # Phases are always a list with at least one entry
        assert isinstance(result['roadmap']['phases'], list)
        assert len(result['roadmap']['phases']) >= 1

        # Each phase has the documented structure
        for phase in result['roadmap']['phases']:
            assert 'id' in phase
            assert 'name' in phase
            assert isinstance(phase['tasks'], list)

        # And the template was the one we expected — anchors the parametrize
        assert meta['template_used'] == expected_template
