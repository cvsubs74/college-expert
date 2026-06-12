"""
Fit history archival + application-clock suppression (#206).

- save_fit_analysis archives the fit being replaced under
  college_fits/{id}/history/{kb_year} (design §3d) — nothing the student
  saw is destroyed by a recompute.
- mark_suppressed flags kb_updates for settled applications (design §3f).
"""

from unittest.mock import MagicMock, patch

import fit_analysis
import fit_staleness as fs


def _existing_fit(kb_year=2025):
    fit = {
        'university_id': 'northeastern',
        'fit_category': 'SAFETY',
        'match_percentage': 82,
    }
    if kb_year is not None:
        fit['kb_data_year'] = kb_year
    return fit


class TestSaveArchivesPriorFit:
    def test_replaced_fit_archived_under_its_kb_year(self):
        db = MagicMock()
        db.get_college_fit.return_value = _existing_fit(kb_year=2025)
        db.save_college_fit.return_value = True
        with patch.object(fit_analysis, 'get_db', return_value=db):
            result = fit_analysis.save_fit_analysis(
                'student@test.com', 'northeastern', {'fit_category': 'TARGET'})

        assert result['success'] is True
        db.archive_college_fit.assert_called_once()
        args = db.archive_college_fit.call_args.args
        assert args[0] == 'student@test.com'
        assert args[1] == 'northeastern'
        assert args[2]['fit_category'] == 'SAFETY'   # the OLD fit
        assert args[3] == '2025'                      # keyed by its KB year

    def test_legacy_fit_archived_under_pre_versioning(self):
        db = MagicMock()
        db.get_college_fit.return_value = _existing_fit(kb_year=None)
        db.save_college_fit.return_value = True
        with patch.object(fit_analysis, 'get_db', return_value=db):
            fit_analysis.save_fit_analysis(
                'student@test.com', 'northeastern', {'fit_category': 'TARGET'})

        assert db.archive_college_fit.call_args.args[3] == 'pre-versioning'

    def test_first_fit_does_not_archive(self):
        db = MagicMock()
        db.get_college_fit.return_value = None
        db.save_college_fit.return_value = True
        with patch.object(fit_analysis, 'get_db', return_value=db):
            fit_analysis.save_fit_analysis(
                'student@test.com', 'northeastern', {'fit_category': 'TARGET'})

        db.archive_college_fit.assert_not_called()

    def test_contentless_placeholder_not_archived(self):
        db = MagicMock()
        db.get_college_fit.return_value = {'university_id': 'northeastern'}  # no fit_category
        db.save_college_fit.return_value = True
        with patch.object(fit_analysis, 'get_db', return_value=db):
            fit_analysis.save_fit_analysis(
                'student@test.com', 'northeastern', {'fit_category': 'TARGET'})

        db.archive_college_fit.assert_not_called()

    def test_get_fit_history_passthrough(self):
        db = MagicMock()
        db.get_college_fit_history.return_value = [{'history_key': '2025'}]
        with patch.object(fit_analysis, 'get_db', return_value=db):
            history = fit_analysis.get_fit_history('student@test.com', 'northeastern')
        assert history == [{'history_key': '2025'}]


class TestMarkSuppressed:
    def _updates(self):
        return [{'university_id': 'northeastern', 'changes': []},
                {'university_id': 'tufts', 'changes': []}]

    def test_settled_statuses_suppressed(self):
        college_list = [
            {'university_id': 'northeastern', 'status': 'applied'},
            {'university_id': 'tufts', 'status': 'planning'},
        ]
        updates = fs.mark_suppressed(self._updates(), college_list)
        by_id = {u['university_id']: u for u in updates}
        assert by_id['northeastern']['nudge_suppressed'] is True
        assert by_id['tufts']['nudge_suppressed'] is False

    def test_accepted_and_rejected_also_suppressed(self):
        for status in ('accepted', 'rejected'):
            updates = fs.mark_suppressed(
                [{'university_id': 'northeastern'}],
                [{'university_id': 'northeastern', 'status': status}])
            assert updates[0]['nudge_suppressed'] is True

    def test_college_not_on_list_is_not_suppressed(self):
        updates = fs.mark_suppressed([{'university_id': 'northeastern'}], [])
        assert updates[0]['nudge_suppressed'] is False

    def test_staleness_data_retained_when_suppressed(self):
        """Suppression gates nudges only — the vintage chip still needs
        the underlying staleness entry."""
        entry = {'university_id': 'northeastern',
                 'changes': [{'field': 'acceptance_rate', 'severity': 'material'}]}
        updates = fs.mark_suppressed(
            [entry], [{'university_id': 'northeastern', 'status': 'applied'}])
        assert updates[0]['changes']  # untouched
