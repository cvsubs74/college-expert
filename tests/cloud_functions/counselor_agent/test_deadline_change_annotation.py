"""
Roadmap deadline-change annotation (#206, design §3f).

A KB refresh can move an application deadline; regenerated tasks must show
the move ('Deadline updated: old → new') instead of silently swapping the
date. task_ids are deterministic per university + plan type.
"""

from planner import annotate_deadline_changes


def _task(task_id='submit_neu_early_decision', due='2026-10-15'):
    return {
        'task_id': task_id,
        'university_id': 'neu',
        'task_type': 'submission',
        'due_date': due,
        'status': 'pending',
    }


class TestAnnotateDeadlineChanges:
    def test_moved_deadline_gets_note_and_previous_date(self):
        saved = [_task(due='2026-11-01')]
        tasks = annotate_deadline_changes([_task(due='2026-10-15')], saved)
        assert tasks[0]['previous_due_date'] == '2026-11-01'
        assert tasks[0]['deadline_change_note'] == 'Deadline updated: 2026-11-01 → 2026-10-15'

    def test_unchanged_deadline_is_not_annotated(self):
        saved = [_task(due='2026-10-15')]
        tasks = annotate_deadline_changes([_task(due='2026-10-15')], saved)
        assert 'previous_due_date' not in tasks[0]
        assert 'deadline_change_note' not in tasks[0]

    def test_new_task_with_no_saved_counterpart_is_not_annotated(self):
        tasks = annotate_deadline_changes([_task()], [_task(task_id='other_task')])
        assert 'previous_due_date' not in tasks[0]

    def test_empty_saved_tasks_is_safe(self):
        tasks = annotate_deadline_changes([_task()], [])
        assert 'previous_due_date' not in tasks[0]
        tasks = annotate_deadline_changes([_task()], None)
        assert 'previous_due_date' not in tasks[0]

    def test_saved_task_without_due_date_ignored(self):
        broken = {'task_id': 'submit_neu_early_decision', 'due_date': None}
        tasks = annotate_deadline_changes([_task(due='2026-10-15')], [broken])
        assert 'previous_due_date' not in tasks[0]

    def test_only_matching_task_ids_are_diffed(self):
        saved = [
            _task(task_id='submit_neu_early_decision', due='2026-11-01'),
            _task(task_id='submit_bu_regular_decision', due='2027-01-05'),
        ]
        tasks = annotate_deadline_changes(
            [_task(task_id='submit_neu_early_decision', due='2026-10-15'),
             _task(task_id='submit_bu_regular_decision', due='2027-01-05')],
            saved,
        )
        assert tasks[0]['previous_due_date'] == '2026-11-01'
        assert 'previous_due_date' not in tasks[1]
