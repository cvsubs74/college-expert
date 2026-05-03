# PRD: Deploy script account & project pinning

Status: Approved (shipped in PR #1, doc backfilled 2026-05-03)
Owner: Engineering
Last updated: 2026-05-03

## Problem

The engineer who works on this codebase keeps two GCP accounts active in `gcloud`: a personal Google account (`cvsubs@gmail.com`, project `college-counselling-478115`) where this app is deployed, and a work account (OneTrust) which is the active default for unrelated reasons. `gcloud config` is process-wide state shared across every shell, so any tooling — or any run of `deploy.sh` — picks up whichever account/project happens to be active at that moment.

The failure mode is silent: a deploy can target the wrong project, leak the wrong service account into a binding, or read secrets from the wrong source. We've already had a near-miss where a deploy was about to land in the work project. Cross-account leaks of this kind are hard to undo and impossible to attribute after the fact.

## Goals

- A deploy run for college-expert always targets `college-counselling-478115` under `cvsubs@gmail.com`, regardless of the operator's `gcloud config`.
- Operators see a clear failure if the required account isn't logged in (rather than a silent fall-through to whatever the active account happens to be).
- No reliance on `gcloud config set` — that mutates user-global state and bleeds into other projects.

## Non-goals

- Service-account–based deploys from CI. CI uses Cloud Build's own identity; the pinning here is for human-driven `./deploy.sh` runs from a developer laptop.
- Multi-environment support (staging vs. prod). The codebase has one environment today.
- Per-component overrides. Every cloud function in this project deploys to the same project; we don't need per-script flexibility.

## Users

- Engineering, running `./deploy.sh` and `./deploy_frontend.sh` from a laptop where multiple GCP accounts are configured.

## User stories

1. *Run the deploy from a fresh shell where my work account is the default*. The script targets the personal account anyway and tells me clearly which one it used.
2. *Run the deploy when I haven't logged into my personal account in a while*. The script fails fast with a "run `gcloud auth login --account=cvsubs@gmail.com`" hint, rather than deploying to the wrong place.
3. *Read the deploy logs after the fact*. The first lines confirm the account + project so I can verify retroactively.

## Success metrics

- Zero deploys to the wrong project from this point forward.
- Operator-time-to-detect-misconfiguration drops from "noticed when something broke in prod" to "first second of running the script."

## Open questions

- None remaining at backfill time. The `CLOUDSDK_CORE_ACCOUNT` / `CLOUDSDK_CORE_PROJECT` env-var approach is the documented gcloud override mechanism and works on every gcloud command without touching user config.
