"""
Unit tests for cloud_functions/counselor_agent/planner.py.

Covers the pure logic that drives the Roadmap surface:
  - semester_from_date / grade resolution
  - resolve_template_key with all four source paths
  - artifact_ref helpers (_college_artifact_ref, _tab_artifact_ref)
  - translate_rd_submission / translate_essay_tasks / translate_verification

These functions are deterministic and have no side effects, so the tests
don't mock anything — they exercise the real module against canned input.
"""

from datetime import datetime

import pytest

import planner as p


# ---------------------------------------------------------------------------
# semester_from_date — Aug-Dec=fall, Jan-May=spring, Jun-Jul=summer
# ---------------------------------------------------------------------------

class TestSemesterFromDate:
    @pytest.mark.parametrize('month,expected', [
        (1, 'spring'), (5, 'spring'),                          # spring boundaries
        (6, 'summer'), (7, 'summer'),                          # summer boundaries
        (8, 'fall'), (12, 'fall'),                             # fall boundaries
        (3, 'spring'), (9, 'fall'), (7, 'summer'),             # interior days
    ])
    def test_each_month(self, month, expected):
        assert p.semester_from_date(datetime(2026, month, 15)) == expected

    def test_uses_today_when_no_arg(self):
        # Just confirm it doesn't crash and returns a known semester string.
        assert p.semester_from_date() in p.VALID_SEMESTERS


# ---------------------------------------------------------------------------
# grade_name_from_grade_level — string → grade name
# ---------------------------------------------------------------------------

class TestGradeNameFromGradeLevel:
    @pytest.mark.parametrize('label,expected', [
        ('9th Grade', 'freshman'),
        ('10th Grade', 'sophomore'),
        ('11th Grade', 'junior'),
        ('12th Grade', 'senior'),
        ('Junior', 'junior'),
        ('SENIOR', 'senior'),
        ('sophomore year', 'sophomore'),
        ('Freshman (just started!)', 'freshman'),
    ])
    def test_recognized_strings(self, label, expected):
        assert p.grade_name_from_grade_level(label) == expected

    @pytest.mark.parametrize('label', ['', None, 'gap year', 'transfer', 'graduate'])
    def test_unrecognized_returns_none(self, label):
        assert p.grade_name_from_grade_level(label) is None

    def test_non_string_returns_none(self):
        assert p.grade_name_from_grade_level(11) is None
        assert p.grade_name_from_grade_level(['11th']) is None


# ---------------------------------------------------------------------------
# grade_name_from_graduation_year — reproduces the legacy mapping used pre-PR-5.
# Test cases lifted directly from the comment block in planner.py so we lock
# in behavior bug-for-bug.
# ---------------------------------------------------------------------------

class TestGradeNameFromGraduationYear:
    @pytest.mark.parametrize('grad,today,expected', [
        # Senior (graduating this year)
        (2026, datetime(2026, 4, 1), 'senior'),
        (2026, datetime(2026, 1, 15), 'senior'),
        # Senior fall (graduating next year, fall semester)
        (2027, datetime(2026, 8, 15), 'senior'),
        (2027, datetime(2026, 12, 1), 'senior'),
        # Junior summer (rising senior — between junior spring and senior fall)
        (2027, datetime(2026, 7, 15), 'junior'),
        # Junior spring
        (2027, datetime(2026, 4, 1), 'junior'),
        # Junior fall (graduating in 2 years, fall)
        (2028, datetime(2026, 9, 1), 'junior'),
        # Sophomore spring
        (2028, datetime(2026, 3, 1), 'sophomore'),
        # Sophomore fall (graduating in 3 years, fall)
        (2029, datetime(2026, 9, 1), 'sophomore'),
        # Freshman spring (graduating in 3 years, spring)
        (2029, datetime(2026, 3, 1), 'freshman'),
        # Freshman fall (graduating in 4+ years)
        (2030, datetime(2026, 9, 1), 'freshman'),
        (2031, datetime(2026, 9, 1), 'freshman'),
        # Already graduated → senior (we don't go past senior)
        (2024, datetime(2026, 9, 1), 'senior'),
    ])
    def test_year_to_grade_mapping(self, grad, today, expected):
        assert p.grade_name_from_graduation_year(grad, now=today) == expected


# ---------------------------------------------------------------------------
# _compose_template_key — string composition + summer-fallback table
# ---------------------------------------------------------------------------

class TestComposeTemplateKey:
    @pytest.mark.parametrize('grade,semester,expected', [
        ('freshman', 'fall', 'freshman_fall'),
        ('freshman', 'spring', 'freshman_spring'),
        ('sophomore', 'fall', 'sophomore_fall'),
        ('sophomore', 'spring', 'sophomore_spring'),
        ('junior', 'fall', 'junior_fall'),
        ('junior', 'spring', 'junior_spring'),
        ('junior', 'summer', 'junior_summer'),     # has its own template
        ('senior', 'fall', 'senior_fall'),
        ('senior', 'spring', 'senior_spring'),
    ])
    def test_direct_template_match(self, grade, semester, expected):
        assert p._compose_template_key(grade, semester) == expected

    @pytest.mark.parametrize('grade,expected_fallback', [
        ('freshman', 'freshman_spring'),
        ('sophomore', 'sophomore_spring'),
        ('senior', 'senior_spring'),
    ])
    def test_summer_falls_back_to_spring_when_no_summer_template(self, grade, expected_fallback):
        assert p._compose_template_key(grade, 'summer') == expected_fallback

    def test_unknown_grade_returns_none(self):
        assert p._compose_template_key('graduate', 'fall') is None
        assert p._compose_template_key('', 'fall') is None


