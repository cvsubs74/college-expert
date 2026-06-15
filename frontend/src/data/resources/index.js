// Registry for all resource papers. Adding a new whitepaper is a matter of
// dropping a new file alongside these and importing it here.

import hiddenCostOfResearch from './hidden-cost-of-research';
import howStratiaBuildsRoadmap from './how-stratia-builds-roadmap';
import howStratiaWorksWithAiAgents from './how-stratia-works-with-ai-agents';

export const papers = [
    hiddenCostOfResearch,
    howStratiaBuildsRoadmap,
    howStratiaWorksWithAiAgents,
];

export const papersBySlug = Object.fromEntries(
    papers.map((p) => [p.slug, p])
);

export const getPaperBySlug = (slug) => papersBySlug[slug] || null;
