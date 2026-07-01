/**
 * Seed prompts that hand an in-app chat off to the student's own AI agent
 * (Claude / ChatGPT) via the Stratia MCP connector. Each builder turns whatever
 * context a chat holds into a self-contained prompt so the agent can pick up
 * where the in-app chat left off — the "use my preferred surface" option we
 * surface in every chat, and a resilient path when the built-in model is
 * overloaded.
 */

const FIT_LABELS = {
  SAFETY: 'safety',
  TARGET: 'target',
  REACH: 'reach',
  SUPER_REACH: 'high reach',
};

const clean = (s) => (s || '').trim();

/** University KB chat: university name + optional current question. */
export function universityAgentPrompt(universityName, question) {
  const name = clean(universityName) || 'this university';
  const q = clean(question);
  return q
    ? `Using the Stratia tools, tell me about ${name}: ${q}`
    : `Using the Stratia tools, tell me about ${name} — the key facts a student would care about: acceptance rate, popular majors, and campus life.`;
}

/** Fit chat: the student's fit with a university. */
export function fitAgentPrompt(universityName, { fitCategory, intendedMajor, question } = {}) {
  const name = clean(universityName) || 'this university';
  const bits = [
    clean(intendedMajor) && `my intended major is ${clean(intendedMajor)}`,
    FIT_LABELS[fitCategory] && `it's a ${FIT_LABELS[fitCategory]} school for me`,
  ].filter(Boolean).join('; ');
  const ctx = bits ? ` (${bits})` : '';
  const q = clean(question);
  return q
    ? `Using my Stratia profile and my fit analysis for ${name}${ctx}, answer: ${q}`
    : `Using my Stratia profile and my fit analysis for ${name}${ctx}, tell me my admission chances and the biggest gaps I should close.`;
}

/** Counselor chat: roadmap / overall admissions journey. */
export function counselorAgentPrompt(roadmapTitle, question) {
  const q = clean(question);
  if (q) {
    return `Using my Stratia roadmap, profile, deadlines and college list, help me: ${q}`;
  }
  const title = clean(roadmapTitle);
  return title
    ? `Using my Stratia roadmap, profile, deadlines and college list, help me make progress on "${title}" — what are my most important next steps?`
    : 'Using my Stratia roadmap, profile, deadlines and college list, tell me my most important next steps.';
}

/** Essay-help chat: a specific essay prompt + the student's current draft. */
export function essayAgentPrompt(universityName, { promptText, currentText, question } = {}) {
  const school = clean(universityName) ? `${clean(universityName)} ` : '';
  const parts = [`Using my Stratia profile, help me with this ${school}essay prompt: "${clean(promptText)}".`];
  const draft = clean(currentText);
  if (draft) parts.push(`Here's my draft so far: "${draft}".`);
  parts.push(clean(question) || 'Give me specific, personal feedback and concrete next steps.');
  return parts.join(' ');
}

// Consumed by AgentChatHandoff across the University, Fit, Counselor and Essay chats.
