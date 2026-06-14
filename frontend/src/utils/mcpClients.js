/**
 * Config for the "Connect your AI agent" hub. The Stratia connector is a single
 * remote MCP server (Streamable HTTP + OAuth 2.1 / Dynamic Client Registration +
 * Google sign-in); each client below just adds that one URL. Steps/requirements
 * are current as of 2026-06 (researched from official docs); UI labels drift, so
 * copy is intentionally forgiving. Override nothing server-side per client — the
 * same endpoint serves them all.
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
      'In Claude, go to Settings → Connectors (Team/Enterprise: Organization settings → Connectors).',
      "Scroll down and click 'Add custom connector'.",
      'Paste the MCP URL below. Leave the Advanced (Client ID/Secret) fields blank — the server registers itself.',
      "Click Add → Connect, then complete the Google sign-in.",
      "In a chat, open '+' → Connectors and toggle Stratia on.",
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
      'On chatgpt.com, open Settings → Apps & Connectors → Advanced settings and turn Developer mode ON.',
      "Back on Apps & Connectors, click Create. Name it 'Stratia' and paste the MCP URL below.",
      "Set Authentication to OAuth, leave Client ID/Secret blank, check 'I trust this application', then Create.",
      'Complete the Google sign-in / consent — the connector shows connected.',
      "In a new chat, open '+' → Developer mode and enable Stratia for that chat.",
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
      'Run the command below (add --scope user to share across all projects).',
      'Start Claude Code and run /mcp, select stratia, and choose authenticate.',
      'Complete the Google sign-in in the browser that opens.',
      'Run /mcp again to confirm stratia is connected.',
    ],
    command: `claude mcp add --transport http stratia ${MCP_URL}`,
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
    requires: 'Free; personal Google account.',
    steps: [
      'Install: npm install -g @google/gemini-cli',
      'Run the command below (add -s user for user scope).',
      'Start gemini; on first use it opens the browser for Google sign-in.',
      'Run /mcp to confirm stratia is connected.',
    ],
    command: `gemini mcp add --transport http stratia ${MCP_URL}`,
  },
  {
    id: 'windsurf',
    name: 'Windsurf',
    sub: 'Cascade',
    emoji: '⋈',
    supported: true,
    requires: 'No paid tier for individuals (Enterprise: admin enables MCP).',
    steps: [
      "Settings → Cascade → MCP Servers → Manage MCPs → 'View raw config'.",
      "Add the entry below under mcpServers (note the 'serverUrl' field), then Save.",
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
    requires: 'Free, open-source. Use a recent Cline build for OAuth.',
    steps: [
      "Open Cline → MCP Servers icon → 'Remote Servers' tab.",
      "Name it 'stratia-connector', paste the MCP URL, Transport = Streamable HTTP.",
      'Click Add Server and complete the Google sign-in in the browser.',
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
      "Settings → Extensions → '+ Add custom extension'.",
      "Type = Streamable HTTP, Name 'Stratia', Endpoint = the MCP URL; leave headers empty.",
      'On first use, complete the Google sign-in in the browser.',
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
export const ASK_PROMPTS = [
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
  };
}
