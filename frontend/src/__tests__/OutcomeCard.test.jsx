/**
 * OutcomeCard renders the run's outcome narrative, verdict chip, and
 * a clickable "First look at →" pointer when failures exist.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import OutcomeCard from '../components/qa/OutcomeCard';

const passingOutcome = {
    narrative: 'All 4 scenarios passed. No regressions detected.',
    verdict: 'all_pass',
    first_look_at: [],
};

const failingOutcome = {
    narrative: 'Roadmap surface looks regressed — 500 from /roadmap on senior_fall.',
    verdict: 'regression_likely',
    first_look_at: [
        {
            scenario_id: 'senior_fall_application_crunch',
            step: 'roadmap_generate',
            reason: 'status=2xx',
        },
    ],
};

describe('OutcomeCard', () => {
    it('shows narrative and the all_pass verdict', () => {
        render(<OutcomeCard outcome={passingOutcome} />);
        expect(screen.getByText(/no regressions detected/i)).toBeInTheDocument();
        expect(screen.getByText(/all[\s_]pass/i)).toBeInTheDocument();
    });

    it('shows narrative and the regression verdict for failing runs', () => {
        render(<OutcomeCard outcome={failingOutcome} />);
        expect(screen.getByText(/Roadmap surface/i)).toBeInTheDocument();
        expect(screen.getByText(/regression[\s_]likely/i)).toBeInTheDocument();
    });

    it('renders First-look-at pointer for failing runs', () => {
        render(<OutcomeCard outcome={failingOutcome} />);
        expect(screen.getByText(/senior_fall_application_crunch/i)).toBeInTheDocument();
        expect(screen.getByText(/roadmap_generate/i)).toBeInTheDocument();
    });

    it('does not render a First-look-at pointer when there are no failures', () => {
        render(<OutcomeCard outcome={passingOutcome} />);
        expect(screen.queryByText(/first look at/i)).toBeNull();
    });

    it('renders nothing when outcome is missing', () => {
        const { container } = render(<OutcomeCard outcome={null} />);
        expect(container.firstChild).toBeNull();
    });
});
