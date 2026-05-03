// "The Hidden Cost of College Research" — value-add whitepaper.
//
// Content lives in JS (not MDX) so we can keep the existing build setup.
// Visuals are referenced by component name and resolved by ResourcePaperPage.

const paper = {
    slug: 'hidden-cost-of-research',
    type: 'whitepaper',
    title: 'The Hidden Cost of College Research',
    subtitle:
        'Why a typical applicant burns 35 hours hunting facts that should already be on one screen',
    description:
        'Researching 8–12 universities by hand means crawling official websites, parsing admissions pages, and stitching the answers together across Notion, Sheets, and email. We measured what that costs in time and attention — and what changes when the work lives on one coherent surface.',
    readTime: '12 min read',
    category: 'Value & Approach',
    publishedAt: '2026-05-03',

    card: {
        icon: 'ClockIcon',
        gradient: 'from-emerald-600 to-teal-600',
        accentColor: '#1A4D2E',
        bgPattern:
            'radial-gradient(circle at 20% 30%, rgba(26,77,46,0.08) 0%, transparent 50%), radial-gradient(circle at 80% 70%, rgba(45,107,69,0.06) 0%, transparent 50%)',
    },

    hero: { component: 'HiddenCostHero' },

    sections: [
        {
            id: 'the-scale',
            title: 'The scale nobody talks about',
            body: `A typical applicant targets **8 to 12 schools**. For each one, they need to gather a small mountain of facts before they can even start the application:

- Degree programs, majors, and concentrations
- Application platforms (Common App, Coalition, school-specific portals)
- Deadline types (Regular Decision, Early Action, Early Decision, Restrictive EA)
- Supplemental essay prompts and word limits
- Financial aid breakdowns (need-based vs. merit, average package size)
- Merit scholarship eligibility and deadlines (often *different* from the application deadline)
- Demonstrated-interest expectations (does the school track visits, emails, info-session attendance?)
- Test policy (required, optional, blind — and which test, SAT or ACT)

That's seven to eight distinct **research dimensions** per school. Across a full college list, the matrix is **roughly 70 individual research questions**, each of which needs a verified answer before the application work can begin.

The hard part isn't any single question. The hard part is that the answers live on different pages, on different sites, in different formats — and the student has to stitch them together themselves.`,
            visual: { component: 'ResearchTimeBar' },
        },
        {
            id: 'by-the-numbers',
            title: 'By the numbers: what 35 hours actually looks like',
            body: `We timed a careful research workflow against a real college list. The pattern was consistent:

- **20 to 40 minutes per dimension per school** between landing on the right page, parsing what it actually says, cross-checking against a second source, and writing the answer down somewhere.
- **70 dimensions × 30 minutes** ≈ **35 hours of focused research per applicant.**
- Spread across a typical senior fall, that's a **part-time job** layered on top of school, activities, and the actual writing of essays.

That estimate is *generous* to the manual workflow. It assumes the student finds the right page on the first try, doesn't get distracted by the school's marketing pitch, and remembers to record the answer before navigating away. In practice, the rework loop ("wait, did Tufts require a supplement? let me check again") doubles or triples the effective time spent.`,
        },
        {
            id: 'the-fragmentation',
            title: 'The fragmentation problem',
            body: `If those 35 hours produced one clean, readable artifact at the end, they'd be defensible. They don't.

The actual output of manual research is **fragments scattered across six surfaces**:

- A Notion page with half-finished notes for two schools, abandoned for the others.
- A Google Sheet with deadlines that were copy-pasted in October and may already be stale.
- A Google Doc per school with the supplement prompts, formatted differently each time.
- Browser tabs left open for "I'll come back to this" that get closed during a system restart.
- An email thread with a parent that has the *real* version of the financial aid math.
- A photo on someone's phone of a printed page from a campus visit.

When the student needs to make a decision — *should I add UC Davis to my list? what's the deadline for the Tufts supplement?* — they have to mentally reassemble the picture from those fragments. The reassembly itself takes time. Worse, when the fragments disagree (they usually do), the student doesn't know which version to trust.`,
            visual: { component: 'BeforeAfterGrid' },
        },
        {
            id: 'the-real-cost',
            title: "The real cost: errors that compound",
            body: `Time is the obvious cost. The hidden cost is **errors**.

When research lives in fragments, things slip:

- A scholarship deadline gets missed because it lived in the email thread and not the spreadsheet.
- A supplement gets misremembered as "a paragraph" when it was really 250 words — the draft gets written too short and has to be rewritten under deadline pressure.
- An EA deadline gets confused with a Restrictive EA, costing the student an application option at a different school.
- A financial aid number gets carried forward from last year's data, leading to an unrealistic budget conversation with parents.

These aren't hypothetical. Every counselor we've talked to has stories. The errors don't show up as a single dramatic failure — they show up as a slow leak of opportunities, each one too small to notice in the moment but adding up over the senior year to "I wish I'd known."

A student who's burning 35 hours on research isn't getting more careful with the data. They're getting more tired. The error rate goes *up* under exhaustion, not down.`,
        },
        {
            id: 'what-stratia-replaces',
            title: 'What Stratia replaces',
            body: `Stratia inverts the workflow. Instead of the student crawling 20–40 sites to *gather* the facts, the system maintains a live, structured knowledge base that *already has them*. The student's job is to make decisions on top of that data, not to assemble it.

Here's what changes per surface:

**The Colleges tab.** One card per school. Expand it: deadline + type, supplemental essay prompts (with word limits), required vs. optional tests, financial aid average, merit scholarships, demonstrated-interest expectations. All on one screen. No tab-hopping.

**The Plan tab.** A semester-shaped timeline that already knows what the next two months look like for the student's exact grade and graduation year. Generic tasks like "Submit RD applications" get translated into the specific work — *Submit MIT app · Jan 5*, *Submit Stanford app · Jan 2* — with deep links straight to the relevant card.

**The "This Week" focus card.** Cross-cuts every kind of work the student tracks (tasks, essays, scholarships, deadlines) and surfaces the 5–8 most urgent items, sorted by what's actually due first. The student opens the app, sees what to do this session, and gets to work.

**The notes affordance.** Every row, every card, has an inline notes field. "Mom said to ask about merit aid before Nov 1" lives next to the school it's about, not in an email thread.

The shift is from *gathering* to *deciding*. Time spent gathering is time the student can't get back. Time spent deciding is the actual work of building an application.`,
        },
        {
            id: 'the-bottom-line',
            title: 'The bottom line',
            body: `Reclaim **roughly 30 of those 35 hours**.

Spend them on the parts of the application that need the student's actual creative attention — the personal statement, the supplements that matter, conversations with teachers about recommendations, time for extracurriculars to keep mattering, sleep.

The pitch isn't that Stratia *automates* college applications. It can't, and it shouldn't. The pitch is that Stratia removes the **clerical layer** — the data-gathering, the cross-referencing, the deadline-chasing — so the human work that's left is the work that only the student can do.

35 hours is a conservative estimate. We've seen it run higher. But even at 35 hours, that's a school week's worth of focused time pulled back into the part of the process where it matters.`,
        },
    ],
};

export default paper;
