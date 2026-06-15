// "How Stratia Works With AI Agents" — platform / architecture whitepaper.
//
// The third paper in the Resources series. Where paper 1 frames the problem
// and paper 2 walks the roadmap algorithm, this one explains the agent-native
// surface: Stratia runs a remote MCP server, so any AI agent can read your
// data, do real analysis, and write the result back into your app — safely.
//
// Content lives in JS (not MDX) so we keep the existing build setup. Inline
// code in the body uses escaped backticks (\`) because the body is a JS
// template literal. Visuals are referenced by component name and resolved by
// ResourcePaperPage via the visual registry.

const paper = {
    slug: 'how-stratia-works-with-ai-agents',
    type: 'whitepaper',
    title: 'How Stratia Works With AI Agents',
    subtitle:
        'Stratia exposes itself as an MCP server — so Claude, ChatGPT, or any AI agent can read your admissions data, do real analysis, and write the results back into your app, safely and on your behalf.',
    description:
        'Most software is a place you go to. Stratia is also a system your AI agent can operate. It runs a remote MCP server that lets any AI agent sign in, work with your real college data through 31 purpose-built tools, and save what it produces back into your app — with guardrails that keep every call scoped to you.',
    readTime: '13 min read',
    category: 'Platform & Architecture',
    publishedAt: '2026-06-15',

    card: {
        icon: 'PuzzlePieceIcon',
        gradient: 'from-violet-600 to-fuchsia-600',
        accentColor: '#6D28D9',
        bgPattern:
            'radial-gradient(circle at 18% 28%, rgba(109,40,217,0.10) 0%, transparent 50%), radial-gradient(circle at 82% 72%, rgba(192,38,211,0.07) 0%, transparent 50%)',
    },

    hero: { component: 'AgentBridgeFlow' },

    sections: [
        {
            id: 'the-shift',
            title: 'Software you use, or software your agent operates',
            body: `Most software is a destination. You open the app, you click around, you do the work with your own two hands. Stratia is that — a web app with a Colleges tab, a Plan, a Research Notebook. But it is also something less common: **a system an AI agent can operate on your behalf.**

The reason matters. A growing number of students, parents, and counselors don't start their day in a college-counseling app. They start it in an AI assistant — Claude, ChatGPT, a coding-style agent — because that's where they already think out loud, paste a transcript, or ask "is this list realistic?" The honest question for any modern tool is: *can the assistant the user already trusts actually do something useful with my product, or does it just describe it from the outside?*

Stratia's answer is to expose itself over **MCP** — the Model Context Protocol — as a set of tools an agent can call. Not a chatbot bolted onto the marketing site. The real thing: your college list, your fit analyses, your profile, your roadmap, your research notebook, reachable by the agent you already use, scoped to you, with safe write actions included. The app is one client. Your agent is another. They read and write the same data.

This paper explains how that works — the connector, the tool surface, the safety model, and the round trip that takes analysis your agent does and lands it back inside your app.`,
        },
        {
            id: 'the-connector',
            title: 'The connector: one URL, and your agent has tools',
            body: `**MCP is an open standard for connecting AI agents to tools and data.** An agent that speaks MCP can call any MCP server's tools through the same interface — which means building *one* connector makes Stratia usable from *every* MCP-capable agent at once. Claude, ChatGPT, Cursor, and the rest don't each need a custom integration; they speak the same protocol.

Stratia's connector is a **remote MCP server** — a small, always-on service (FastMCP over streamable HTTP, running on Google Cloud Run), not something you download or install. The setup is one step: you add a single URL to your agent and sign in once with Google. From that moment your agent has a Stratia toolset.

The sign-in does double duty. The Google account you authenticate with **is** your Stratia identity — the verified email is the only key the server uses to decide whose data a given tool call touches. There is no separate API key to paste, no shared secret to leak, and no way for one student's session to read another's data. Every tool call resolves "who is this?" from the signed-in identity behind the request, every time.

The connector speaks open standards on both sides: OAuth with dynamic client registration so any compliant agent can register itself, and MCP's tool protocol so the agent discovers what's available. You don't configure tools one by one. You connect once, and the agent sees the whole surface.`,
        },
        {
            id: 'the-tool-surface',
            title: 'What an agent can actually do',
            body: `Connecting isn't the interesting part — what the agent can *do* once connected is. The connector exposes **31 purpose-built tools** today, in three families.

**Read (20 tools) — see everything the app sees.** Your full academic profile; your college list with each school's status and current fit category; a complete fit analysis for any school (match %, scored factors, gap analysis, strategy, timeline, essay angles, scholarships); upcoming deadlines across your whole list; essays, financial-aid packages, the scholarship tracker, your credit balance; and the entire university knowledge base by search or by school. An agent can answer "what's due in the next two weeks and which of those am I behind on?" without you copy-pasting a thing.

**Act (write tools) — make safe changes.** Add or remove a college from your list, recompute a fit against the latest data, update a single profile field, build your whole profile from a document, or record a real admission decision. These change your data, so they're labeled as such and the agent asks before doing anything destructive (see the next section).

**Remember (research notebook) — keep the work.** Save a piece of analysis to your Research Notebook, search and revisit earlier notes, get a bird's-eye overview of what you've researched and what's missing, pin your master strategy, refresh notes built on older data, and turn a note's recommendations into roadmap tasks.

The surface is deliberately comprehensive. The design goal was that an agent should be able to do anything you could do yourself in the app — not a thin read-only slice that forces you back into the UI for every real action.`,
            visual: { component: 'ToolSurfaceGrid' },
        },
        {
            id: 'your-data-only',
            title: "It's your data, and only yours",
            body: `Handing an AI agent write access to anything is a fair thing to be nervous about. The connector is built so the agent can never do more than you could do yourself, and never touches anyone else's data.

**Per-user scoping.** Every tool call derives the student from the verified sign-in token. There is no "user_id" parameter an agent could change to look at someone else's list. If you're not authenticated, the call fails. Your data is reachable by exactly one identity: yours.

**Honest tool labels.** Every tool is annotated for the agent's host so it knows what it's about to do. Read tools are marked read-only — the host knows they can't change anything. Write tools are marked as writes, and the genuinely destructive ones (removing a college, deleting a note, clearing a field) are flagged so the agent prompts you for confirmation before acting. The one tool that spends a credit — recomputing a fit, which calls the model — is labeled accordingly and rate-limited more tightly than the rest.

**Rate limits and a kill switch.** Writes are throttled per minute and credit-spending recomputes per hour, so a runaway agent can't drain your credits or hammer the backend. And the entire connector sits behind a kill switch: if it ever needs to be taken offline, it can be disabled instantly without a redeploy, while a health check stays up. The transport layer also validates request origins to block the classic browser-based rebinding attacks against local agents.

None of this is visible to you in normal use. That's the point: the safe path is the default path, and the agent is structurally prevented from coloring outside the lines.`,
        },
        {
            id: 'the-round-trip',
            title: "The round trip: work doesn't stay in the chat",
            body: `This is the part that makes the connector more than a fancy read-only API. **Analysis your agent does flows back into your app.**

Think about what normally happens when you ask an assistant to compare two schools or draft an application timeline: you get a great answer, and then it evaporates into a chat history you'll never scroll back to. The work was real; the persistence wasn't.

The connector closes that loop. When your agent produces something worth keeping — a college comparison, a timeline, essay angles, a scholarship plan, a deep-dive, an overall strategy — it saves the analysis straight into your **Research Notebook** with one tool call. The note lands in your app, linked to the exact colleges it's about (so it shows up on their cards), tagged, and stamped with provenance: which agent produced it, and which admissions-data cycle it was based on, so the app can flag it later if newer data arrives.

It doesn't stop at a note. The agent can turn a note's recommendations into **roadmap tasks** — each task linked back to the note that produced it — so research becomes action on your Plan, not a paragraph you have to re-read and manually transcribe. And it works in the other direction too: hand your agent a transcript, résumé, or activities list, and it reads the document and builds your structured Stratia profile in a single call, merging cleanly into whatever you already had.

The throughline: you do the thinking with the agent you like, and the *durable artifacts* — notes, tasks, a profile — accumulate inside the product where the rest of your application work already lives.`,
            visual: { component: 'ClosedLoopDiagram' },
        },
        {
            id: 'honest-about-itself',
            title: 'Honest about itself: attribution, repeatable workflows, and a ledger that keeps score',
            body: `An agent-operable system can quietly become a system that lies about its own provenance — claiming everything was written by one model, or pretending a prediction was better than it was. Stratia is built to resist both.

**Honest attribution.** Every note the connector saves is labeled with the *real* agent that made it, derived from the client's own registration. A note written through ChatGPT says ChatGPT; one written through Claude says Claude; an unrecognized client keeps its own name or a neutral "an AI agent" label. It is never silently relabeled as something it wasn't. When you look back at your notebook, you can trust the byline.

**Workflows as repeatable recipes.** When your agent saves analysis, it can also capture *how* it got there — your original request in your own words, plus the ordered steps it ran ("pulled my profile," "got Duke & UCSD fit," "compared against my list"). That turns a one-off result into a recipe you can re-run later as your data changes. Across all users, these step-sequences are aggregated — stripped of any personal data — into **Popular Workflows**, so the system can surface the research patterns that actually help, rather than guessing.

**A ledger that grades the predictions.** This is the sharpest example. Your agent can record what *actually happened* — accepted, waitlisted, denied, deferred, enrolled — for each school, kept cleanly separate from where you are in the application process. Stratia then compares those real outcomes against the fit categories it predicted, and shows you the scorecard: *we called Michigan a Target and you got in; we called Cornell a Reach and you were waitlisted.* A tool that confidently scores your chances should be willing to be checked against reality. The Decision Ledger is the system keeping score on itself, in the open.`,
        },
        {
            id: 'what-this-gets-you',
            title: 'What this gets you',
            body: `The architecture is the means. Here's what changes for the person at the keyboard:

- **Use the assistant you already use.** Your real college data shows up inside Claude, ChatGPT, or whichever MCP agent you live in — not behind one more login you have to remember to open.
- **The agent reasons over your real situation, not a generic guess.** It reads your actual profile, your actual list, your actual fit scores — so "is this realistic?" gets an answer grounded in your data, not in averages.
- **Nothing good gets lost.** The comparison, the timeline, the strategy your agent produced lands back in your app, linked to the right schools and ready to act on — instead of scrolling away in a chat log.
- **It stays yours.** Every call is scoped to your sign-in, destructive actions ask first, and credits are protected. The agent can do what you could do — and nothing more.
- **It's honest about itself.** Notes are labeled by who wrote them, the steps are repeatable, and the system grades its own predictions against what really happened.

Stratia's bet is that the future of this kind of tool isn't a walled app you have to live inside. It's a well-defined, safe surface that the AI you already trust can operate — turning your assistant into a genuine collaborator on the one application process that's hard to get a second try at.`,
        },
    ],
};

export default paper;
