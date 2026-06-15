import { describe, it, expect } from 'vitest';
import {
  kindMeta,
  kindsPresent,
  formatDate,
  researchProvenance,
  researchSourceLabel,
} from '../utils/research';

describe('research utils', () => {
  describe('kindMeta', () => {
    it('returns metadata for a known kind', () => {
      expect(kindMeta('comparison').label).toBe('Comparison');
      expect(kindMeta('timeline').emoji).toBeTruthy();
    });
    it('falls back to note for unknown/missing kinds', () => {
      expect(kindMeta('totally_made_up').label).toBe('Note');
      expect(kindMeta(undefined).label).toBe('Note');
    });
  });

  describe('kindsPresent', () => {
    it('returns distinct present kinds in canonical order, unknown → note', () => {
      const notes = [
        { kind: 'timeline' },
        { kind: 'comparison' },
        { kind: 'timeline' }, // dup
        { kind: 'mystery' }, // unknown → note
      ];
      expect(kindsPresent(notes)).toEqual(['comparison', 'timeline', 'note']);
    });
    it('handles empty input', () => {
      expect(kindsPresent([])).toEqual([]);
    });
  });

  describe('formatDate', () => {
    it('formats an ISO date and tolerates junk', () => {
      expect(formatDate('2026-06-14T00:00:00Z')).toMatch(/2026/);
      expect(formatDate('')).toBe('');
      expect(formatDate('not-a-date')).toBe('');
    });
  });

  describe('researchProvenance', () => {
    const now = new Date('2026-06-01T00:00:00Z'); // currentCycleYear → 2026

    it('labels per-client source (legacy Claude, ChatGPT, Cursor, app)', () => {
      // #233: research is attributed to the real MCP client, not always Claude.
      expect(researchProvenance({ source: 'claude_mcp' }, now).sourceLabel).toBe('From Claude'); // legacy notes
      expect(researchProvenance({ source: 'chatgpt' }, now).sourceLabel).toBe('From ChatGPT');
      expect(researchProvenance({ source: 'cursor' }, now).sourceLabel).toBe('From Cursor');
      expect(researchProvenance({ source: 'app' }, now).sourceLabel).toBe('Added in app');
    });

    it('falls back to the stored model name for an unmapped client — never "Claude"', () => {
      const named = { source: 'mcp', provenance: { source: 'mcp', model: 'Acme Agent' } };
      expect(researchProvenance(named, now).sourceLabel).toBe('From Acme Agent');
      const unnamed = { source: 'mcp', provenance: { source: 'mcp' } };
      expect(researchProvenance(unnamed, now).sourceLabel).toBe('From an AI agent');
    });

    it('marks a note stale when its KB cycle is older than the current one', () => {
      const note = { source: 'claude_mcp', created_at: '2025-09-01', provenance: { kb_year: 2025 } };
      const p = researchProvenance(note, now);
      expect(p.cycle).toBe('2025–26');
      expect(p.stale).toBe(true);
    });

    it('is not stale when on the current cycle', () => {
      const p = researchProvenance({ provenance: { kb_year: 2026 } }, now);
      expect(p.cycle).toBe('2026–27');
      expect(p.stale).toBe(false);
    });

    it('reports no cycle (and never stale) when kb_year is absent', () => {
      const p = researchProvenance({ source: 'app', provenance: {} }, now);
      expect(p.cycle).toBeNull();
      expect(p.stale).toBe(false);
    });
  });
});

import { workflowSteps, hasWorkflow, repeatPrompt } from '../utils/research';

describe('research workflow helpers', () => {
  it('workflowSteps coerces strings and filters empties', () => {
    const note = { workflow: [{ tool: 'get_profile', label: 'Pulled profile' }, 'Compared schools', { label: '' }, null] };
    const steps = workflowSteps(note);
    expect(steps).toHaveLength(2);
    expect(steps[1]).toEqual({ tool: '', label: 'Compared schools' });
    expect(workflowSteps({})).toEqual([]);
  });

  it('hasWorkflow is true with an ask OR steps, false otherwise', () => {
    expect(hasWorkflow({ source_prompt: 'compare X and Y' })).toBe(true);
    expect(hasWorkflow({ workflow: [{ label: 'step' }] })).toBe(true);
    expect(hasWorkflow({ source_prompt: '   ', workflow: [] })).toBe(false);
    expect(hasWorkflow({})).toBe(false);
  });

  it('repeatPrompt prefers the original ask', () => {
    expect(repeatPrompt({ source_prompt: 'Compare Duke and UCSD' })).toBe('Compare Duke and UCSD');
  });

  it('repeatPrompt synthesizes from steps + title when no ask', () => {
    const p = repeatPrompt({ title: 'Duke vs UCSD', workflow: [{ label: 'Pulled profile' }, { label: 'Got fit' }] });
    expect(p).toContain('Duke vs UCSD');
    expect(p).toContain('Pulled profile; Got fit');
    expect(p).toMatch(/save the updated result/i);
  });
});

