"""
Unit tests for cloud_functions/counselor_agent/work_feed.py.

Covers the pure logic that drives the "This Week" focus card:
  - Urgency thresholds at boundaries
  - Date parsing edge cases
  - Sort key (date items first, nulls last)
  - Per-source normalizers + their filtering rules
  - Deadline grace window (recent overdue kept; ancient overdue dropped)
  - Cache TTL behavior

Source-fetcher tests stub `requests.get` so we don't make network calls.
"""

from datetime import datetime, date, timedelta
from unittest.mock import patch

import pytest

import work_feed as wf


# ---------------------------------------------------------------------------
# Date parsing
# ---------------------------------------------------------------------------

class TestParseIsoDate:
    @pytest.mark.parametrize('value,expected', [
        ('2026-05-15', date(2026, 5, 15)),
        ('2026-12-31', date(2026, 12, 31)),
        ('2026-01-01', date(2026, 1, 1)),
        ('2026-05-15T10:00:00Z', date(2026, 5, 15)),         # tolerates time suffix
        ('2026-05-15 10:00:00', date(2026, 5, 15)),
    ])
    def test_valid_iso_date(self, value, expected):
        assert wf._parse_iso_date(value) == expected

    @pytest.mark.parametrize('value', [None, '', 'not a date', 'abc-de-fg', 12345, []])
    def test_invalid_returns_none(self, value):
        assert wf._parse_iso_date(value) is None


# ---------------------------------------------------------------------------
# days_until + urgency thresholds
# ---------------------------------------------------------------------------

class TestUrgency:
    TODAY = date(2026, 5, 1)

    @pytest.mark.parametrize('due,expected_urgency', [
        (date(2026, 4, 25), 'overdue'),                       # < 0 days
        (date(2026, 4, 30), 'overdue'),                       # -1 day
        (date(2026, 5, 1),  'urgent'),                        # 0 days (today)
        (date(2026, 5, 2),  'urgent'),                        # 1 day
        (date(2026, 5, 8),  'urgent'),                        # exactly 7 days
        (date(2026, 5, 9),  'soon'),                          # 8 days
        (date(2026, 5, 31), 'soon'),                          # exactly 30 days
        (date(2026, 6, 1),  'later'),                         # 31 days
        (date(2027, 5, 1),  'later'),                         # 1 year out
    ])
    def test_thresholds_at_boundaries(self, due, expected_urgency):
        assert wf._urgency(due, self.TODAY) == expected_urgency

    def test_none_due_returns_none(self):
        assert wf._urgency(None, self.TODAY) is None

    def test_days_until_basic(self):
        assert wf._days_until(date(2026, 5, 10), self.TODAY) == 9
        assert wf._days_until(date(2026, 4, 30), self.TODAY) == -1
        assert wf._days_until(None, self.TODAY) is None


# ---------------------------------------------------------------------------
# Sort: date-bearing items first (oldest due first), nulls last
# ---------------------------------------------------------------------------

class TestSortKey:
    def test_date_items_before_null_items(self):
        items = [
            {'due_date': None, 'source': 'essay', 'title': 'b'},
            {'due_date': '2026-06-01', 'source': 'roadmap_task', 'title': 'a'},
            {'due_date': '2026-05-15', 'source': 'scholarship', 'title': 'c'},
            {'due_date': None, 'source': 'essay', 'title': 'a'},
        ]
        items.sort(key=wf._sort_key)
        ordered_dates = [i.get('due_date') for i in items]
        assert ordered_dates == ['2026-05-15', '2026-06-01', None, None]

    def test_stable_secondary_sort_by_source_then_title(self):
        # All same date → falls through to source then title.
        items = [
            {'due_date': '2026-05-15', 'source': 'scholarship', 'title': 'b'},
            {'due_date': '2026-05-15', 'source': 'essay', 'title': 'a'},
            {'due_date': '2026-05-15', 'source': 'essay', 'title': 'b'},
        ]
        items.sort(key=wf._sort_key)
        assert [i['source'] for i in items] == ['essay', 'essay', 'scholarship']


# ---------------------------------------------------------------------------
# Title formatting + ID generation
# ---------------------------------------------------------------------------

