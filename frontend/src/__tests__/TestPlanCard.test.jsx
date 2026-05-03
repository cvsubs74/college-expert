/**
 * TestPlanCard renders the run's test_plan narrative + rationale chip
 * + per-surface coverage row at the top of the run-detail page.
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import TestPlanCard from '../components/qa/TestPlanCard';

const sampleTestPlan = {
    narrative: 'Today we re-test junior_spring_5school after yesterday\'s flake.',
    rationale: 'recently_failed',
    coverage: { profile: 1, college_list: 1, roadmap: 1 },
};

describe('TestPlanCard', () => {
    it('renders the narrative as the primary text', () => {
        render(<TestPlanCard testPlan={sampleTestPlan} />);
        expect(screen.getByText(/re-test junior_spring_5school/i)).toBeInTheDocument();
    });

    it('renders the rationale as a chip', () => {
        render(<TestPlanCard testPlan={sampleTestPlan} />);
        // Human-readable label for recently_failed rationale
        expect(screen.getByText(/recent failure|recently[\s_]failed/i)).toBeInTheDocument();
    });

    it('renders coverage by surface', () => {
        render(<TestPlanCard testPlan={sampleTestPlan} />);
        expect(screen.getByText(/profile/i)).toBeInTheDocument();
        expect(screen.getByText(/college[\s_]list/i)).toBeInTheDocument();
        expect(screen.getByText(/roadmap/i)).toBeInTheDocument();
    });

    it('renders gracefully when testPlan is missing', () => {
        const { container } = render(<TestPlanCard testPlan={null} />);
        expect(container.firstChild).toBeNull();
    });
});
