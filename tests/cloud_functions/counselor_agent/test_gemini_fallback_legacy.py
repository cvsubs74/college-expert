"""Unit tests for the counselor chat's legacy-SDK Gemini model-fallback helper.

Built around GenerativeModel.start_chat(...).send_message(...). Same fallback
contract as the new-SDK helper: retry the next model on an overload, fail fast on
a permanent error, re-raise once the chain is exhausted.
"""
import pytest

import google.generativeai as genai  # the conftest stub; helper imports this lazily
from gemini_fallback import send_message_with_fallback, DEFAULT_MODEL_CHAIN


def _fake_generative_model(behavior, tried):
    """Return a GenerativeModel stand-in driven by a per-model behavior map."""
    class _FakeChat:
        def __init__(self, model_name):
            self._model_name = model_name

        def send_message(self, message):
            tried.append(self._model_name)
            outcome = behavior.get(self._model_name)
            if isinstance(outcome, Exception):
                raise outcome
            return outcome

    class _FakeModel:
        def __init__(self, model_name, system_instruction=None):
            self._model_name = model_name

        def start_chat(self, history=None):
            return _FakeChat(self._model_name)

    return _FakeModel


def test_returns_first_model_on_success(monkeypatch):
    tried = []
    behavior = {DEFAULT_MODEL_CHAIN[0]: "OK"}
    monkeypatch.setattr(genai, "GenerativeModel", _fake_generative_model(behavior, tried))
    resp = send_message_with_fallback("hi", history=[], system_instruction="sys")
    assert resp == "OK"
    assert tried == [DEFAULT_MODEL_CHAIN[0]]


def test_falls_back_on_overload(monkeypatch):
    tried = []
    behavior = {
        DEFAULT_MODEL_CHAIN[0]: RuntimeError("503 UNAVAILABLE high demand"),
        DEFAULT_MODEL_CHAIN[1]: "OK",
    }
    monkeypatch.setattr(genai, "GenerativeModel", _fake_generative_model(behavior, tried))
    resp = send_message_with_fallback("hi", history=[], system_instruction="sys")
    assert resp == "OK"
    assert tried == [DEFAULT_MODEL_CHAIN[0], DEFAULT_MODEL_CHAIN[1]]


def test_non_capacity_error_fails_fast(monkeypatch):
    tried = []
    behavior = {DEFAULT_MODEL_CHAIN[0]: ValueError("400 INVALID_ARGUMENT")}
    monkeypatch.setattr(genai, "GenerativeModel", _fake_generative_model(behavior, tried))
    with pytest.raises(ValueError, match="400"):
        send_message_with_fallback("hi", history=[], system_instruction="sys")
    assert tried == [DEFAULT_MODEL_CHAIN[0]]


def test_exhausted_chain_raises(monkeypatch):
    tried = []
    behavior = {m: RuntimeError("overloaded") for m in DEFAULT_MODEL_CHAIN}
    monkeypatch.setattr(genai, "GenerativeModel", _fake_generative_model(behavior, tried))
    with pytest.raises(RuntimeError, match="overloaded"):
        send_message_with_fallback("hi", history=[], system_instruction="sys")
    assert tried == list(DEFAULT_MODEL_CHAIN)
