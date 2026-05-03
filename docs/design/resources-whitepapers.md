# Design: Resources & Whitepapers

Status: Draft (awaiting approval)
Last updated: 2026-05-03
Related PRD: [docs/prd/resources-whitepapers.md](../prd/resources-whitepapers.md)

## Information architecture

```
/resources                          (new top-level route, public)
  Header: "Resources" + tagline
  Featured strip: hero card for the most-recent paper
  Card grid: one card per whitepaper
        click ↓
  /resources/<paper-slug>           (per-paper reading view)
        Hero (title + subtitle + estimated read time + visuals)
        Section list (rich content + inline visuals)
        Cross-promo footer (link to the other paper)
```

URL strategy:
- `/resources` — hub
- `/resources/hidden-cost-of-research` — paper 1
- `/resources/how-stratia-builds-your-roadmap` — paper 2

Section anchors are URL fragments (`/resources/hidden-cost-of-research#by-the-numbers`) so deep links to specific sections work.

## Frontend

### Components

```
frontend/src/pages/ResourcesPage.jsx        ← /resources hub
frontend/src/pages/ResourcePaperPage.jsx    ← /resources/<slug>

frontend/src/components/resources/
  PaperCard.jsx                ← hub card
  PaperHero.jsx                ← per-paper hero block
  PaperSection.jsx             ← reusable section renderer (title + body + optional visual)
  visuals/
    HiddenCostHero.jsx         ← paper 1 hero infographic
    ResearchTimeBar.jsx        ← paper 1: 35h-of-research bar visualization
    BeforeAfterGrid.jsx        ← paper 1: side-by-side workflow comparison
    ResolverFlow.jsx           ← paper 2: input → resolver → template diagram
    TemplateMatrix.jsx         ← paper 2: 4×3 grade × semester grid
    TranslationDiagram.jsx     ← paper 2: generic task → per-school task
```

All visuals are React components rendering inline SVG with framer-motion animations on view-enter. The pattern intentionally mirrors what regulatory_intelligence's `Insights.jsx` did — gradient backgrounds, hero icons, scroll-triggered reveals.

### Content data

The paper content lives in `frontend/src/data/resources/`:

```
frontend/src/data/resources/
  index.js                     ← exports all papers
  hidden-cost-of-research.js   ← paper 1 content
  how-stratia-builds-roadmap.js ← paper 2 content
```

Each paper file exports an object:

```js
export default {
  slug: 'hidden-cost-of-research',
  type: 'whitepaper',
  title: 'The Hidden Cost of College Research',
  subtitle: 'Why a typical applicant burns 35 hours hunting facts that should already be on one screen',
  description: '<one-paragraph description for the hub card>',
  readTime: '12 min read',
  category: 'Value & Approach',
  publishedAt: '2026-05-03',
  hero: { component: 'HiddenCostHero', /* component-specific props */ },
  card: {
    icon: 'ClockIcon',                   // heroicons name
    color: 'from-emerald-500 to-teal-600',
    bgPattern: 'radial-gradient(...)',
  },
  sections: [
    {
      id: 'opening',                     // becomes #opening anchor
      title: 'The scale nobody talks about',
      body: `markdown-style string (rendered by react-markdown)`,
      visual: { component: 'ResearchTimeBar', props: {...} },
    },
    // ... more sections
  ],
};
```

Content is markdown strings inside JS — same pattern regulatory_intelligence's `Insights.jsx` uses. Renders via `react-markdown` (already a dep). Custom React components for visuals are referenced by name and resolved at render time.

### Routes

In `App.jsx`:

```jsx
<Route path="/resources"        element={<ResourcesPage />} />
<Route path="/resources/:slug"  element={<ResourcePaperPage />} />
```

No `<ProtectedRoute>` wrapper — Resources is public.

### Nav

Add a "Resources" entry to the top-level nav alongside "Roadmap":

```js
const navLinks = [
  { label: 'Roadmap',   to: '/roadmap',   requiresAuth: true  },
  { label: 'Resources', to: '/resources', requiresAuth: false },
];
```

Logged-out users see only Resources (and the marketing landing page). Logged-in users see both.

## Whitepaper visuals — spec for paper 1

### Hero: `HiddenCostHero`

A clock-shaped infographic with 12 segments, each labeled with a research dimension (degrees, deadlines, supplements, financial aid, merit scholarships, demonstrated interest, test policy, location, fit, alumni, athletics, application platform). Animation: segments fill sequentially with a scrubbing motion as the user scrolls into view. Total filled time = 35 hours, surfaced as a center label.

### Section visual: `ResearchTimeBar`

Horizontal stacked bar chart. 10 schools as rows; each row split into 7 segments (one per research dimension). Hovering a segment surfaces the time estimate ("Financial aid breakdown — 25 min"). Aggregate across all rows = ~35 hours, shown above the chart.

### Section visual: `BeforeAfterGrid`

Two columns. Left: a chaotic-looking grid of mini-screenshots (university page, Google Doc, Notion, Sheets, email, browser tabs). Right: a single Stratia screen — the Colleges tab with one card expanded. Animated transition: mini-screenshots fly in and consolidate into the right column on scroll. The "savings" overlay numerically counts up to ~30 hours.

## Whitepaper visuals — spec for paper 2

### Hero: `ResolverFlow`

A horizontal flow diagram: inputs (Grade · Graduation year · College list · Today) → priority cascade box (caller > profile > caller-grade-only > default) → output box (template + grade + semester + source). Each priority rule lights up sequentially based on a staggered animation. Sample inputs are real ("graduation_year=2027 · today=Apr 2026 → junior_spring · profile").

### Section visual: `TemplateMatrix`