import { workflowSignature, workflowName, groupByWorkflow } from '../utils/research';

describe('workflow grouping (workflows as reusable algorithms)', () => {
  const A1 = { research_id: 'a1', title: 'Duke vs UCSD', created_at: '2026-06-01', source_prompt: 'compare two colleges', workflow_signature: 'get_profile>get_fit_analysis', workflow: [{ tool: 'get_profile', label: 'profile' }, { tool: 'get_fit_analysis', label: 'fit' }] };
  const A2 = { research_id: 'a2', title: 'UCLA vs Cal', created_at: '2026-06-10', source_prompt: 'compare two colleges', workflow_signature: 'get_profile>get_fit_analysis', workflow: [{ tool: 'get_profile', label: 'profile' }, { tool: 'get_fit_analysis', label: 'fit' }] };
  const B1 = { research_id: 'b1', title: 'Timeline', created_at: '2026-06-05', source_prompt: 'build my timeline', workflow_signature: 'get_roadmap>get_deadlines', workflow: [{ tool: 'get_roadmap', label: 'roadmap' }] };
  const NOWF = { research_id: 'n1', title: 'manual note', created_at: '2026-06-02' };

  it('signature prefers the stored value, falls back to tools then ask/title', () => {
    expect(workflowSignature(A1)).toBe('get_profile>get_fit_analysis');
    expect(workflowSignature({ workflow: [{ tool: 'x' }, { tool: 'y' }] })).toBe('x>y');
    expect(workflowSignature({ source_prompt: 'Hi There' })).toBe('p:hi there');
    expect(workflowSignature({})).toBe('');
  });

  it('groups researches by workflow, newest-first within a group, most-run first', () => {
    const groups = groupByWorkflow([A1, A2, B1, NOWF]);
    expect(groups).toHaveLength(2); // NOWF excluded (no workflow)
    expect(groups[0].researches).toHaveLength(2); // the 2-run workflow first
    expect(groups[0].researches[0].research_id).toBe('a2'); // newest first
    expect(groups[0].signature).toBe('get_profile>get_fit_analysis');
    expect(groups[1].researches).toHaveLength(1);
  });

  it('names a workflow from its representative ask', () => {
    expect(workflowName(A1)).toBe('compare two colleges');
  });
});

import { toolLabel, popularWorkflowName, popularWorkflowPrompt } from '../utils/research';

describe('popular workflow helpers', () => {
  it('toolLabel maps known tools and prettifies unknown', () => {
    expect(toolLabel('get_fit_analysis')).toBe('Get fit analysis');
    expect(toolLabel('some_new_tool')).toBe('Some New Tool');
  });
  it('popularWorkflowName builds a kind + step summary', () => {
    const wf = { kind: 'comparison', tools: ['get_profile', 'get_fit_analysis', 'save_research'] };
    expect(popularWorkflowName(wf)).toBe('Comparison: Get profile → Get fit analysis → Save research');
  });
  it('popularWorkflowPrompt is generic and PII-free', () => {
    const p = popularWorkflowPrompt({ kind: 'comparison', tools: ['get_profile', 'get_fit_analysis'] });
    expect(p).toContain('Get profile, then Get fit analysis');
    expect(p).toMatch(/save the result to my research notebook/i);
  });
  it('falls back to the signature when tools are absent', () => {
    expect(popularWorkflowName({ kind: 'note', signature: 'a>b' })).toContain('A → B');
  });
});

import { isoWeekKey, workflowTrend, isNewToUser } from '../utils/research';

describe('popular workflow trending', () => {
  it('isoWeekKey matches ISO-8601 week numbering (and the Python backend)', () => {
    expect(isoWeekKey(new Date('2026-06-15T12:00:00Z'))).toBe('2026-W25'); // a Monday
    expect(isoWeekKey(new Date('2026-01-01T00:00:00Z'))).toBe('2026-W01'); // Thursday → wk 1
    expect(isoWeekKey(new Date('2021-01-01T00:00:00Z'))).toBe('2020-W53'); // Friday → prev year wk 53
  });

  it('workflowTrend flags a real week-over-week jump and ignores noise', () => {
    const now = new Date('2026-06-15T00:00:00Z');
    const thisW = isoWeekKey(now);
    const lastW = isoWeekKey(new Date(now.getTime() - 7 * 86400000));
    expect(workflowTrend({ count: 20, weeks: { [thisW]: 8, [lastW]: 2 } }, now).trending).toBe(true);
    expect(workflowTrend({ count: 4, weeks: { [thisW]: 8, [lastW]: 2 } }, now).trending).toBe(false);  // too few all-time
    expect(workflowTrend({ count: 9, weeks: { [thisW]: 1 } }, now).trending).toBe(false);              // single run
    expect(workflowTrend({ count: 9, weeks: { [thisW]: 4, [lastW]: 4 } }, now).trending).toBe(false);  // flat
    expect(workflowTrend({ count: 9 }, now)).toEqual({ thisWeek: 0, lastWeek: 0, trending: false });   // no buckets
  });

  it('isNewToUser is true only when the signature is not in the user set', () => {
    const own = new Set(['get_profile>get_fit_analysis']);
    expect(isNewToUser({ signature: 'search_universities>add_college' }, own)).toBe(true);
    expect(isNewToUser({ signature: 'get_profile>get_fit_analysis' }, own)).toBe(false);
    expect(isNewToUser({ signature: 'x' }, ['x'])).toBe(false); // accepts arrays too
    expect(isNewToUser({}, own)).toBe(false);                   // no signature → not "new"
  });
});

