/**
 * Config for the "Connect your AI agent" hub. The Stratia connector is a single
 * remote MCP server (Streamable HTTP + OAuth 2.1 / Dynamic Client Registration +
 * Google sign-in); each client below just adds that one URL. Steps/requirements
 * verified against each client's official docs on 2026-06-17; UI labels drift, so
 * copy is intentionally forgiving. Override nothing server-side per client — the
 * same endpoint serves them all. Config JSON keys differ per client and are
 * load-bearing: Cursor uses `url`, Windsurf uses `serverUrl`, VS Code nests under
 * `servers` with `type:"http"`, Cline uses `type:"streamableHttp"`, Goose uses
 * `type:"streamable_http"`/`uri`, Gemini CLI's settings.json uses `httpUrl`.
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
  {
    id: 'claude_code',
    name: 'Claude Code',
    sub: 'CLI',
    emoji: '⌘',
    primary: true,
    supported: true,
    requires: 'Any Claude login or Anthropic API key.',
    steps: [
      'Run the command below (it uses --scope user so Stratia is available across all your projects).',
      'Start Claude Code and run /mcp, select stratia, and choose authenticate.',
      'Complete the Google sign-in in the browser that opens.',
      'Run /mcp again to confirm stratia is connected.',
    ],
    command: `claude mcp add --transport http --scope user stratia ${MCP_URL}`,
  },
  {
    id: 'cursor',
    name: 'Cursor',
    sub: 'IDE',
    emoji: '▷',
    supported: true,
    requires: 'Any plan, including Free.',
    steps: [
      'Settings → Tools & MCP → New MCP Server (opens mcp.json).',
      'Add the entry below (just a url — no type or client id), then Save.',
      "The server shows 'Needs Login' — click it and complete the Google sign-in.",
    ],
    config: `{
  "mcpServers": {
    "stratia-connector": {
      "url": "${MCP_URL}"
    }
  }
}`,
    deepLink:
      'cursor://anysphere.cursor-deeplink/mcp/install?name=stratia-connector&config=eyJ1cmwiOiJodHRwczovL3N0cmF0aWEtY29ubmVjdG9yLXBmbndqZnAyNmEtdWUuYS5ydW4uYXBwL21jcCJ9',
  },
  {
    id: 'vscode',
    name: 'VS Code',
    sub: 'GitHub Copilot (Agent mode)',
    emoji: '⧉',
    supported: true,
    requires: 'GitHub Copilot (any plan) with Chat in Agent mode.',
    steps: [
      "Command Palette → 'MCP: Add Server' → HTTP → paste the MCP URL → name it 'stratia'.",
      'Choose Workspace or Global, then click Start on the server.',
      'Complete the Google sign-in when the browser opens.',
    ],
    config: `{
  "servers": {
    "stratia": {
      "type": "http",
      "url": "${MCP_URL}"
    }
  }
}`,
    deepLink:
      'vscode:mcp/install?%7B%22name%22%3A%22stratia%22%2C%22type%22%3A%22http%22%2C%22url%22%3A%22https%3A%2F%2Fstratia-connector-pfnwjfp26a-ue.a.run.app%2Fmcp%22%7D',
  },
  {
    id: 'gemini_cli',
    name: 'Gemini CLI',
    sub: 'CLI',
    emoji: '✦',
    supported: true,
    requires: 'Free; personal Google account. Needs a recent gemini-cli (remote-server OAuth).',
    steps: [
      'Install or update: npm install -g @google/gemini-cli',
      'Run the command below — it adds Stratia at user scope (without -s user it would only apply in the current folder).',
      'Start gemini and run: /mcp auth stratia — a browser opens for Google sign-in; approve it. (This step is required; sign-in does not start on its own.)',
      'Run /mcp to confirm stratia is connected. If sign-in never opens, update gemini-cli and retry — older versions lack remote-server OAuth.',
    ],
    command: `gemini mcp add --transport http -s user stratia ${MCP_URL}`,
  },
  {
    id: 'windsurf',
    name: 'Windsurf',
    sub: 'Cascade',
    emoji: '⋈',
    supported: true,
    requires: 'No paid tier for individuals (Enterprise: admin enables MCP).',
    steps: [
      "Open Windsurf Settings → Cascade → MCP Servers (or the MCP icon at the top of the Cascade panel), then click 'View raw config'.",
      "Add the entry below under mcpServers (note the 'serverUrl' field — Windsurf-specific; no headers/API key), then Save.",
      'Click Refresh and complete the Google sign-in when prompted.',
    ],
    config: `{
  "mcpServers": {
    "stratia-connector": {
      "serverUrl": "${MCP_URL}"
    }
  }
}`,
  },
  {
    id: 'cline',
    name: 'Cline',
    sub: 'VS Code / JetBrains',
    emoji: '◆',
    supported: true,
    requires: 'Free, open-source. Cline 3.x or newer (OAuth for remote servers).',
    steps: [
      "Open Cline → MCP Servers icon → 'Remote Servers' tab.",
      "Name it 'stratia-connector', paste the MCP URL, set Transport Type = Streamable HTTP, then click Add Server.",
      "The server appears needing auth — click its 'Authenticate' button, then complete the Google sign-in in the browser.",
    ],
    config: `{
  "mcpServers": {
    "stratia-connector": {
      "url": "${MCP_URL}",
      "type": "streamableHttp"
    }
  }
}`,
  },
  {
    id: 'goose',
    name: 'Goose',
    sub: 'Block',
    emoji: '◐',
    supported: true,
    requires: 'Free, open-source. Recent build for Streamable HTTP + OAuth.',
    steps: [
      "Open the Goose sidebar → Extensions → 'Add custom extension'.",
      "Type = 'Remote Extension (Streaming HTTP)', Name 'Stratia', Endpoint = the MCP URL; leave headers empty, then Save.",
      'Start a chat and ask Goose to use a Stratia tool — a browser opens for Google sign-in (OAuth runs on first tool use); approve it.',
    ],
    config: `{
  "extensions": {
    "stratia": {
      "enabled": true,
      "type": "streamable_http",
      "uri": "${MCP_URL}",
      "timeout": 300
    }
  }
}`,
    deepLink:
      'goose://extension?type=streamable_http&url=https%3A%2F%2Fstratia-connector-pfnwjfp26a-ue.a.run.app%2Fmcp&name=Stratia',
  },
];

/**
 * Curated "ask something real" prompts that exercise the Stratia tools. Each can
 * be copied or opened directly in Claude / ChatGPT (the connected agent runs the
 * tools to answer).
 */