# ---------------------------------------------------------------------------
# resolve_template_key — orchestrates the full caller→profile→default chain
# ---------------------------------------------------------------------------

class TestResolveTemplateKey:
    def test_caller_wins_when_both_grade_and_semester_provided(self):
        # Profile says freshman; caller says junior+spring → caller wins.
        key, source = p.resolve_template_key(
            grade_level='11th Grade', semester='spring',
            profile={'graduation_year': 2030},
            now=datetime(2026, 9, 1),
        )
        assert (key, source) == ('junior_spring', 'caller')

    def test_grade_only_falls_through_to_profile(self):
        # Caller's grade alone is treated as "not enough" — profile takes over.
        # Today's frontend (pre-PR-7) sent only grade_level='11th Grade';
        # this test locks in that we don't accidentally start respecting it.
        key, source = p.resolve_template_key(
            grade_level='11th Grade', semester=None,
            profile={'graduation_year': 2030},
            now=datetime(2026, 9, 1),
        )
        assert source == 'profile'
        assert key == 'freshman_fall'

    def test_invalid_semester_treated_as_missing(self):
        # 'winter' isn't in VALID_SEMESTERS → falls through to profile path.
        key, source = p.resolve_template_key(
            grade_level='11th Grade', semester='winter',
            profile={'graduation_year': 2027},
            now=datetime(2026, 9, 1),
        )
        assert source == 'profile'
        assert key == 'senior_fall'

    def test_no_caller_no_profile_returns_default(self):
        key, source = p.resolve_template_key(grade_level=None, semester=None, profile=None)
        assert (key, source) == ('senior_fall', 'default')

    def test_caller_grade_only_with_no_profile(self):
        # If the user has nothing in their profile, fall back to the caller's
        # grade hint plus a computed semester.
        key, source = p.resolve_template_key(
            grade_level='12th Grade', semester=None,
            profile=None, now=datetime(2026, 9, 1),
        )
        assert (key, source) == ('senior_fall', 'caller-grade-only')

    def test_malformed_graduation_year_falls_to_default(self):
        key, source = p.resolve_template_key(
            grade_level=None, semester=None,
            profile={'graduation_year': 'not a year'},
        )
        assert source == 'default'


# ---------------------------------------------------------------------------
# Artifact ref helpers
# ---------------------------------------------------------------------------

class TestArtifactRefHelpers:
    def test_college_ref_basic(self):
        ref = p._college_artifact_ref({'id': 'mit', 'name': 'MIT'})
        assert ref == {
            'type': 'college',
            'university_id': 'mit',
            'label': 'Open MIT',
            'deep_link': '/roadmap?tab=colleges&school=mit',
        }

    def test_college_ref_falls_back_to_id_when_no_name(self):
        ref = p._college_artifact_ref({'id': 'random_school'})
        assert ref['label'] == 'Open random_school'

    @pytest.mark.parametrize('bad', [None, {}, {'name': 'no-id-college'}])
    def test_college_ref_returns_none_on_data_quality_issues(self, bad):
        assert p._college_artifact_ref(bad) is None

    def test_tab_ref_shape(self):
        ref = p._tab_artifact_ref('essays', 'Open Essays')
        assert ref == {
            'type': 'tab',
            'tab': 'essays',
            'label': 'Open Essays',
            'deep_link': '/roadmap?tab=essays',
        }


# ---------------------------------------------------------------------------
# translate_* — convert generic template tasks to college-specific ones,
# stamped with artifact_ref where appropriate.
# ---------------------------------------------------------------------------

class TestTranslateRdSubmission:
    GENERIC = {'id': 'task_submit_rd', 'title': 'Submit RD Applications', 'type': 'deadline'}

    def test_uc_group_plus_individual_non_uc(self, make_college_context):
        ctx = make_college_context(
            colleges=[
                {'id': 'university_of_california_berkeley', 'name': 'UC Berkeley',
                 'deadline': '2026-11-30', 'is_uc': True},
                {'id': 'university_of_california_los_angeles', 'name': 'UCLA',
                 'deadline': '2026-11-30', 'is_uc': True},
                {'id': 'mit', 'name': 'MIT', 'deadline': '2027-01-05', 'is_uc': False},
            ],
            uc_schools=['UC Berkeley', 'UCLA'],
        )
        tasks = p.translate_rd_submission(self.GENERIC, ctx)
        assert len(tasks) == 2  # UC group + MIT

        uc_task = next(t for t in tasks if 'UC Application' in t['title'])
        assert uc_task['artifact_ref']['type'] == 'college'
        assert 'university_of_california' in uc_task['artifact_ref']['university_id']
        # Label overrides the per-school label for the group.
        assert uc_task['artifact_ref']['label'] == 'Open UC Berkeley, UCLA'

        mit_task = next(t for t in tasks if 'MIT' in t['title'])
        assert mit_task['artifact_ref']['university_id'] == 'mit'
        assert mit_task['artifact_ref']['deep_link'] == '/roadmap?tab=colleges&school=mit'

    def test_overdue_marker_on_past_deadline(self, make_college_context):
        ctx = make_college_context(colleges=[
            {'id': 'mit', 'name': 'MIT', 'deadline': '2020-01-01', 'is_uc': False},
        ])
        tasks = p.translate_rd_submission(self.GENERIC, ctx)
        assert tasks[0]['title'].startswith('⚠️ OVERDUE')
        assert tasks[0]['is_overdue'] is True

    def test_empty_context_returns_generic_task(self, make_college_context):
        ctx = make_college_context()
        assert p.translate_rd_submission(self.GENERIC, ctx) == [self.GENERIC]


