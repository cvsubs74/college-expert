"""
Unit tests for the scenario corpus: archetype loading, selection policy,
LLM variation parsing + fallback, and apply_variation.

The selection policy tests use a deterministic random.Random(seed) so
shuffle order is reproducible.
"""

import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

import corpus


def _now():
    return datetime(2026, 5, 3, 12, 0, 0, tzinfo=timezone.utc)


# ----------------- Archetype loading ----------------------------------------


def test_load_archetypes_picks_up_every_json_file():
    archetypes = corpus.load_archetypes()
    # We ship 8 archetypes at launch; validate the count + that each has
    # the required fields.
    assert len(archetypes) >= 8
    ids = [a['id'] for a in archetypes]
    assert len(ids) == len(set(ids)), 'archetype ids must be unique'
    for a in archetypes:
        assert 'id' in a
        assert 'description' in a
        assert 'profile_template' in a
        assert 'colleges_template' in a


# ----------------- Selection policy -----------------------------------------


def _archetype(id_):
    return {
        'id': id_,
        'description': f'arch {id_}',
        'profile_template': {'grade_level': '11th Grade'},
        'colleges_template': [],
    }


def test_select_prefers_untried():
    archetypes = [_archetype('a'), _archetype('b'), _archetype('c')]
    history = {
        'a': {'last_run_at': (_now() - timedelta(days=15)).isoformat()},
        'b': {'last_run_at': (_now() - timedelta(days=2)).isoformat()},
        'c': {},  # never run
    }
    chosen = corpus.select_scenarios(
        archetypes, history, n=2, rng=random.Random(0), now=_now()
    )
    chosen_ids = [s['id'] for s in chosen]
    # 'a' (15 days old) and 'c' (never run) qualify as untried; 'b' is
    # recent. The first two slots should come from untried.
    assert 'b' not in chosen_ids


def test_select_includes_recent_failure():
    archetypes = [_archetype('stable'), _archetype('flaky')]
    history = {
        'stable': {
            'last_run_at': (_now() - timedelta(days=2)).isoformat(),
            'failures_last_30d': 0,
        },
        'flaky': {
            'last_run_at': (_now() - timedelta(days=2)).isoformat(),
            'failures_last_30d': 1,
        },
    }
    chosen = corpus.select_scenarios(
        archetypes, history, n=1, rng=random.Random(0), now=_now()
    )
    # With n=1, the one slot tends to be 'flaky' due to the
    # recent-failures branch when no untried exist.
    assert chosen[0]['id'] == 'flaky'


def test_select_returns_at_most_n():
    archetypes = [_archetype(f'a{i}') for i in range(10)]
    chosen = corpus.select_scenarios(archetypes, {}, n=4, rng=random.Random(0))
    assert len(chosen) == 4


def test_select_does_not_mutate_archetypes():
    archetypes = [_archetype('a')]
    archetypes[0]['profile_template']['gpa'] = 3.5
    chosen = corpus.select_scenarios(archetypes, {}, n=1, rng=random.Random(0))
    chosen[0]['profile_template']['gpa'] = 9.0
    assert archetypes[0]['profile_template']['gpa'] == 3.5


# ----------------- LLM variation parsing + fallback --------------------------


def test_generate_variation_falls_back_when_no_api_key(monkeypatch):
    monkeypatch.delenv('GEMINI_API_KEY', raising=False)
    archetype = {
        'id': 'x',
        'description': 'd',
        'default_student_name': 'Pat Test',
        'profile_template': {'intended_major': 'Biology'},
    }
    v = corpus.generate_variation(archetype)
    assert v['student_name'] == 'Pat Test'
    assert v['intended_major'] == 'Biology'
    assert v['gpa_delta'] == 0.0


def test_generate_variation_falls_back_on_invalid_json(monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY', 'fake')
    from google import genai

    class _Client:
        def __init__(self, *_a, **_k):
            class _Models:
                def generate_content(self, *_a, **_k):
                    class R:
                        text = 'not json'
                    return R()
            self.models = _Models()

    monkeypatch.setattr(genai, 'Client', _Client)
    archetype = {
        'id': 'x',
        'description': 'd',
        'default_student_name': 'Pat Test',
        'profile_template': {'intended_major': 'Bio'},
    }
    v = corpus.generate_variation(archetype)
    assert v['student_name'] == 'Pat Test'
    assert v['intended_major'] == 'Bio'


def test_generate_variation_strips_code_fences(monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY', 'fake')
    from google import genai

    class _Client:
        def __init__(self, *_a, **_k):
            class _Models:
                def generate_content(self, *_a, **_k):
                    class R:
                        text = (
                            "```json\n"
                            '{"student_name": "Sam Adler", "intended_major": "CS",'
                            ' "extra_interest": "music", "gpa_delta": 0.1}\n'
                            "```"
                        )
                    return R()
            self.models = _Models()

    monkeypatch.setattr(genai, 'Client', _Client)
    archetype = {
        'id': 'x',
        'description': 'd',
        'default_student_name': 'Pat',
        'profile_template': {'intended_major': 'Bio'},
    }
    v = corpus.generate_variation(archetype)
    assert v['student_name'] == 'Sam Adler'
    assert v['intended_major'] == 'CS'
    assert v['extra_interest'] == 'music'
    assert v['gpa_delta'] == 0.1


def test_generate_variation_clamps_gpa_delta(monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY', 'fake')
    from google import genai

    class _Client:
        def __init__(self, *_a, **_k):
            class _Models:
                def generate_content(self, *_a, **_k):
                    class R:
                        text = '{"student_name": "X Y", "intended_major": "M", "extra_interest": "", "gpa_delta": 5.0}'
                    return R()
            self.models = _Models()

    monkeypatch.setattr(genai, 'Client', _Client)
    archetype = {
        'id': 'x',
        'description': 'd',
        'default_student_name': 'Pat',
        'profile_template': {'intended_major': 'Bio'},
    }
    v = corpus.generate_variation(archetype)
    # 5.0 is out of bounds; falls back to 0.0
    assert v['gpa_delta'] == 0.0


# ----------------- apply_variation ------------------------------------------


def test_apply_variation_updates_profile_fields():
    archetype = {
        'id': 'x',
        'description': 'd',
        'profile_template': {
            'gpa': 3.7,
            'intended_major': 'Biology',
            'interests': ['reading'],
        },
        'colleges_template': ['mit'],
    }
    variation = {
        'student_name': 'Sam Lee',
        'intended_major': 'Chemistry',
        'extra_interest': 'lab',
        'gpa_delta': 0.1,
    }
    out = corpus.apply_variation(archetype, variation)
    assert out['profile_template']['full_name'] == 'Sam Lee'
    assert out['profile_template']['intended_major'] == 'Chemistry'
    assert 'lab' in out['profile_template']['interests']
    assert out['profile_template']['gpa'] == 3.8
    assert out['_variation'] == variation
    # Archetype unchanged
    assert archetype['profile_template'].get('full_name') is None
    assert archetype['profile_template']['intended_major'] == 'Biology'


def test_apply_variation_no_double_interest():
    archetype = {
        'id': 'x',
        'description': 'd',
        'profile_template': {'interests': ['robotics']},
        'colleges_template': [],
    }
    variation = {'extra_interest': 'robotics', 'gpa_delta': 0.0,
                 'student_name': 'X Y', 'intended_major': 'CS'}
    out = corpus.apply_variation(archetype, variation)
    assert out['profile_template']['interests'].count('robotics') == 1
