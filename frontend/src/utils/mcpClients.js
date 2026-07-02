/**
 * Config for the "Connect your AI agent" hub. The Stratia connector is a single
 * remote MCP server (Streamable HTTP + OAuth 2.1 / Dynamic Client Registration +
 * Google sign-in); each client below just adds that one URL. Steps/requirements
 * verified against each client's official docs on 2026-06-17; UI labels drift, so
 * copy is intentionally forgiving. Override nothing server-side per client — the
 * same endpoint serves them all. We surface only Claude.ai and ChatGPT — the two
 * consumer agents our students actually use.
 */

export const MCP_URL = 'https://stratia-connector-pfnwjfp26a-ue.a.run.app/mcp';

export const MCP_CLIENTS = [
  {
    id: 'claude_web',
    name: 'Claude.ai',
    sub: 'Web & desktop app',
    emoji: '✶',
    primary: true,
    supported: true,
    requires: 'Any plan (Free allows 1 custom connector). No developer mode.',
    steps: [
      'In Claude (web or desktop), go to Settings/Customize → Connectors (Team/Enterprise: an Owner adds it under Organization settings).',
      "Click '+', then 'Add custom connector'.",
      'Paste the MCP URL below. Leave the Advanced (OAuth Client ID/Secret) fields blank — the server self-registers.',
      "Click Add, then complete the Google sign-in when the browser prompt appears.",
      "In a chat, open '+' (lower-left) → Connectors and toggle Stratia on.",
    ],
  },
  {
    id: 'chatgpt',
    name: 'ChatGPT',
    sub: 'Custom connector (Developer mode)',
    emoji: '◍',
    primary: true,
    supported: true,
    requires: 'ChatGPT Plus, Pro, Business, Enterprise or Edu — web only (not mobile/free).',
    steps: [
      'On chatgpt.com (web only), open Settings → Apps & Connectors → Advanced settings and turn Developer mode ON.',
      "Back on Apps & Connectors, click Create. Name it 'Stratia' and paste the MCP URL below.",
      "Set Authentication to OAuth. Leave Client ID/Secret blank — if the UI marks Client ID required, ignore it and submit anyway (the server self-registers). Tick 'I trust this application', then Create.",
      'Complete the Google sign-in / consent — the connector shows connected.',
      "In a chat, open '+' → More and select Stratia for that chat.",
    ],
  },
];

/**
 * Curated "ask something real" prompts that exercise the Stratia tools. Each can
 * be copied or opened directly in Claude / ChatGPT (the connected agent runs the
 * tools to answer).
 */
// A weekly-plan prompt. It doesn't force a save — it asks the agent to offer,
// so if you accept, the agent saves a `weekly_plan` note and the app pins it to
// the top of the Research Notebook as "This week".
export const WEEKLY_PLAN_PROMPT = "Look at my Stratia deadlines, roadmap tasks, and any stale fits, then tell me the 3 most important things to do this week — each one a short action tied to a real deadline or task. When you're done, ask me whether I'd like to save it to my Research Notebook as this week's plan so it pins to the top.";

export const ASK_PROMPTS = [
  { title: "What should I do this week?", prompt: WEEKLY_PLAN_PROMPT },
  { title: 'Build my profile from my transcript', prompt: "I'm attaching my transcript / résumé. Read it and build my Stratia student profile — extract my GPA, test scores, courses, AP exams, activities, leadership, awards and intended major, then save it to my profile." },
  { title: 'Analyze my fit for a dream school', prompt: "Look at my college list and pick my top reach school. Using my profile and its fit analysis, tell me my match category, the 3 biggest gaps holding me back, and a concrete plan to close them. If I don't have a fit analysis for it yet, offer to compute one before spending a credit; if my list is empty, ask me which school to analyze." },
  { title: "What's due next across my list", prompt: 'Show every upcoming deadline across my college list, sorted by date. Flag which are Early Decision vs Early Action vs Regular, and tell me what to prioritize this month.' },
  { title: 'Find scholarships I actually qualify for', prompt: "Look at my profile and scholarship tracker, then surface scholarships I'm eligible for that I haven't started yet. Rank them by award amount and deadline." },
  { title: 'Brainstorm essay angles from my real story', prompt: "Using my extracurriculars, awards, and intended major, draft three distinct Common App personal-statement angles that aren't clichés, each with a one-line hook." },
  { title: 'Build my fall application roadmap', prompt: 'Look at my roadmap tasks, college list, and deadlines, then build a week-by-week action plan from now through my earliest deadline.' },
  { title: 'Compare two colleges side by side', prompt: "Pick two schools from my college list and compare them on my admissions odds, cost after aid, and strength in my intended major. If I have fewer than two schools on my list, ask me which ones to compare. When you're done, ask me whether I'd like to save the comparison to my Research Notebook." },
  { title: 'Is my list balanced (reach/target/safety)?', prompt: "Pull my full college list with each school's fit category and tell me whether my reach/target/safety balance is healthy. If it's too top-heavy, suggest additions; if my list is empty, suggest a starter set of reach/target/safety schools based on my profile." },
  { title: 'Tune up a stale fit and capture the strategy', prompt: "Check my saved fit analyses for any that are stale. If one is, recompute the one that matters most (yes, spend the credit) and summarize what changed; if none are stale, just tell me that. When you're done, ask me whether I'd like to save the updated strategy to my Research Notebook." },
];

/**
 * A launch prompt that asks the connected agent to RECOMPUTE this school's fit
 * analysis and major-chances itself and SAVE them via the Stratia MCP tools —
 * FREE (0 credits) vs the in-app 1-credit Generate (#310). The server
 * re-derives KB-sourced fields and rejects fabricated numbers, so the saved
 * analysis is trust-identical to an in-app one. Never exposes the save-schema
 * in the UI — the agent fetches it via get_analysis_schema.
 */
export function agentUpdateAnalysisPrompt(universityName) {
  const name = (universityName || '').trim() || 'this school';
  return (
    `Recompute my Stratia fit analysis AND major chances for ${name} and save `
    + `them so I don't spend a credit. Use my profile (get_profile) and the `
    + `school knowledge base (get_university, get_university_majors); call `
    + `get_analysis_schema first for the exact shape, then save with `
    + `save_fit_analysis and save_major_chances. Tell me my fit category and the `
    + `strongest majors when you're done.`
  );
}

/** Open-in-agent deep links for a prompt (best-effort; Copy is the reliable path). */
export function askLinks(prompt) {
  const q = encodeURIComponent(prompt);
  return {
    claude: `https://claude.ai/new?q=${q}`,
    chatgpt: `https://chatgpt.com/?q=${q}`,
  };
}
