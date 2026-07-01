"""Unit tests for the new-SDK Gemini model-fallback helper.

Covers the shared logic used by the university chat and fit chat: on a capacity
error (503 / overload / 429) the request retries the next model in the chain; a
non-capacity error fails fast; an exhausted chain re-raises the last error.
The same file is copied into knowledge_base_manager_universities_v2, so testing
the profile_manager_v2 copy covers both.
"""
import pytest

from gemini_fallback import (
    generate_content_with_fallback,
    is_capacity_error,
    DEFAULT_MODEL_CHAIN,
)

_SENTINEL = object()


class _FakeModels:
    """Records the models tried and raises/returns per a behavior map."""

    def __init__(self, behavior):
        self.behavior = behavior
        self.tried = []

    def generate_content(self, *, model, contents, config):
        self.tried.append(model)
        outcome = self.behavior.get(model, _SENTINEL)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class _FakeClient:
    def __init__(self, behavior):
        self.models = _FakeModels(behavior)


def _overload(msg="503 UNAVAILABLE. This model is currently experiencing high demand"):
    return RuntimeError(msg)


def test_returns_first_model_on_success():
    client = _FakeClient({DEFAULT_MODEL_CHAIN[0]: _SENTINEL})
    result = generate_content_with_fallback(client, contents=[], config=None)
    assert result is _SENTINEL
    assert client.models.tried == [DEFAULT_MODEL_CHAIN[0]]  # no needless fallback


def test_falls_back_to_next_model_on_overload():
    client = _FakeClient({
        DEFAULT_MODEL_CHAIN[0]: _overload(),
        DEFAULT_MODEL_CHAIN[1]: _SENTINEL,
    })
    result = generate_content_with_fallback(client, contents=[], config=None)
    assert result is _SENTINEL
    assert client.models.tried == [DEFAULT_MODEL_CHAIN[0], DEFAULT_MODEL_CHAIN[1]]


def test_walks_entire_chain_then_raises_when_all_overloaded():
    client = _FakeClient({m: _overload() for m in DEFAULT_MODEL_CHAIN})
    with pytest.raises(RuntimeError, match="503"):
        generate_content_with_fallback(client, contents=[], config=None)
    assert client.models.tried == list(DEFAULT_MODEL_CHAIN)  # every model attempted


def test_non_capacity_error_fails_fast():
    client = _FakeClient({DEFAULT_MODEL_CHAIN[0]: ValueError("400 INVALID_ARGUMENT")})
    with pytest.raises(ValueError, match="400"):
        generate_content_with_fallback(client, contents=[], config=None)
    assert client.models.tried == [DEFAULT_MODEL_CHAIN[0]]  # did NOT try other models


def test_custom_model_chain_is_respected():
    client = _FakeClient({"model-b": _SENTINEL, "model-a": _overload()})
    result = generate_content_with_fallback(
        client, contents=[], config=None, models=["model-a", "model-b"]
    )
    assert result is _SENTINEL
    assert client.models.tried == ["model-a", "model-b"]


@pytest.mark.parametrize("msg", [
    "503 UNAVAILABLE",
    "The model is OVERLOADED right now",
    "This model is currently experiencing high demand",
    "429 RESOURCE_EXHAUSTED",
    "quota exceeded",
])
def test_is_capacity_error_true_for_transient(msg):
    assert is_capacity_error(RuntimeError(msg)) is True


@pytest.mark.parametrize("msg", [
    "400 INVALID_ARGUMENT",
    "401 UNAUTHENTICATED",
    "something else entirely",
])
def test_is_capacity_error_false_for_permanent(msg):
    assert is_capacity_error(RuntimeError(msg)) is False
