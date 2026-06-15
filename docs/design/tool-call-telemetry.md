# Design exploration: capturing MCP tool-call workflows for usage auditing

Status: **proposal / thoughts** (not built). Prompted by: "we save researches —
should we also save the tool-call workflows that lead to them, so we can see the
most common ways people use Stratia?"

## TL;DR

Yes — capturing tool usage is worth doing, but **reframe it**: the valuable,
cheap thing is an **aggregate tool-call event log (telemetry)**, not per-research
"lineage" traces. The product question — *what workflows do people actually run?*
— is answered by analyzing the event stream (tool frequencies, sequences, funnels
to credit-spend / `save_research`), which does **not** require tying each trace to
a specific research artifact.

Recommended first step: emit one **structured log line per tool call**
(metadata only — no PII payloads) and route Cloud Run logs to **BigQuery** via a
log sink. ~Zero new infra, privacy-friendly, and immediately answers the
"most common workflows" question with SQL. Per-research lineage and an in-app
"popular workflows" surface are good **phase 2/3**, not phase 1.

## What "saving the workflow" could mean — two very different things

1. **Usage telemetry (aggregate).** Log every tool call as an event
   `{user, tool, ts, ok/err, duration, safe params}`. Analyze in aggregate:
   tool frequencies, common 2–3 call sequences (n-grams), funnels (e.g. how often
   `get_fit_analysis` → `recompute_fit`, or what precedes `save_research`).
   → Directly answers "most common workflows." **This is the high-value core.**
2. **Per-research lineage.** Attach the ordered tool calls that preceded a given
   `save_research` to that research doc ("how this analysis was produced").
   → Nice for provenance/debugging, but needs reliable conversation correlation
   (see limitation below), adds PII/storage weight, and isn't needed to answer
   the product question. **Defer.**

## Feasibility in our architecture

- **Single chokepoint is easy to add.** Today each `@mcp.tool` in `server.py`
  calls `_email()` / `_rate_guard()` itself; there's no middleware. A thin
  decorator (`@instrumented`) wrapping each tool body — record start, call, record
  `{tool, email, duration_ms, status, arg_keys}` — is ~30 lines and the only
  change. (FastMCP middleware in `mcp==1.27.2` is an option but the decorator is
  version-proof and explicit.)
- **Identity is already available.** `get_access_token()` yields the subject
  (email) and `client_id` (the registered MCP client, ~stable per Claude/ChatGPT
  install). Enough to attribute events to a user and client.
- **Storage pattern exists.** `store.py` is a Firestore K/V with TTL + a
  fixed-window counter (`rate_allow`); an events collection or counters would
  slot in the same way. But Firestore is a poor fit for *analytical* queries
  (sequences/funnels) — prefer logs→BigQuery for that (below).

### The real limitation: we can't perfectly reconstruct a "conversation"

The connector is `stateless_http=True`. The access token identifies the **user**
(stable across *all* their conversations), not a single chat. Claude/ChatGPT do
**not** pass a stable per-conversation id we can read in a tool, and MCP's
`Mcp-Session-Id` isn't maintained in stateless mode. So server-side we cannot
reliably group calls into "the tool calls of one conversation."

**Mitigation:** *sessionize by time* — treat a user's consecutive tool calls with
gaps < ~30 min as one workflow during analysis. Good enough for aggregate
patterns; imperfect for exact per-research attribution. Exact grouping would
require leaving stateless mode (operationally heavier) for marginal benefit — not
worth it for analytics.

## Where to store it

| Option | Pros | Cons | Verdict |
|---|---|---|---|
| **Structured logs → BigQuery sink** | ~0 new infra (Cloud Run already logs to Cloud Logging); decoupled from serving DB; SQL for sequences/funnels; cheap at our volume | analytics not "live" in-app without a query layer | **Recommended for analytics** |
| **Firestore events collection** | queryable in-app; reuse `store.py` | per-call write cost/latency; bad at sequence/funnel queries; PII sprawl | Optional, for small live counters only |

Tool-call volume is low (per-user, rate-limited), so cost is negligible either way.
Make the write **fire-and-forget / log-only** so telemetry never adds latency or
can fail a tool call.

## Privacy is the gating constraint

Tool args/results carry student PII (profile, fits, essays). The log must be
**metadata-only**:
- Record: tool name, timestamp, hashed-or-plain user id, client_id, ok/error,
  duration, and *coarse* params at most (e.g. `university_id` is low-sensitivity;
  raw essay/profile text is **never** logged).
- No tool **results/payloads**.
- Set a **retention policy** (e.g. 90–180 days raw events; keep aggregates longer).
- Be transparent — note usage analytics in the connector consent / `/connect`
  copy. This is the student's own data product; surveillance optics matter.

## What the analytics unlock (the payoff)

- **Most-common workflows** — tool n-grams and funnels (the original ask).
- **Credit-spend funnels** — what precedes `recompute_fit`; where users drop off.
- **Tool ROI** — which tools are used vs dead weight (prune or promote).
- **Multi-agent insight** — usage by `client_id` (Claude vs ChatGPT vs Cursor).
- **Closing the loop → product:** the `/connect` "Ask something real" prompts are
  currently hand-written. Telemetry lets them become **data-driven** — surface the
  workflows people actually run successfully as suggested prompts, and (phase 3)
  show users "your most-used workflows." Analytics → product, not just a dashboard.

## Phased recommendation

1. **Phase 1 (do this):** `@instrumented` decorator on every tool → one structured
   log line per call (metadata only). Add a Cloud Logging → BigQuery sink. Write
   2–3 starter SQL views (top tools, top 2-grams, funnel to `save_research` /
   `recompute_fit`). Low risk, high signal.
2. **Phase 2:** small Firestore counters for a live in-app "popular workflows"
   widget; make `/connect` prompts data-driven.
3. **Phase 3 (optional):** per-research lineage (time-sessionized) attached to
   research docs for provenance.

## When NOT to / risks

- If we can't commit to the **privacy** discipline (metadata-only + retention +
  transparency), don't build it.
- Don't over-invest in **per-research lineage** before aggregate telemetry proves
  the value — it's more cost and PII for a narrower benefit.
- Don't leave stateless mode just to get perfect conversation grouping; time-based
  sessionization is sufficient.
