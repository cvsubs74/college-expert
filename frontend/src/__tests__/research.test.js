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
