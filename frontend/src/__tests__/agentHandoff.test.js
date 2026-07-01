import { describe, it, expect } from 'vitest';
import {
  universityAgentPrompt,
  fitAgentPrompt,
  counselorAgentPrompt,
  essayAgentPrompt,
} from '../utils/agentHandoff';

describe('agentHandoff prompt builders', () => {
  describe('universityAgentPrompt', () => {
    it('uses the current question when present', () => {
      const p = universityAgentPrompt('Princeton University', "What's the acceptance rate?");
      expect(p).toBe("Using the Stratia tools, tell me about Princeton University: What's the acceptance rate?");
    });
    it('falls back to key facts with no question', () => {
      const p = universityAgentPrompt('Princeton University', '');
      expect(p).toMatch(/tell me about Princeton University/);
      expect(p).toMatch(/acceptance rate, popular majors, and campus life/);
    });
    it('handles a missing university name', () => {
      expect(universityAgentPrompt('', '')).toContain('this university');
    });
  });

  describe('fitAgentPrompt', () => {
    it('weaves in fit category and intended major', () => {
      const p = fitAgentPrompt('MIT', { fitCategory: 'REACH', intendedMajor: 'CS', question: 'My chances?' });
      expect(p).toContain('my fit analysis for MIT');
      expect(p).toContain('my intended major is CS');
      expect(p).toContain("it's a reach school for me");
      expect(p).toContain('answer: My chances?');
    });
    it('maps SUPER_REACH to "high reach"', () => {
      expect(fitAgentPrompt('MIT', { fitCategory: 'SUPER_REACH' })).toContain('high reach school');
    });
    it('omits the context clause when no fit/major given, and uses a default ask', () => {
      const p = fitAgentPrompt('MIT', {});
      expect(p).toBe('Using my Stratia profile and my fit analysis for MIT, tell me my admission chances and the biggest gaps I should close.');
    });
  });

  describe('counselorAgentPrompt', () => {
    it('prefers the question', () => {
      expect(counselorAgentPrompt('Fall Plan', 'What is due this week?'))
        .toBe('Using my Stratia roadmap, profile, deadlines and college list, help me: What is due this week?');
    });
    it('uses the roadmap title when there is no question', () => {
      expect(counselorAgentPrompt('Fall Plan', '')).toContain('make progress on "Fall Plan"');
    });
    it('has a sensible default with neither', () => {
      expect(counselorAgentPrompt('', '')).toContain('most important next steps');
    });
  });

  describe('essayAgentPrompt', () => {
    it('includes prompt, draft, and question', () => {
      const p = essayAgentPrompt('Stanford', {
        promptText: 'Why us?',
        currentText: 'Draft one.',
        question: 'Is my hook strong?',
      });
      expect(p).toContain('this Stanford essay prompt: "Why us?"');
      expect(p).toContain('my draft so far: "Draft one."');
      expect(p).toContain('Is my hook strong?');
    });
    it('omits the draft clause when empty and uses a default ask', () => {
      const p = essayAgentPrompt('Stanford', { promptText: 'Why us?' });
      expect(p).not.toMatch(/draft so far/);
      expect(p).toMatch(/specific, personal feedback/);
    });
  });
});
