/**
 * ResolvedIssuesCard renders FAIL → PASS transitions returned by
 * /summary's `resolved_issues` block.
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import ResolvedIssuesCard from '../components/qa/ResolvedIssuesCard';

describe('ResolvedIssuesCard', () => {
    const sample = {
        total_fixes: 2,
        lookback_runs: 30,
        fixes: [
            {
                scenario_id: 'synth_high_achiever_junior_all_ucs',
                step_name: 'roadmap_generate',
                failing_message: "metadata.template_used=='junior_fall': got 'sophomore_spring'",
                failed_at_run: 'run_20260504T010246Z_bdba3a',
                fixed_at_run: 'run_20260504T011634Z_46140b',
                fixed_at_time: '2026-05-04T01:16:34+00:00',
            },
            {
                scenario_id: 'freshman_fall_starter',
                step_name: 'roadmap_generate',
                failing_message: "got 'freshman_spring'",
                failed_at_run: 'run_old',
                fixed_at_run: 'run_new',
                fixed_at_time: '2026-05-03T22:00:00+00:00',
            },
        ],
    };

    it('renders one row per fix with scenario/step + failing message', () => {
        render(<ResolvedIssuesCard resolvedIssues={sample} />);
        // Both fixes appear.
        expect(
            screen.getByText(/synth_high_achiever_junior_all_ucs/i)
        ).toBeInTheDocument();
        expect(screen.getByText(/freshman_fall_starter/i)).toBeInTheDocument();
        // Step name shown.
        expect(screen.getAllByText(/roadmap_generate/i).length).toBeGreaterThan(0);
        // Failing message preserved as evidence.
        expect(
            screen.getByText(/junior_fall.*sophomore_spring/i)
        ).toBeInTheDocument();
    });

    it('shows total fixes + lookback in the header', () => {
        render(<ResolvedIssuesCard resolvedIssues={sample} />);
        expect(screen.getByText(/2 fixes/i)).toBeInTheDocument();
        expect(screen.getByText(/30 runs/i)).toBeInTheDocument();
    });

    it("shows singular 'fix' when there's exactly one", () => {
        render(
            <ResolvedIssuesCard
                resolvedIssues={{
                    total_fixes: 1,
                    lookback_runs: 5,
                    fixes: [sample.fixes[0]],
                }}
            />
        );
        expect(screen.getByText(/^1 fix across last 5 runs$/)).toBeInTheDocument();
    });

    it('mentions the failed_at and fixed_at run IDs', () => {
        render(<ResolvedIssuesCard resolvedIssues={sample} />);
        expect(screen.getByText(/run_20260504T010246Z_bdba3a/)).toBeInTheDocument();
        expect(screen.getByText(/run_20260504T011634Z_46140b/)).toBeInTheDocument();
    });

    it('renders nothing when fixes is empty', () => {
        const { container } = render(
            <ResolvedIssuesCard
                resolvedIssues={{ total_fixes: 0, lookback_runs: 30, fixes: [] }}
            />
        );
        expect(container.firstChild).toBeNull();
    });

    it('renders nothing when resolvedIssues is missing', () => {
        const { container } = render(<ResolvedIssuesCard />);
        expect(container.firstChild).toBeNull();
    });

    it('shows truncation hint when total_fixes exceeds rendered fixes', () => {
        render(
            <ResolvedIssuesCard
                resolvedIssues={{
                    total_fixes: 15,
                    lookback_runs: 30,
                    fixes: sample.fixes,  // only 2 rendered
                }}
            />
        );
        expect(screen.getByText(/13 more/i)).toBeInTheDocument();
    });
});
