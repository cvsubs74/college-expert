# PRD: Resources & Whitepapers

Status: Approved
Owner: Product
Last updated: 2026-05-03

## Problem

A prospective user — a student, parent, or counselor — landing on Stratia Admissions for the first time has two questions before they're willing to invest in the product:

1. **Why does this matter?** What problem does it actually solve, and how big is that problem? Researching colleges manually means crawling 20–40 university websites, hunting through admissions pages for degree offerings, deadline types, supplemental essay prompts, financial aid breakdowns, and merit-based scholarship eligibility. Per school, that's 2–4 hours of focused research; across a typical 8–12 school list, that's a part-time job spread across senior fall.
2. **How does this thing actually work?** Is the tool just a glorified spreadsheet, or is there real intelligence underneath — and if so, what's the approach?

We have no surface today that answers either question. The marketing site sells. The app itself is gated behind login. Neither tells the kind of substantive, well-reasoned story that builds trust with someone who's already heard pitches from a dozen other admissions tools.

The pattern that works for our regulatory_intelligence sister product is a **Resources hub**: a top-level nav entry that lists thoughtfully-written whitepapers explaining the product's value and approach, with rich visuals that make the arguments stick.

## Goals

- A new top-nav entry, **Resources**, that takes users to a hub listing the available whitepapers.
- Two launch whitepapers:
  - **The Hidden Cost of College Research** — a value-add piece that quantifies the manual research burden and shows how Stratia compresses that work into a single coherent surface.
  - **How Stratia Builds Your Roadmap** — an approach piece that explains, at a high level, how the system turns a student's grade + graduation year + college list into a personalized semester plan with translated tasks, deep-links, and urgency-aware focus.
- Each whitepaper has a card on the hub (gradient + icon + title + subtitle + read-time) and opens to a long-form reading view with sectioned content, embedded visuals, and pull-quotes.
- "Amazing visuals" is a hard requirement, not a stretch goal. Each paper has at least 3 distinct visual elements: hero infographic, comparison/before-after visualization, and a process diagram.
- The hub layout is extensible — adding a third whitepaper later means dropping a content object into the page's content array and ideally adding a standalone HTML page for any interactive diagrams.
- Public-readable: Resources is reachable without login (so prospective users can find it from a marketing link), but the Resources entry shows in the nav for logged-in users too (signed-in students who want to share a paper with parents).

## Non-goals

- A full CMS for whitepapers. Content lives in code; new papers are merged as PRs. We can revisit if the cadence ever justifies a CMS.
- User-generated content (comments, ratings, sharing). Read-only.
- Email-gated downloads ("enter your email to get the PDF"). The whole point is removing friction. The papers are HTML pages, not PDFs.
- Translation / localization. English only at launch.
- A search feature inside Resources. Two papers don't need search.
- SEO optimization beyond standard meta tags. Marketing-page-grade SEO can come later if traffic justifies it.

## Users

- **Primary**: prospective students and parents evaluating whether to sign up for Stratia. They arrive from a Google search, a counselor referral, or a social media link.
- **Secondary**: signed-in students who want to share specific papers with parents or counselors (e.g., "this is what the tool actually does").
- **Tertiary**: high-school counselors evaluating whether to recommend Stratia to their students.

## User stories

1. *As a parent who's just started thinking about college applications for their junior*, I land on Resources, read "The Hidden Cost of College Research," and walk away convinced this is a real problem worth solving with software.
2. *As a student who's heard about Stratia from a friend*, I want to understand what makes it different from a Google Doc with a spreadsheet. The "How Stratia Builds Your Roadmap" paper convinces me there's real intelligence underneath, not vibes.
3. *As a parent reading on my phone in waiting-room downtime*, the papers render cleanly on a small screen and the visuals don't break.
4. *As a counselor looking for evidence to bring to my school's tech-evaluation committee*, I can link directly to a specific paper section (`/resources/hidden-cost-of-research#by-the-numbers`) and the page deep-links work.
5. *As a signed-in student*, the Resources nav entry sits alongside Roadmap so I can find the papers anytime — useful for reminding parents what the app does.

## User stories — paper 1: The Hidden Cost of College Research

The narrative arc:

