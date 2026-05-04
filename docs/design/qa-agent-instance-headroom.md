# Design — QA Agent Instance Headroom

Spec: docs/prd/qa-agent-instance-headroom.md.

## Change

`deploy.sh` qa-agent block: `--max-instances=2` → `--max-instances=5`.

## Why 5 (not 3, not 10)

- 1 long-running `/run` + concurrent `/summary` from the dashboard +
  scheduled `/run` overlap during a manual trigger = up to 3 in-flight
  at once today.
- Add headroom for the `/feedback` polling on the dashboard, plus a
  buffer for the inevitable bursty refresh.
- 5 is small enough that runaway Gemini-call costs are bounded if a
  bug ever causes a tight loop. At Gen 2 concurrency=1, max parallel
  Gemini calls = 5.

## Cost

Cloud Functions only bills for active instance time, so going from
max=2 to max=5 adds **zero** standing cost. The only delta is during
genuine concurrency bursts, which is exactly the case we're trying
to serve.

## Rollout

1. Merge PR.
2. Redeploy via the standard `./deploy.sh qa-agent` flow.
3. Monitor logs for 7 days; expect zero "no available instance"
   warnings.

## Rollback

Revert the deploy.sh diff and redeploy. The old revision is still in
Cloud Run's history.
