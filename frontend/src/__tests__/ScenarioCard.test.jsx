/**
 * ScenarioCard renders one scenario inside a run report. Tests focus
 * on the new `business_rationale` field added in PR-I — a 1-2 sentence
 * plain-English explanation of what the scenario validates and why
 * it matters, intended to be readable to a non-engineer.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

// ScenarioCard pulls in several heavy dependencies — stub them.
vi.mock('../services/qaAgent', () => ({}));
vi.mock('../components/qa/StepRow', () => ({
    default: () => <div data-testid="step-row" />,
}));
vi.mock('../components/qa/PassFailBadge', () => ({
    default: ({ summary }) => <div data-testid="pf-badge">{summary?.pass}/{summary?.total}</div>,
}));
vi.mock('../components/qa/ReportBugButton', () => ({
    default: () => <button>Report bug</button>,
}));
vi.mock('../components/qa/SuggestCauseModal', () => ({
    default: () => null,
}));
vi.mock('../components/qa/SynthesizedBadge', () => ({
    default: () => null,
}));

import ScenarioCard from '../components/qa/ScenarioCard';

const baseScenario = {
    scenario_id: 'junior_spring_5school',
    description: 'Junior with 5-school list',
    passed: true,
    duration_ms: 1234,
    steps: [{ name: 'roadmap', passed: true, assertions: [] }],
};

describe('ScenarioCard business_rationale', () => {
    it('renders business_rationale when present (instead of plain description)', async () => {
        const user = userEvent.setup();
        const scenario = {
            ...baseScenario,
            description: 'Junior with 5-school list',
            business_rationale:
                "Validates that junior-year students still mid-college-search " +
                "get a fully personalized roadmap recognizing both reach and UC schools.",
        };
        render(<ScenarioCard runId="run_abc" scenario={scenario} />);
        // Open the card so the rationale block becomes visible.
        await user.click(screen.getByRole('button'));

        expect(
            screen.getByText(/junior-year students still mid-college-search/i)
        ).toBeInTheDocument();
        // The "Why this matters" header should appear when rationale is present.
        expect(screen.getByText(/why this matters/i)).toBeInTheDocument();
    });

    it('falls back to description when business_rationale is missing', async () => {
        const user = userEvent.setup();
        render(<ScenarioCard runId="run_abc" scenario={baseScenario} />);
        await user.click(screen.getByRole('button'));

        expect(screen.getByText(/Junior with 5-school list/i)).toBeInTheDocument();
        expect(screen.queryByText(/why this matters/i)).toBeNull();
    });

    it('header description still shows when business_rationale is present', () => {
        const scenario = {
            ...baseScenario,
            business_rationale: 'Long-form rationale',
        };
        render(<ScenarioCard runId="run_abc" scenario={scenario} />);
        // The compact header description text remains visible (not gated
        // behind the open state).
        expect(screen.getByText(/Junior with 5-school list/i)).toBeInTheDocument();
    });
});