import { latestWeeklyPlan } from '../utils/research';

describe('weekly plan banner selection', () => {
  it('kindMeta knows the weekly_plan kind', () => {
    expect(kindMeta('weekly_plan').label).toBe('This week');
  });

  it('returns null when there is no weekly_plan note', () => {
    expect(latestWeeklyPlan([{ kind: 'note' }, { kind: 'strategy' }])).toBeNull();
    expect(latestWeeklyPlan([])).toBeNull();
    expect(latestWeeklyPlan(null)).toBeNull();
  });

  it('picks the newest weekly_plan', () => {
    const plan = latestWeeklyPlan([
      { kind: 'weekly_plan', research_id: 'old', created_at: '2026-06-01' },
      { kind: 'note', research_id: 'n' },
      { kind: 'weekly_plan', research_id: 'new', created_at: '2026-06-14' },
    ]);
    expect(plan.research_id).toBe('new');
  });

  it('prefers a pinned weekly_plan over a newer unpinned one', () => {
    const plan = latestWeeklyPlan([
      { kind: 'weekly_plan', research_id: 'newer', created_at: '2026-06-14' },
      { kind: 'weekly_plan', research_id: 'pinned', created_at: '2026-06-10', pinned: true },
    ]);
    expect(plan.research_id).toBe('pinned');
  });
});

import { researchToTasksPrompt, researchTitleMap } from '../utils/research';

describe('research → roadmap loop', () => {
  it('researchToTasksPrompt names the note and calls research_to_tasks (agent-derived)', () => {
    const p = researchToTasksPrompt({ title: 'Duke vs UCSD for CS' });
    expect(p).toContain('Duke vs UCSD for CS');
    expect(p).toContain('research_to_tasks');
    expect(p).toMatch(/roadmap tasks/i);
  });

  it('researchToTasksPrompt falls back gracefully without a title', () => {
    expect(researchToTasksPrompt({})).toContain('my latest Stratia research');
    expect(researchToTasksPrompt(null)).toContain('research_to_tasks');
  });

  it('researchTitleMap maps research_id → title, skipping id-less/null notes', () => {
    const m = researchTitleMap([
      { research_id: 'r1', title: 'A' },
      { research_id: 'r2', title: 'B' },
      { title: 'no id' },
      null,
    ]);
    expect(m).toEqual({ r1: 'A', r2: 'B' });
    expect(researchTitleMap(null)).toEqual({});
  });
});

describe('popularWorkflowPrompt personalization (#249)', () => {
  const wf = { kind: 'comparison', tools: ['get_profile', 'get_fit_analysis'] };

  it('stays the generic PII-free template with no profile/colleges', () => {
    const generic = popularWorkflowPrompt(wf);
    expect(generic).not.toMatch(/Use my real data/);
    expect(popularWorkflowPrompt(wf, {})).toBe(generic);
    expect(popularWorkflowPrompt(wf, { profile: {}, collegeList: [] })).toBe(generic);
  });

  it('interpolates guarded profile + college fields', () => {
    const p = popularWorkflowPrompt(wf, {
      profile: { intended_major: 'CS', gpa_unweighted: 3.95, sat_total: 1530 },
      collegeList: [{ university_name: 'Stanford' }, { name: 'UC Berkeley' }],
    });
    expect(p).toContain('Use my real data');
    expect(p).toContain('intended major CS');
    expect(p).toContain('3.95 GPA/1530 SAT');
    expect(p).toContain('my college list (Stanford, UC Berkeley)');
  });

  it('omits fields that are missing (partial profile)', () => {
    const p = popularWorkflowPrompt(wf, { profile: { intended_major: 'Biology' } });
    expect(p).toContain('intended major Biology');
    expect(p).not.toMatch(/GPA|SAT|ACT|college list/);
  });

  it('prefers SAT but falls back to ACT', () => {
    expect(popularWorkflowPrompt(wf, { profile: { act_composite: 34 } })).toContain('34 ACT');
    expect(popularWorkflowPrompt(wf, { profile: { sat_total: 1480, act_composite: 34 } })).toContain('1480 SAT');
  });

  it('caps the embedded college list at 4 names', () => {
    const colleges = Array.from({ length: 6 }, (_, i) => ({ university_name: `U${i}` }));
    const p = popularWorkflowPrompt(wf, { collegeList: colleges });
    expect(p).toContain('U0, U1, U2, U3');
    expect(p).not.toContain('U4');
  });
});
