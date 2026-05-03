// Thin client for the qa-agent Cloud Function. Used by the admin
// dashboard. Always sends the current user's Firebase ID token in the
// Authorization header — the agent's dual-auth gate accepts that for
// admin-allowlisted emails.

import { auth } from '../firebase';

const QA_AGENT_URL = import.meta.env.VITE_QA_AGENT_URL;

async function authHeader() {
    if (!auth.currentUser) {
        throw new Error('not signed in');
    }
    const token = await auth.currentUser.getIdToken();
    return { Authorization: `Bearer ${token}` };
}

async function jsonOrThrow(resp) {
    const text = await resp.text();
    let parsed;
    try {
        parsed = text ? JSON.parse(text) : {};
    } catch {
        parsed = {};
    }
    if (!resp.ok) {
        const err = new Error(parsed.error || `HTTP ${resp.status}`);
        err.status = resp.status;
        err.body = parsed;
        throw err;
    }
    return parsed;
}

// GET /scenarios — public, no auth needed (matches backend).
export async function listScenarios() {
    const resp = await fetch(`${QA_AGENT_URL}/scenarios`);
    return jsonOrThrow(resp);
}

// POST /run — kicks off a fresh batch (or a single archetype if
// `scenarioId` is provided). Returns { run_id, summary }.
export async function triggerRun({ scenarioId = null, actor = '' } = {}) {
    const headers = {
        'Content-Type': 'application/json',
        ...(await authHeader()),
    };
    const body = { trigger: 'manual', actor };
    if (scenarioId) body.scenario = scenarioId;

    const resp = await fetch(`${QA_AGENT_URL}/run`, {
        method: 'POST',
        headers,
        body: JSON.stringify(body),
    });
    return jsonOrThrow(resp);
}

// POST /suggest-cause — LLM analysis of a failing scenario.
export async function suggestCause({ runId, scenarioId }) {
    const headers = {
        'Content-Type': 'application/json',
        ...(await authHeader()),
    };
    const resp = await fetch(`${QA_AGENT_URL}/suggest-cause`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ run_id: runId, scenario_id: scenarioId }),
    });
    return jsonOrThrow(resp);
}

// POST /github-issue — returns a pre-filled URL the browser opens in
// a new tab. The user reviews and submits manually.
export async function buildIssueUrl({ runId, scenarioId }) {
    const headers = {
        'Content-Type': 'application/json',
        ...(await authHeader()),
    };
    const resp = await fetch(`${QA_AGENT_URL}/github-issue`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ run_id: runId, scenario_id: scenarioId }),
    });
    return jsonOrThrow(resp);
}

// GET /summary — executive summary for the dashboard top.
export async function getSummary() {
    const resp = await fetch(`${QA_AGENT_URL}/summary`, {
        headers: await authHeader(),
    });
    return jsonOrThrow(resp);
}

// GET /schedule — current run schedule.
export async function getSchedule() {
    const resp = await fetch(`${QA_AGENT_URL}/schedule`, {
        headers: await authHeader(),
    });
    return jsonOrThrow(resp);
}

// POST /schedule — replace the run schedule. Body shape:
//   { frequency, times[], days[], timezone }
export async function saveSchedule(schedule) {
    const headers = {
        'Content-Type': 'application/json',
        ...(await authHeader()),
    };
    const resp = await fetch(`${QA_AGENT_URL}/schedule`, {
        method: 'POST',
        headers,
        body: JSON.stringify(schedule),
    });
    return jsonOrThrow(resp);
}
