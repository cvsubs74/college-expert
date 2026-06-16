import { describe, it, expect } from 'vitest';
import { balanceSegments, balanceVerdict, BALANCE_BANDS, collegeFitCategory, isEstimatedFit } from '../utils/listBalance';

describe('listBalance', () => {
  describe('balanceSegments', () => {
    it('returns all three bands with counts and fractions summing to 1', () => {
      const segs = balanceSegments({ reach: 2, target: 4, safety: 2 });
      expect(segs.map((s) => s.key)).toEqual(BALANCE_BANDS.map((b) => b.key));
      expect(segs.find((s) => s.key === 'target').count).toBe(4);
      expect(segs.reduce((a, s) => a + s.fraction, 0)).toBeCloseTo(1, 5);
    });
    it('uses zero fractions (not NaN) when there are no colleges', () => {
      const segs = balanceSegments({});
      expect(segs.every((s) => s.fraction === 0 && s.count === 0)).toBe(true);
    });
  });

  describe('balanceVerdict', () => {
    it('info when the list is empty', () => {
      expect(balanceVerdict({}).tone).toBe('info');
      expect(balanceVerdict({ reach: 0, target: 0, safety: 0 }).headline).toMatch(/no colleges/i);
    });
    it('warns hardest about a missing safety school', () => {
      const v = balanceVerdict({ reach: 3, target: 2, safety: 0 });
      expect(v.tone).toBe('warn');
      expect(v.headline).toMatch(/no safety/i);
    });
    it('warns when top-heavy (reaches outnumber target+safety)', () => {
      const v = balanceVerdict({ reach: 5, target: 1, safety: 1 });
      expect(v.tone).toBe('warn');
      expect(v.headline).toMatch(/top-heavy/i);
      expect(v.detail).toContain('5 reaches');
    });
    it('warns when there are no target schools', () => {
      const v = balanceVerdict({ reach: 1, target: 0, safety: 2 });
      expect(v.tone).toBe('warn');
      expect(v.headline).toMatch(/no target/i);
    });
    it('is happy with a spread of reach/target/safety', () => {
      const v = balanceVerdict({ reach: 3, target: 4, safety: 2 });
      expect(v.tone).toBe('good');
      expect(v.headline).toMatch(/balanced/i);
    });
  });

  describe('collegeFitCategory / isEstimatedFit (#250)', () => {
    it('prefers personalized fit (nested or top-level) over the soft category', () => {
      expect(collegeFitCategory({ fit_analysis: { fit_category: 'TARGET' }, soft_fit_category: 'REACH' })).toBe('TARGET');
      expect(collegeFitCategory({ fit_category: 'SAFETY', soft_fit_category: 'REACH' })).toBe('SAFETY');
      expect(collegeFitCategory({ soft_fit_category: 'REACH' })).toBe('REACH');
      expect(collegeFitCategory({})).toBeNull();
    });

    it('isEstimatedFit is true only when there is no personalized fit', () => {
      expect(isEstimatedFit({ soft_fit_category: 'REACH' })).toBe(true);  // soft only → estimate
      expect(isEstimatedFit({})).toBe(true);
      expect(isEstimatedFit({ fit_category: 'TARGET' })).toBe(false);
      expect(isEstimatedFit({ fit_analysis: { fit_category: 'SAFETY' } })).toBe(false);
    });
  });
});
