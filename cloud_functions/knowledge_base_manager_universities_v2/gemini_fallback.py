"""Gemini model-fallback for chat calls.

When the primary model is overloaded (503 UNAVAILABLE / "high demand") or
rate-limited (429 / RESOURCE_EXHAUSTED), retry the same request against the next
model in the chain instead of failing the chat. Each model taps a different
capacity pool, so an overload on one rarely hits all of them. Non-capacity errors
(bad request, auth, etc.) fail fast so we don't mask real bugs.

Two entry points cover both SDK shapes in this codebase:
  * generate_content_with_fallback — new ``google-genai`` ``client.models`` API
    (university chat, fit chat).
  * send_message_with_fallback — legacy ``google.generativeai`` GenerativeModel
    chat API (counselor chat). Its SDK is imported lazily so services that only
    use the new SDK don't need the legacy package installed.

Kept self-contained — these Cloud Functions deploy independently and share no
common package, so an identical copy lives in each chat service.
"""
import logging

logger = logging.getLogger(__name__)

# Ordered chain: cheap/fast primary first, then progressively different pools.
DEFAULT_MODEL_CHAIN = (
    "gemini-2.5-flash-lite",
    "gemini-2.5-flash",
    "gemini-2.0-flash",
)

# Substrings that mark a transient overload / rate-limit worth retrying elsewhere.
_CAPACITY_MARKERS = (
    "503", "unavailable", "overloaded", "high demand",
    "429", "resource_exhausted", "resource exhausted", "quota",
)


def is_capacity_error(exc) -> bool:
    """True if the exception looks like a transient overload / rate-limit."""
    msg = str(exc).lower()
    return any(m in msg for m in _CAPACITY_MARKERS)


def generate_content_with_fallback(client, *, contents, config, models=None):
    """``client.models.generate_content``, walking the chain on capacity errors.

    Returns the first successful response. On a capacity error it retries the next
    model; when the chain is exhausted (or on a non-capacity error) it re-raises.
    """
    chain = tuple(models) if models else DEFAULT_MODEL_CHAIN
    last_index = len(chain) - 1
    for i, model in enumerate(chain):
        try:
            response = client.models.generate_content(
                model=model, contents=contents, config=config
            )
            if i:
                logger.warning("Gemini recovered on fallback model %s", model)
            return response
        except Exception as e:  # noqa: BLE001 — we branch on the error message
            if is_capacity_error(e) and i < last_index:
                logger.warning("Model %s unavailable (%s); trying %s", model, e, chain[i + 1])
                continue
            raise


def send_message_with_fallback(message, *, history, system_instruction, models=None):
    """Legacy ``start_chat(history).send_message(message)`` with model fallback.

    Same contract as ``generate_content_with_fallback`` for the older
    ``google.generativeai`` SDK. The SDK is imported lazily so services that only
    use the new SDK never need it installed.
    """
    import google.generativeai as genai  # lazy: only the counselor service calls this

    chain = tuple(models) if models else DEFAULT_MODEL_CHAIN
    last_index = len(chain) - 1
    for i, model_name in enumerate(chain):
        try:
            model = genai.GenerativeModel(model_name, system_instruction=system_instruction)
            chat = model.start_chat(history=history)
            response = chat.send_message(message)
            if i:
                logger.warning("Counselor Gemini recovered on fallback model %s", model_name)
            return response
        except Exception as e:  # noqa: BLE001 — we branch on the error message
            if is_capacity_error(e) and i < last_index:
                logger.warning("Model %s unavailable (%s); trying %s", model_name, e, chain[i + 1])
                continue
            raise

# Deployed by the auto-deploy pipeline; an identical copy lives in each chat service.
