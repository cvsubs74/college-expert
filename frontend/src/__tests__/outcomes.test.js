import { describe, it, expect } from 'vitest';
import {
  normalizeDecision, decisionMeta, predictedBand, calibrationOutcome, calibrationSummary,
} from '../utils/outcomes';

describe('outcomes (Decision Ledger)', () => {
  describe('normalizeDecision', () => {
    it('canonicalizes synonyms and casing', () => {
      expect(normalizeDecision('Admitted')).toBe('accepted');
      expect(normalizeDecision('REJECTED')).toBe('denied');
      expect(normalizeDecision('wait-listed')).toBe('waitlisted');
      expect(normalizeDecision('Enrolled')).toBe('enrolled');
    });
    it('returns null for empty/unknown', () => {
      expect(normalizeDecision('')).toBeNull();
      expect(normalizeDecision(null)).toBeNull();
      expect(normalizeDecision('maybe')).toBeNull();
    });
  });

  it('decisionMeta gives a label/tone for known decisions, null otherwise', () => {
    expect(decisionMeta('accepted').label).toBe('Accepted');
    expect(decisionMeta('admitted').key).toBe('accepted');
    expect(decisionMeta('')).toBeNull();
  });

  it('predictedBand folds SUPER_REACH into Reach', () => {
    expect(predictedBand('SUPER_REACH')).toBe('Reach');
    expect(predictedBand('reach')).toBe('Reach');
    expect(predictedBand('TARGET')).toBe('Target');
    expect(predictedBand('SAFETY')).toBe('Safety');
    expect(predictedBand(null)).toBeNull();
  });

  describe('calibrationOutcome', () => {
    it('targets/safeties: admit=match, deny=miss', () => {
      expect(calibrationOutcome('TARGET', 'accepted')).toBe('match');
      expect(calibrationOutcome('SAFETY', 'enrolled')).toBe('match');
      expect(calibrationOutcome('TARGET', 'denied')).toBe('miss');
    });
    it('reaches: deny=match (behaved like a reach), admit=beat', () => {
      expect(calibrationOutcome('REACH', 'denied')).toBe('match');
      expect(calibrationOutcome('SUPER_REACH', 'accepted')).toBe('beat');
    });
    it('waitlist/deferred/unknown are neutral', () => {
      expect(calibrationOutcome('TARGET', 'waitlisted')).toBe('neutral');
      expect(calibrationOutcome('REACH', 'deferred')).toBe('neutral');
      expect(calibrationOutcome(null, 'accepted')).toBe('neutral');
    });
  });

  describe('calibrationSummary', () => {
    it('is not ready below the minimum decided count', () => {
      const s = calibrationSummary([
        { predicted: 'TARGET', decision: 'accepted' },
        { predicted: 'REACH', decision: 'denied' },
      ]);
      expect(s.ready).toBe(false);
      expect(s.decided).toBe(2);
      expect(s.headline).toBeNull();
    });

    it('grades calls once >=3 decisions are in, surfacing beats separately', () => {
      const s = calibrationSummary([
        { predicted: 'TARGET', decision: 'accepted' },  // match
        { predicted: 'SAFETY', decision: 'accepted' },  // match
        { predicted: 'REACH', decision: 'denied' },     // match
        { predicted: 'SUPER_REACH', decision: 'accepted' }, // beat (not scored)
        { predicted: 'TARGET', decision: 'waitlisted' },    // neutral
      ]);
      expect(s.ready).toBe(true);
      expect(s.match).toBe(3);
      expect(s.miss).toBe(0);
      expect(s.beat).toBe(1);
      expect(s.scored).toBe(3);
      expect(s.headline).toMatch(/3 of 3 right/);
      expect(s.headline).toMatch(/beat the odds on 1/);
    });

    it('does not overclaim when only beats/neutrals are in (scored == 0)', () => {
      const s = calibrationSummary([
        { predicted: 'SUPER_REACH', decision: 'accepted' }, // beat
        { predicted: 'REACH', decision: 'accepted' },        // beat
        { predicted: 'TARGET', decision: 'waitlisted' },     // neutral
      ]);
      expect(s.ready).toBe(true);
      expect(s.scored).toBe(0);
      expect(s.headline).toMatch(/beat the odds on 2/);
      expect(s.headline).not.toMatch(/of 0 right/);
    });

    it('only counts decisions that normalize (ignores blanks/unknowns)', () => {
      const s = calibrationSummary([
        { predicted: 'TARGET', decision: 'accepted' },
        { predicted: 'TARGET', decision: '' },
        { predicted: 'TARGET', decision: 'maybe' },
      ]);
      expect(s.decided).toBe(1);
      expect(s.ready).toBe(false);
    });
  });
});
