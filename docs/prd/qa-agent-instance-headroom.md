# QA Agent — Instance Headroom

## Problem

Cloud Run logs over the past week (2026-04-28 → 2026-05-04) show
**13 occurrences** of `"The request was aborted because there was no
available instance"` for the `qa-agent` function. Each is a real
request that got dropped — typically a `/summary` or `/feedback` from
the dashboard hitting while a `/run` is in flight.

Cloud Functions Gen 2 sets `maxInstanceRequestConcurrency=1` per
instance by default, so when a /run (which can take ~60s end-to-end
including Gemini + downstream cloud function calls) holds the only
instance, the next request waits and may be aborted at the load
balancer.

## Goal

Cut the abort rate to ~0 without paying for idle instances.

## Non-goals

- Not enabling `--min-instances`. Cold starts are acceptable for a
  monitoring service that runs every 30 minutes; we don't want to pay
  for a warm instance 24/7.
- Not raising per-instance concurrency. Each /run does heavy work and
  loads the LLM client; staying at 1 keeps memory predictable.

## Success criteria

- `max-instances` raised so concurrent /summary + /run requests both
  land on their own instance.
- After redeploy: zero "no available instance" warnings for at least
  7 days under normal load.
