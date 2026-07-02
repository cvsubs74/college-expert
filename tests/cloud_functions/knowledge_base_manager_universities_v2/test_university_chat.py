"""First tests for university_chat (#286): the two-axis history block is
injected into the system prompt — labeled, precedence-stated, fault-isolated
— and the existing chat response contract is unchanged.

The Gemini call chain is stubbed: generate_content_with_fallback captures
`contents` and returns canned chat JSON; genai types are replaced with
capture-friendly shims (the conftest stubs return None, which would hide the
prompt text these tests need to inspect).
"""

import json
import types as _types

import pytest

CHAT_ANSWER = "The acceptance rate fell from 30% to 25%."
CHAT_JSON = json.dumps({
    "answer": CHAT_ANSWER,
    "suggested_questions": [
        "How competitive is Early Decision?",
        "What are the deadlines?",
        "Is it test optional?",
    ],
})


@pytest.fixture
def chat_env(kb, monkeypatch):
    """Hermetic Gemini stub; returns the capture dict."""
    captured = {}

    def fake_generate(client, contents=None, config=None, **kwargs):
        captured['contents'] = contents
        captured['config'] = config
        return _types.SimpleNamespace(text=CHAT_JSON)

    monkeypatch.setattr(kb.main, 'generate_content_with_fallback', fake_generate)
    monkeypatch.setattr(kb.main, 'types', _types.SimpleNamespace(
        Content=lambda role=None, parts=None: {'role': role, 'parts': parts},
        Part=lambda text=None: text,
        GenerateContentConfig=lambda **k: k,
    ))
    monkeypatch.setattr(kb.main.genai, 'Client', lambda *a, **k: object())
    return captured


def _system_prompt(captured):
    # First content is the system prompt (role user); Part shim returns text.
    return captured['contents'][0]['parts'][0]


def _trends():
    return [
        {'year': 2024, 'cycle_name': 'Class of 2028', 'acceptance_rate_overall': 6.0},
        {'year': 2023, 'cycle_name': 'Class of 2027', 'acceptance_rate_overall': 6.6},
    ]


class TestHistoryInjection:
    def test_multi_version_school_gets_labeled_history_block(self, kb, make_profile, chat_env):
        kb.main.ingest_university(make_profile(acceptance_rate=30.0), year=2025)
        kb.main.ingest_university(
            make_profile(acceptance_rate=25.0, longitudinal_trends=_trends()), year=2026)

        result = kb.main.university_chat('testu', 'How has the acceptance rate changed?')
        assert result['success'] is True

        prompt = _system_prompt(chat_env)
        assert 'YEARLY ADMISSIONS HISTORY:' in prompt
        # Both labels, verbatim trust framing.
        assert ('Stratia KB snapshots (authoritative; keyed by '
                'application-cycle year') in prompt
        assert ('School-reported trend series (UNVERIFIED, entering-class '
                'year axis') in prompt
        # Precedence + never-merge sentences.
        assert 'When the two disagree, prefer the KB snapshots.' in prompt
        assert 'never merge them into one timeline' in prompt
        # Both cycle rows and both trend rows made it in (compact JSON).
        assert '"acceptance_rate":25.0' in prompt
        assert '"acceptance_rate":30.0' in prompt
        assert '"source":"profile_trend"' in prompt
        assert '"verified":false' in prompt

    def test_history_block_sits_after_data_and_rules_stay_intact(self, kb, make_profile, chat_env):
        kb.main.ingest_university(make_profile(acceptance_rate=30.0), year=2025)
        kb.main.ingest_university(make_profile(acceptance_rate=25.0), year=2026)

        kb.main.university_chat('testu', 'Trends?')
        prompt = _system_prompt(chat_env)

        assert (prompt.index('UNIVERSITY DATA:')
                < prompt.index('YEARLY ADMISSIONS HISTORY:')
                < prompt.index('RULES:')
                < prompt.index('RESPONSE FORMAT:'))
        # Existing rules untouched.
        assert 'Only answer based on the data above' in prompt
        assert 'You MUST respond with valid JSON' in prompt

    def test_history_rows_are_null_stripped(self, kb, make_profile, chat_env):
        kb.main.ingest_university(make_profile(acceptance_rate=30.0), year=2025)
        kb.main.ingest_university(make_profile(acceptance_rate=25.0), year=2026)

        kb.main.university_chat('testu', 'Trends?')
        prompt = _system_prompt(chat_env)

        history = prompt[prompt.index('YEARLY ADMISSIONS HISTORY:'):]
        # make_profile has no in/out-of-state rates or testing ranges — those
        # keys must be dropped, not serialized as null.
        assert ':null' not in history
        assert 'in_state_acceptance_rate' not in history
        assert 'sat_middle_50' not in history

    def test_single_snapshot_no_trends_gets_no_block(self, kb, make_profile, chat_env):
        kb.main.ingest_university(make_profile(), year=2026)

        result = kb.main.university_chat('testu', 'What is the acceptance rate?')
        assert result['success'] is True
        assert 'YEARLY ADMISSIONS HISTORY' not in _system_prompt(chat_env)

    def test_history_failure_never_breaks_chat(self, kb, make_profile, chat_env, monkeypatch):
        kb.main.ingest_university(make_profile(), year=2025)
        kb.main.ingest_university(make_profile(), year=2026)

        def boom(*a, **k):
            raise RuntimeError('firestore melted')
        monkeypatch.setattr(kb.main, 'get_university_history', boom)

        result = kb.main.university_chat('testu', 'Trends?')
        assert result['success'] is True
        assert result['answer'] == CHAT_ANSWER
        assert 'YEARLY ADMISSIONS HISTORY' not in _system_prompt(chat_env)


class TestChatContractUnchanged:
    def test_answer_suggestions_and_history_round_trip(self, kb, make_profile, chat_env):
        kb.main.ingest_university(make_profile(), year=2026)

        prior = [
            {'role': 'user', 'content': 'hi'},
            {'role': 'assistant', 'content': 'hello'},
        ]
        result = kb.main.university_chat('testu', 'Acceptance rate?',
                                         conversation_history=prior)

        assert result['success'] is True
        assert result['answer'] == CHAT_ANSWER
        assert len(result['suggested_questions']) == 3
        assert result['university_name'] == 'Test University'
        assert result['university_id'] == 'testu'
        # History appended, not rewritten; answer stored as plain text.
        assert result['conversation_history'][:2] == prior
        assert result['conversation_history'][-2:] == [
            {'role': 'user', 'content': 'Acceptance rate?'},
            {'role': 'assistant', 'content': CHAT_ANSWER},
        ]

    def test_unparseable_model_output_falls_back_to_raw_text(self, kb, make_profile, chat_env, monkeypatch):
        kb.main.ingest_university(make_profile(), year=2026)
        monkeypatch.setattr(
            kb.main, 'generate_content_with_fallback',
            lambda *a, **k: _types.SimpleNamespace(text='plain, not JSON'))

        result = kb.main.university_chat('testu', 'Acceptance rate?')
        assert result['success'] is True
        assert result['answer'] == 'plain, not JSON'
        assert result['suggested_questions'] == []
