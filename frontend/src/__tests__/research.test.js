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