class TestEssayTitle:
    def test_full_title_with_index_and_prompt(self):
        e = {'university_name': 'Stanford', 'prompt_index': 0, 'prompt_text': 'Why Stanford?'}
        assert wf._essay_title(e) == 'Stanford #1: Why Stanford?'

    def test_long_prompt_gets_truncated(self):
        long_prompt = 'A' * 80
        title = wf._essay_title({'university_name': 'MIT', 'prompt_text': long_prompt})
        assert title.endswith('…')
        assert len(title) < 80 + 10                          # rough check

    def test_no_prompt_just_school(self):
        title = wf._essay_title({'university_name': 'Yale', 'prompt_index': 1})
        assert title == 'Yale #2'

    def test_missing_school_falls_back(self):
        title = wf._essay_title({})
        assert title == 'Essay'


class TestDeadlineId:
    def test_replaces_spaces_with_underscores(self):
        assert wf._deadline_id('stanford', 'Regular Decision') == 'deadline_stanford_Regular_Decision'

    def test_handles_missing_uni(self):
        assert wf._deadline_id(None, 'Early Action') == 'deadline_unknown_Early_Action'

    def test_handles_missing_type(self):
        assert wf._deadline_id('mit', None) == 'deadline_mit_deadline'


# ---------------------------------------------------------------------------
# Per-source normalizers
# ---------------------------------------------------------------------------

class TestNormalizeTasks:
    TODAY = date(2026, 5, 1)

    def test_completed_tasks_filtered_out(self):
        tasks = [
            {'task_id': 't1', 'title': 'Done', 'status': 'completed'},
            {'task_id': 't2', 'title': 'Pending', 'status': 'pending'},
        ]
        result = wf._normalize_tasks(tasks, self.TODAY)
        assert len(result) == 1
        assert result[0]['id'] == 't2'

    def test_normalized_shape(self):
        result = wf._normalize_tasks([{
            'task_id': 't1',
            'title': 'Submit MIT app',
            'description': 'Common App + supplements',
            'due_date': '2026-05-10',
            'university_id': 'mit',
            'university_name': 'MIT',
            'status': 'pending',
            'notes': 'don\'t forget portfolio',
        }], self.TODAY)
        item = result[0]
        assert item['id'] == 't1'
        assert item['source'] == 'roadmap_task'
        assert item['title'] == 'Submit MIT app'
        assert item['subtitle'] == 'Common App + supplements'
        assert item['due_date'] == '2026-05-10'
        assert item['days_until'] == 9
        assert item['urgency'] == 'soon'
        assert item['university_id'] == 'mit'
        assert item['notes'] == 'don\'t forget portfolio'
        assert item['deep_link'] == '/roadmap?tab=plan&task_id=t1'

    def test_falls_back_to_id_field_when_task_id_missing(self):
        result = wf._normalize_tasks([{'id': 'old_id', 'title': 'a', 'status': 'pending'}], self.TODAY)
        assert result[0]['id'] == 'old_id'


class TestNormalizeEssays:
    TODAY = date(2026, 5, 1)

    def test_final_essays_filtered_out(self):
        essays = [
            {'essay_id': 'e1', 'status': 'final'},
            {'essay_id': 'e2', 'status': 'draft'},
            {'essay_id': 'e3', 'status': 'not_started'},
        ]
        result = wf._normalize_essays(essays, self.TODAY)
        assert {item['id'] for item in result} == {'e2', 'e3'}

    def test_essays_have_no_due_date(self):
        # Essays don't carry a per-row due date in the current schema.
        result = wf._normalize_essays([{
            'essay_id': 'e1', 'status': 'draft', 'university_name': 'MIT',
            'prompt_text': 'Why MIT?', 'prompt_index': 0,
        }], self.TODAY)
        assert result[0]['due_date'] is None
        assert result[0]['urgency'] is None
        assert result[0]['deep_link'] == '/roadmap?tab=essays&essay_id=e1'


class TestNormalizeScholarships:
    TODAY = date(2026, 5, 1)

    @pytest.mark.parametrize('status', ['received', 'not_eligible', 'RECEIVED', 'Not_Eligible'])
    def test_terminal_statuses_filtered_out(self, status):
        result = wf._normalize_scholarships([{'scholarship_id': 's1', 'status': status}], self.TODAY)
        assert result == []

    def test_active_scholarship_kept(self):
        result = wf._normalize_scholarships([{
            'scholarship_id': 's1',
            'scholarship_name': 'Need-based aid',
            'university_name': 'Stanford',
            'university_id': 'stanford',
            'status': 'applied',
            'deadline': '2026-06-01',
            'notes': 'follow up on Wednesday',
        }], self.TODAY)
        assert len(result) == 1
        assert result[0]['id'] == 's1'
        assert result[0]['days_until'] == 31
        assert result[0]['urgency'] == 'later'
        assert result[0]['deep_link'] == '/roadmap?tab=scholarships&scholarship_id=s1'