A 4×3 grid: rows = grade (freshman, sophomore, junior, senior), columns = semester (fall, spring, summer). Each cell shows the template name if one exists, else the fallback ("falls back to → spring"). The cell corresponding to the user's example (junior, spring) glows. junior_summer is the only summer cell with a real template — visually distinct.

### Section visual: `TranslationDiagram`

A vertical "before / after" flow:
- Top: a generic template task — "Submit RD Applications" with no school context.
- Middle: an arrow labeled "translate against college list = [MIT, Stanford, UC Berkeley, UC Davis, UCLA]".
- Bottom: three task pills:
  - "Submit MIT app — Jan 5" with an `Open MIT` artifact_ref pill.
  - "Submit Stanford app — Jan 2" with an `Open Stanford` pill.
  - "Submit UC Application — Nov 30" with an `Open UC Berkeley, UC Davis, UCLA` pill (group treatment).

## Backend

No backend work for the launch.

The whitepapers are static frontend content. If we ever want analytics ("which paper got read more") we add a small `track-resource-view` endpoint to whichever cloud function is convenient — but that's a follow-up, not launch.

## SEO + sharing

- Each paper page sets:
  - `<title>` to the paper title.
  - `<meta name="description">` to the subtitle.
  - Open Graph tags (`og:title`, `og:description`, `og:type=article`, `og:image=<paper-specific image>`).
  - Twitter card tags.
- The hub page sets `<title>Resources — Stratia Admissions</title>`.
- Open Graph images: pre-rendered PNG export of each paper's hero visual. Stored in `frontend/public/og-images/<slug>.png`. Generation: a one-off Playwright script that loads each hero in isolation and screenshots it. Run on demand, not in CI.

## Visual production process

For each visual:
1. Build the React component with framer-motion animations.
2. Render in dev, screenshot at design-quality resolution.
3. Iterate on layout, color, motion until it lands.
4. (For OG images) export a static PNG snapshot.

Brand alignment: pick up the existing tailwind palette (the emerald/teal already used in counselor chat and pill components). No new design tokens.

## Performance

- The reading view loads paper content client-side (markdown is in the JS bundle). Each paper's content + visual components is roughly 50–100KB minified.
- Code-split per paper: each `ResourcePaperPage` loads its visual components via `React.lazy()` so a user reading paper 1 never downloads paper 2's bundle.
- Hub page is small (cards only) and loads fast even on slow connections.

## Testing strategy

- **Vitest**: hub page renders all paper cards from the data array; clicking a card navigates to the right `/resources/<slug>`. Per-paper page renders the right hero + sections + visuals.
- **Playwright**: E2E covers (1) load `/resources`, see both cards, (2) click a card, land on the paper, (3) deep link to a section anchor scrolls correctly. Public route — no auth bypass needed.
- **Manual**: reading the actual content end-to-end on desktop and mobile. Visuals render and animate cleanly. No layout shift on slow connections.

## Phasing

| PR | Scope |
|---|---|
| 1 | Hub page (`ResourcesPage.jsx`) + routing + nav entry. Empty list of papers initially. |
| 2 | Paper 1 content + reading view (`ResourcePaperPage.jsx`) + paper 1 visuals. |
| 3 | Paper 2 content + paper 2 visuals. |
| 4 | OG images + meta tags polish. |

PRs 1 and 2 land back-to-back. PR 3 can land independently. PR 4 is polish.

## Risks

- **Content quality is the gate, not the code.** Bad whitepapers shipped beautifully are still bad whitepapers. Mitigation: each paper goes through a content review with the user before merging the implementation PR.
- **Visual production overhead.** Hand-coded SVG infographics are time-consuming. Mitigation: aggressive scoping — 3 visuals per paper, not 8. Reuse a `<Visual>` wrapper component so motion + responsive behavior is consistent.
- **Code-and-content coupling.** Editing a paper means a code commit. Acceptable for two papers; revisit if we ever have 20.
- **Public-readable content drift.** A future paper could accidentally mention non-public details (an unreleased feature, an internal customer). Mitigation: review checklist on every paper PR.
- **Mobile typography.** Long-form reading needs care at small breakpoints. Mitigation: use a tested typographic scale (1.6 line-height, max-width 65ch); we already have these tokens in the existing Tailwind setup.

## Alternatives considered

- **Static MDX files.** Slightly more ergonomic for long-form content. Rejected for now: existing tooling renders markdown strings via react-markdown without an MDX setup; adding MDX is a tooling expansion we don't need yet.
- **Hosted-elsewhere blog (Substack, Medium).** Rejected: links the trust-building content to a third-party brand and breaks the integrated nav experience. Lose deep-link control too.
- **PDFs.** Rejected: gates the content behind a download step and breaks mobile reading. HTML is the right format for this audience.
- **Email gating.** Rejected per the PRD.
- **Whitepaper-as-interactive-app** (e.g., a calculator that takes a college list and shows your projected research time). Compelling but scope-creeps the launch. Defer to a v2 follow-up after the static papers prove the engagement model.

## Open implementation questions for engineering

- Should we use `react-router`'s scroll restoration for paper anchors, or implement scroll-to-anchor manually with `useEffect`? Recommend manual — react-router's restoration plays poorly with hash-only navigation.
- Tailwind prose styles (`@tailwindcss/typography`) for the reading view? Recommend yes — gives us defaults for headings, lists, blockquotes inside markdown content. Adds one devDependency.
- Color palette for paper-2 visuals — same emerald/teal as paper 1, or a distinct tone (sapphire / indigo) so the papers feel like a series with variation? Recommend: paper 2 uses indigo/sapphire as the primary; both share the same neutral typography.
