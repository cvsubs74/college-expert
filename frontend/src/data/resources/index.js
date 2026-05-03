// Registry for all resource papers. Adding a new whitepaper is a matter of
// dropping a new file alongside these and importing it here.

import hiddenCostOfResearch from './hidden-cost-of-research';
import howStratiaBuildsRoadmap from './how-stratia-builds-roadmap';

export const papers = [
    hiddenCostOfResearch,
    howStratiaBuildsRoadmap,
];

export const papersBySlug = Object.fromEntries(
    papers.map((p) => [p.slug, p])
);

export const getPaperBySlug = (slug) => papersBySlug[slug] || null;