class TestNormalizeDeadlines:
    TODAY = date(2026, 5, 1)

    def test_recent_overdue_kept(self):
        # 2 days past deadline → still surfaced as 'overdue' (within grace window)
        deadlines = [{
            'university_id': 'mit', 'university_name': 'MIT',
            'deadline_type': 'Regular Decision', 'date': '2026-04-29',
        }]
        result = wf._normalize_deadlines(deadlines, self.TODAY)
        assert len(result) == 1
        assert result[0]['urgency'] == 'overdue'
        assert result[0]['days_until'] == -2

    def test_ancient_overdue_dropped(self):
        # >7 days past → dropped entirely
        deadlines = [{
            'university_id': 'mit', 'university_name': 'MIT',
            'deadline_type': 'Early Decision', 'date': '2026-01-01',
        }]
        assert wf._normalize_deadlines(deadlines, self.TODAY) == []

    def test_grace_boundary_exact(self):
        # exactly _OVERDUE_GRACE_DAYS past → kept
        boundary = self.TODAY - timedelta(days=wf._OVERDUE_GRACE_DAYS)
        deadlines = [{
            'university_id': 'mit', 'university_name': 'MIT',
            'deadline_type': 'EA', 'date': boundary.isoformat(),
        }]
        assert len(wf._normalize_deadlines(deadlines, self.TODAY)) == 1

    def test_future_deadline_kept(self):
        deadlines = [{
            'university_id': 'stanford', 'university_name': 'Stanford',
            'deadline_type': 'Early Action', 'date': '2026-11-01',
        }]
        result = wf._normalize_deadlines(deadlines, self.TODAY)
        assert result[0]['urgency'] == 'later'

    def test_deadlines_have_no_user_notes(self):
        # KB-derived items don't have user-owned notes.
        result = wf._normalize_deadlines([{
            'university_id': 'mit', 'university_name': 'MIT',
            'deadline_type': 'RD', 'date': '2026-11-01',
        }], self.TODAY)
        assert result[0]['notes'] is None


# ---------------------------------------------------------------------------
# Source fetchers — best-effort: log + return [] on failure.
# ---------------------------------------------------------------------------

class TestSourceFetchers:
    def test_returns_list_on_success(self):
        class _R:
            status_code = 200
            def json(self):
                return {'tasks': [{'task_id': 't1'}]}
        with patch.object(wf.requests, 'get', return_value=_R()):
            assert wf._fetch_roadmap_tasks('u@x.com') == [{'task_id': 't1'}]

    def test_returns_empty_on_non_200(self):
        class _R:
            status_code = 500
            text = 'oops'
        with patch.object(wf.requests, 'get', return_value=_R()):
            assert wf._fetch_essays('u@x.com') == []

    def test_returns_empty_on_exception(self):
        with patch.object(wf.requests, 'get', side_effect=ConnectionError('down')):
            assert wf._fetch_scholarships('u@x.com') == []

    def test_returns_empty_when_key_missing(self):
        class _R:
            status_code = 200
            def json(self):
                return {}                                       # missing 'tasks' key
        with patch.object(wf.requests, 'get', return_value=_R()):
            assert wf._fetch_roadmap_tasks('u@x.com') == []


class TestSafeFetchDeadlines:
    def test_passes_through_aggregator_result(self):
        with patch.object(wf, 'fetch_aggregated_deadlines', return_value=[{'date': '2026-11-01'}]):
            assert wf._safe_fetch_deadlines('u@x.com') == [{'date': '2026-11-01'}]

    def test_swallows_exceptions(self):
        with patch.object(wf, 'fetch_aggregated_deadlines', side_effect=RuntimeError('kb down')):
            assert wf._safe_fetch_deadlines('u@x.com') == []


# ---------------------------------------------------------------------------
# get_work_feed — composition + cache + limit clamping
# ---------------------------------------------------------------------------