// A weekly-plan prompt that explicitly asks the agent to save a `weekly_plan`
// note, so the app pins it to the top of the Research Notebook as "This week".
export const WEEKLY_PLAN_PROMPT = "Look at my Stratia deadlines, roadmap tasks, and any stale fits, then tell me the 3 most important things to do this week — each one short action tied to a real deadline or task. Save it to my research notebook as a weekly_plan so it pins to the top.";

export const ASK_PROMPTS = [
  { title: "What should I do this week?", prompt: WEEKLY_PLAN_PROMPT },
  { title: 'Build my profile from my transcript', prompt: "I'm attaching my transcript / résumé. Read it and build my Stratia student profile — extract my GPA, test scores, courses, AP exams, activities, leadership, awards and intended major, then save it to my profile." },
  { title: 'Analyze my fit for a dream school', prompt: 'Pull my profile and my saved fit analysis for Stanford. Tell me my match category and the 3 biggest gaps holding me back, then give me a concrete plan to close them.' },
  { title: "What's due next across my list", prompt: 'Show every upcoming deadline across my college list, sorted by date. Flag which are Early Decision vs Early Action vs Regular, and tell me what to prioritize this month.' },
  { title: 'Find scholarships I actually qualify for', prompt: "Look at my profile and scholarship tracker, then surface scholarships I'm eligible for that I haven't started yet. Rank them by award amount and deadline." },
  { title: 'Brainstorm essay angles from my real story', prompt: "Using my extracurriculars, awards, and intended major, draft three distinct Common App personal-statement angles that aren't clichés, each with a one-line hook." },
  { title: 'Build my fall application roadmap', prompt: 'Look at my roadmap tasks, college list, and deadlines, then build a week-by-week action plan from now through my earliest deadline.' },
  { title: 'Compare two colleges side by side', prompt: 'Compare UCLA and the University of Michigan for me on admissions odds given my stats, cost after aid, and strength in my intended major. Save the comparison to my notebook.' },
  { title: 'Is my list balanced (reach/target/safety)?', prompt: "Pull my full college list with each school's fit category and tell me if my reach/target/safety balance is healthy. If it's too top-heavy, suggest additions." },
  { title: 'Tune up a stale fit and capture the strategy', prompt: 'Check which of my saved fits are stale, recompute the one that matters most (yes, spend the credit), then summarize what changed and save the updated strategy.' },
];

/** Open-in-agent deep links for a prompt (best-effort; Copy is the reliable path). */
export function askLinks(prompt) {
  const q = encodeURIComponent(prompt);
  return {
    claude: `https://claude.ai/new?q=${q}`,
    chatgpt: `https://chatgpt.com/?q=${q}`,
    gemini: `https://gemini.google.com/app?q=${q}`,
    grok: `https://grok.com/?q=${q}`,
  };
}