class TestTranslateEssayTasks:
    GENERIC = {'id': 'task_essays', 'title': 'Complete Supplements', 'type': 'core'}

    def test_uc_piqs_get_tab_level_artifact(self, make_college_context):
        ctx = make_college_context(uc_schools=['UC Berkeley', 'UCLA'])
        tasks = p.translate_essay_tasks(self.GENERIC, ctx)
        uc_piq = next(t for t in tasks if 'UC PIQs' in t['title'])
        assert uc_piq['artifact_ref'] == {
            'type': 'tab',
            'tab': 'essays',
            'label': 'Open Essays',
            'deep_link': '/roadmap?tab=essays',
        }

    def test_per_school_supplements_get_college_artifact(self, make_college_context):
        ctx = make_college_context(colleges=[
            {'id': 'stanford', 'name': 'Stanford'},
            {'id': 'harvard', 'name': 'Harvard'},
        ])
        tasks = p.translate_essay_tasks(self.GENERIC, ctx)
        stanford_task = next(t for t in tasks if 'Stanford' in t['title'])
        assert stanford_task['artifact_ref']['university_id'] == 'stanford'
        assert stanford_task['artifact_ref']['type'] == 'college'

    def test_empty_context_returns_generic(self, make_college_context):
        ctx = make_college_context()
        assert p.translate_essay_tasks(self.GENERIC, ctx) == [self.GENERIC]


class TestTranslateVerification:
    GENERIC = {'id': 'verify', 'title': 'Verify Materials', 'type': 'core'}

    def test_returns_tab_level_artifact_for_colleges_tab(self, make_college_context):
        ctx = make_college_context(colleges=[
            {'id': 'mit', 'name': 'MIT'},
            {'id': 'stanford', 'name': 'Stanford'},
        ])
        tasks = p.translate_verification(self.GENERIC, ctx)
        assert len(tasks) == 1
        assert tasks[0]['artifact_ref']['type'] == 'tab'
        assert tasks[0]['artifact_ref']['tab'] == 'colleges'
        assert tasks[0]['title'].startswith('Verify')
        assert 'MIT' in tasks[0]['title'] and 'Stanford' in tasks[0]['title']

    def test_truncates_school_list_after_five(self, make_college_context):
        many = [{'id': f'school_{i}', 'name': f'School{i}'} for i in range(7)]
        ctx = make_college_context(colleges=many)
        tasks = p.translate_verification(self.GENERIC, ctx)
        assert 'and more' in tasks[0]['title']
        assert '(7 colleges)' in tasks[0]['title']

    def test_empty_context_returns_generic(self, make_college_context):
        ctx = make_college_context()
        assert p.translate_verification(self.GENERIC, ctx) == [self.GENERIC]


# ---------------------------------------------------------------------------
# translate_task — dispatcher that picks one of the translate_* functions
# based on the generic task's title.
# ---------------------------------------------------------------------------

class TestTranslateTaskDispatch:
    def test_rd_submission_dispatched(self, make_college_context):
        ctx = make_college_context(colleges=[{'id': 'mit', 'name': 'MIT'}])
        out = p.translate_task({'title': 'Submit RD Applications'}, ctx)
        assert any('MIT' in t['title'] for t in out)

    def test_essay_dispatched(self, make_college_context):
        ctx = make_college_context(colleges=[{'id': 'stanford', 'name': 'Stanford'}])
        out = p.translate_task({'title': 'Complete Essay'}, ctx)
        assert any('Stanford' in t['title'] for t in out)

    def test_verify_dispatched(self, make_college_context):
        ctx = make_college_context(colleges=[{'id': 'mit', 'name': 'MIT'}])
        out = p.translate_task({'title': 'Verify Materials Received'}, ctx)
        assert out[0]['artifact_ref']['tab'] == 'colleges'

    def test_unmatched_title_returns_unchanged(self, make_college_context):
        ctx = make_college_context(colleges=[{'id': 'mit', 'name': 'MIT'}])
        task = {'id': 'x', 'title': 'Maintain Strong Grades', 'type': 'core'}
        assert p.translate_task(task, ctx) == [task]
