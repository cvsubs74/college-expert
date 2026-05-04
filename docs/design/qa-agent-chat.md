# Design — QA Agent Chat

Companion to [docs/prd/qa-agent-chat.md](../prd/qa-agent-chat.md).

## Architecture

```
┌─────────────────────────────────┐
│  Dashboard (frontend/src)       │
│  ChatPanel component            │
│  - Messages array (in-memory)   │
│  - Send on Enter                │
└──────────────┬──────────────────┘
               │ POST /chat with Bearer ID token
               │ { question, history: [{role, content}, ...] }
               ▼
┌─────────────────────────────────┐
│  qa-agent (cloud_functions)     │
│  POST /chat → _handle_chat      │
│  1. Auth check (existing)       │
│  2. Load run context            │
│  3. Build prompt                │
│  4. Call Gemini                 │
│  5. Return answer               │
└──────────────┬──────────────────┘
               │
               ▼
       ┌───────────────┐
       │ Firestore     │
       │ qa_runs/      │ (last 30 docs)
       └───────────────┘
       ┌───────────────┐
       │ Gemini 2.5    │
       │ Flash         │
       └───────────────┘
```

## API contract

**`POST /chat`** (admin-auth required, same allowlist as `/run`)

Request:
```json
{
  "question": "Why did synth_high_achiever_junior_all_ucs fail last run?",
  "history": [
    {"role": "user", "content": "What's the worst-performing scenario this week?"},
    {"role": "assistant", "content": "freshman_fall_starter has failed 3 of 5 runs..."}
  ]
}
```

Response:
```json
{
  "success": true,
  "answer": "In run_20260504T010246Z_bdba3a, the scenario failed at the roadmap_generate step. The assertion metadata.template_used=='junior_fall' got 'sophomore_spring' instead. This was caused by the date-aware template drift bug fixed in PR #40 — the scenario was generated assuming fall semester but ran in May (spring).",
  "model": "gemini-2.5-flash",
  "context_run_count": 12
}
```

Error response:
```json
{
  "success": false,
  "error": "no recent runs to ground answer in"
}
```

## Server-side: `_handle_chat`

New file `cloud_functions/qa_agent/chat.py`:

```python
def handle_chat(body: dict, cfg: dict) -> dict:
    question = (body.get("question") or "").strip()
    if not question:
        return {"success": False, "error": "question is required"}, 400

    history = body.get("history") or []
    if not isinstance(history, list):
        return {"success": False, "error": "history must be a list"}, 400

    # Pull recent run context — pass/fail summary + scenario_id + failing
    # step names. Avoid full assertion bodies (token budget).
    runs = _load_recent_run_summaries(limit=30)
    if not runs:
        return {
            "success": False,
            "error": "no runs found yet — trigger a run before chatting",
        }, 400

    # Build prompt
    system = _system_prompt()  # Pinned in chat.py
    context = _format_run_context(runs)  # Compact JSON-ish text
    history_text = _format_history(history)
    full_prompt = f"{context}\n\n{history_text}\n\nUser: {question}"

    # Call Gemini
    answer = _call_gemini(system, full_prompt, cfg["GEMINI_API_KEY"])

    return {
        "success": True,
        "answer": answer,
        "model": "gemini-2.5-flash",
        "context_run_count": len(runs),
    }
```

Wired in `main.py`:

```python
if path == "chat" and request.method == "POST":
    return _cors(_handle_chat(body, cfg))
```

### Context budget

A run summary is roughly:
```
run_20260504T010246Z_bdba3a · 5/8 pass · 2026-05-04T01:02 · agent_loop
  FAIL synth_high_achiever_junior_all_ucs: roadmap_generate (template_used)
  FAIL freshman_fall_starter: roadmap_generate (template_used)
  ...
```

≈100-200 tokens per run × 30 runs = 3-6K tokens for context. Gemini Flash takes 1M tokens of input — we have plenty of headroom for history + question on top.

### System prompt

```
You are a QA analyst answering questions about scheduled monitoring runs of
the Stratia Admissions college-admissions system. You have access to summaries
of the last 30 runs. Each summary lists the run ID, pass/fail counts, trigger,
and (for failing scenarios) the failing step name + assertion.

Rules:
- Ground every answer in the supplied context. If the user asks about something
  not in the context, say so — never invent run IDs, scenario IDs, or assertions.
- Cite specific run IDs and scenario IDs in your answers when possible.
- Keep answers concise (1-3 paragraphs unless the user asks for more).
- If the context shows a clear pattern (e.g., the same scenario failing 5 times
  in a row), surface it.
```

## Client-side: `ChatPanel.jsx`

New file `frontend/src/components/qa/ChatPanel.jsx`:

```jsx
const ChatPanel = () => {
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState('');
    const [busy, setBusy] = useState(false);

    const handleSend = async () => {
        if (!input.trim() || busy) return;
        const question = input.trim();
        setMessages((prev) => [...prev, { role: 'user', content: question }]);
        setInput('');
        setBusy(true);
        try {
            const resp = await sendChatMessage({ question, history: messages });
            setMessages((prev) => [...prev, { role: 'assistant', content: resp.answer }]);
        } catch (err) {
            setMessages((prev) => [...prev, { role: 'assistant', content: `Error: ${err.message}`, isError: true }]);
        } finally {
            setBusy(false);
        }
    };
    // ...render messages + input + send button...
};
```

Layout: a card on `QaRunsListPage`, below the executive summary, above the run table. Collapsible (toggle button to hide chat when not in use).

Service: add `sendChatMessage` to `frontend/src/services/qaAgent.js`.

## Files

**New (server):**
- `cloud_functions/qa_agent/chat.py` — `handle_chat`, `_load_recent_run_summaries`, `_format_run_context`, `_call_gemini`, `_system_prompt`
- `tests/cloud_functions/qa_agent/test_chat.py` — tests for each helper + `handle_chat` happy path / error paths

**Modified (server):**
- `cloud_functions/qa_agent/main.py` — wire `/chat` route in `qa_agent` dispatch

**New (frontend):**
- `frontend/src/components/qa/ChatPanel.jsx`
- `frontend/src/__tests__/ChatPanel.test.jsx`

**Modified (frontend):**
- `frontend/src/services/qaAgent.js` — add `sendChatMessage`
- `frontend/src/pages/QaRunsListPage.jsx` — render `<ChatPanel />`

## Trade-offs

**Why not streaming?** Chat replies are short enough (1-3 paragraphs ≈ 2-3 sec) that streaming UX adds complexity for marginal benefit. Revisit if we add long-form analysis.

**Why no server-side history persistence?** v1 is per-tab. Adding Firestore-backed history requires storage rules, cleanup of stale conversations, and per-user keying. Not worth it before we know the feature gets used.

**Why feed the LLM raw run summaries instead of letting it tool-call into Firestore?** Tool calls add a round trip per query. For "summarize last 30 runs" type questions, having all the data in the prompt is faster. If we add ad-hoc analysis (e.g., "compare this week vs last week"), we'll revisit with tool calls.

**Why not RAG?** 30 runs × 200 tokens = 6K tokens. Fits easily in-context. RAG would help once we have thousands of historical runs, but we're nowhere near that scale.

## Rollout

1. Land `chat.py` + `handle_chat` + tests
2. Land frontend `ChatPanel.jsx` + tests
3. Deploy
4. Try the four PRD jobs-to-be-done questions; verify answers ground correctly
5. Iterate on system prompt based on observed failure modes