1. **Open with the scale.** A typical applicant targets 8–12 schools. For each, they need to know: degree programs, admissions deadlines (RD/EA/ED), supplemental essay prompts, average financial aid, merit scholarship eligibility, demonstrated-interest expectations, test policy. That's ~7 dimensions × 10 schools = 70 distinct research questions.
2. **Quantify the time.** Rough estimates per dimension per school: 20–40 minutes between finding the right page, parsing what it says, and recording the answer somewhere. 70 questions × 30 min = ~35 hours of focused research per applicant.
3. **Show what that looks like in practice.** A side-by-side "manual workflow" vs. "Stratia workflow" visualization. The manual side shows tabs, search queries, a Notion doc, a Google Sheet, an email thread with mom — fragments of an answer scattered across 6 surfaces. The Stratia side shows a single coherent screen.
4. **The compounding cost: errors.** When research is fragmented across 6 surfaces, things slip. A scholarship deadline gets missed. An essay prompt gets misremembered. The actual cost isn't just time — it's the lost opportunity from missed details.
5. **What Stratia replaces.** Per school: one card on the Colleges tab showing every dimension. Cross-school: focus card surfaces what's urgent right now. Pre-translated tasks tell you "submit MIT app" not "submit RD applications" — the abstraction layer is removed.
6. **The bottom line.** Reclaim ~30 of those 35 hours. Spend them on the parts of the application that need the student's actual creative attention — essays, activities, outreach — not on manual data hunting.

## User stories — paper 2: How Stratia Builds Your Roadmap

The narrative arc:

1. **Start with the input.** A student tells the app three things: their grade, their graduation year, and their college list (which can be empty at first).
2. **The resolver.** Explain that Stratia derives a precise (grade, semester) state from those inputs and today's date, with named priority rules — so a junior in spring gets exactly the right template, a freshman gets ramp-in tasks, a graduated senior doesn't crash the page.
3. **The templates.** Stratia has 9 hand-curated semester templates (freshman_fall through senior_spring + a special junior_summer). Each template defines phases (e.g., "Test Prep & Activities", "Application Crunch") and the tasks under each phase. The diagram shows the 4-grade × 3-semester grid with the templates that exist mapped to the student's progression.
4. **The translation.** The interesting part. Generic template tasks like "Submit RD Applications" get translated against the student's actual college list into per-school tasks ("Submit MIT app — Jan 5"). UCs get group-treated because of the shared application. Each translated task carries an artifact_ref pointing at the right place to do that task.
5. **The focus card.** The system reads from four sources simultaneously (roadmap tasks, essays, scholarships, college deadlines), bucketizes by urgency, and surfaces the 5–8 most pressing items with a single deep link each.
6. **The pieces that make it real.** A read-side aggregator (counselor_agent), a data manager (profile_manager_v2), a Firestore-backed knowledge base. Live, not static. Each piece called out so the reader sees the architecture is deliberate.
7. **What's not in the algorithm.** No black-box ML. No hidden personalization that's hard to explain. The reasoning chain from inputs to output is fully visible — what you read in the paper IS what runs in production.

## Success metrics

- Resources nav entry visible on every page, public-readable.
- Both whitepapers ship with at least 3 visual elements each (hero, comparison, process diagram).
- 60-second-task test: a parent who lands on the Resources hub can articulate the value-add of the tool after reading paper 1, and the high-level approach after reading paper 2.
- Average time-on-page per whitepaper > 3 minutes (proxy for "they're actually reading it").
- Bounce rate on Resources hub < 50% (proxy for "the cards are compelling enough to click into").

## Open questions

- Domain for Resources URL: `/resources` (matches the nav label) vs. `/insights` (matches regulatory_intelligence). Recommend `/resources` — clearer for a consumer-facing product.
- Should the Resources hub be the public landing page for non-logged-in users (i.e., the homepage redirects to /resources)? Recommend NO for now — keep the marketing landing page as it is, and let Resources be a sibling section.
- Public-readable: confirm with security review. The papers contain no user data and no proprietary algorithms (just architecture descriptions); making them public is fine.
- Visual content production: do we hand-build the infographics in code (SVG + framer-motion), or commission/source them as static PNGs? Recommend code-rendered SVG for the hero + before/after, static PNG only as a fallback. Reasoning: code visuals scale across breakpoints and stay editable without a designer round-trip.
- Should the whitepapers also be downloadable as PDFs? Defer — the HTML versions cover the use case; PDF generation adds tooling burden.