class TestGetWorkFeed:
    @pytest.fixture(autouse=True)
    def clear_cache_each_test(self):
        wf._cache.clear()
        yield
        wf._cache.clear()

    def _stub_sources(self, tasks=None, essays=None, scholarships=None, deadlines=None):
        return [
            patch.object(wf, '_fetch_roadmap_tasks', return_value=tasks or []),
            patch.object(wf, '_fetch_essays', return_value=essays or []),
            patch.object(wf, '_fetch_scholarships', return_value=scholarships or []),
            patch.object(wf, '_safe_fetch_deadlines', return_value=deadlines or []),
        ]

    def test_response_shape(self):
        with self._stub_sources()[0], self._stub_sources()[1], \
             self._stub_sources()[2], self._stub_sources()[3]:
            result = wf.get_work_feed('u@x.com', limit=5)
        assert result['success'] is True
        assert result['items'] == []
        assert result['total'] == 0

    def test_limit_clamped_to_min_1(self):
        with self._stub_sources(tasks=[
            {'task_id': f't{i}', 'title': f'T{i}', 'status': 'pending'}
            for i in range(5)
        ])[0], self._stub_sources()[1], self._stub_sources()[2], self._stub_sources()[3]:
            wf._cache.clear()
            result = wf.get_work_feed('u@x.com', limit=0)
        assert len(result['items']) == 1                       # clamped to 1, not 0

    def test_limit_clamped_to_max_50(self):
        many = [{'task_id': f't{i}', 'title': f'T{i}', 'status': 'pending'} for i in range(60)]
        with self._stub_sources(tasks=many)[0], self._stub_sources()[1], \
             self._stub_sources()[2], self._stub_sources()[3]:
            wf._cache.clear()
            result = wf.get_work_feed('u@x.com', limit=999)
        assert len(result['items']) == 50                      # _MAX_LIMIT
        assert result['total'] == 60                           # full count preserved

    def test_results_sorted_by_due_date(self):
        with self._stub_sources(tasks=[
            {'task_id': 'late', 'title': 'Z', 'status': 'pending', 'due_date': '2027-01-01'},
            {'task_id': 'early', 'title': 'A', 'status': 'pending', 'due_date': '2026-06-01'},
        ])[0], self._stub_sources()[1], self._stub_sources()[2], self._stub_sources()[3]:
            wf._cache.clear()
            result = wf.get_work_feed('u@x.com')
        assert [i['id'] for i in result['items']] == ['early', 'late']

    def test_cache_serves_repeat_call(self):
        # First call populates the cache; mutate the stubs and confirm the
        # second call doesn't re-fetch.
        first_tasks = [{'task_id': 't1', 'title': 'first', 'status': 'pending'}]
        second_tasks = [{'task_id': 't2', 'title': 'second', 'status': 'pending'}]

        with patch.object(wf, '_fetch_roadmap_tasks', return_value=first_tasks), \
             patch.object(wf, '_fetch_essays', return_value=[]), \
             patch.object(wf, '_fetch_scholarships', return_value=[]), \
             patch.object(wf, '_safe_fetch_deadlines', return_value=[]):
            r1 = wf.get_work_feed('u@x.com')
        with patch.object(wf, '_fetch_roadmap_tasks', return_value=second_tasks), \
             patch.object(wf, '_fetch_essays', return_value=[]), \
             patch.object(wf, '_fetch_scholarships', return_value=[]), \
             patch.object(wf, '_safe_fetch_deadlines', return_value=[]):
            r2 = wf.get_work_feed('u@x.com')

        # Without invalidation, the second call returns the cached first payload.
        assert [i['id'] for i in r1['items']] == ['t1']
        assert [i['id'] for i in r2['items']] == ['t1']

    def test_invalidate_cache_per_user(self):
        with patch.object(wf, '_fetch_roadmap_tasks', return_value=[
            {'task_id': 't1', 'status': 'pending', 'title': 'a'},
        ]), patch.object(wf, '_fetch_essays', return_value=[]), \
             patch.object(wf, '_fetch_scholarships', return_value=[]), \
             patch.object(wf, '_safe_fetch_deadlines', return_value=[]):
            wf.get_work_feed('u@x.com')
        assert 'u@x.com' in wf._cache
        wf.invalidate_cache('u@x.com')
        assert 'u@x.com' not in wf._cache

    def test_invalidate_cache_all(self):
        wf._cache['a'] = (0.0, [])
        wf._cache['b'] = (0.0, [])
        wf.invalidate_cache(None)
        assert wf._cache == {}
