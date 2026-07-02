/**
 * MajorStrategySynthesis — the strategy layer under the Majors tab facts
 * panel (#284).
 *
 * Rules pinned here:
 *   - a saved strategy renders every synthesis section labeled "Stratia's
 *     read" (inference), the ESSAY IMPLICATION block, the verify-yourself
 *     checklist, and data_notes (incl. validator-stripped claims)
 *   - no saved strategy → an explicit, priced CTA (1 credit)
 *   - the never-charged KB miss ({strategy: null, gaps}) renders honestly
 *   - stale chip when the KB has newer data than the strategy was built on
 *   - 402 → CreditsUpgradeModal (server-billed; no client deduction)
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';

vi.mock('../services/api', () => ({
    getMajorStrategy: vi.fn(),
    generateMajorStrategy: vi.fn(),
    checkCredits: vi.fn(),
}));
vi.mock('../components/CreditsUpgradeModal', () => ({
    default: ({ isOpen }) => (isOpen ? <div data-testid="upgrade-modal" /> : null),
}));

import { getMajorStrategy, generateMajorStrategy, checkCredits } from '../services/api';
import MajorStrategySynthesis from '../components/majors/MajorStrategySynthesis';

const STRATEGY_FIXTURE = {
    university_id: 'uw',
    kb_data_year: 2025,
    synthesis: {
        primary_call: "My read: list Computer Science and mean it. Heads up: the door locks — you can't switch in later.",
        second_choice_play: 'A second choice inside engineering keeps the file coherent.',
        backup_rationale: 'Computer Engineering is the on-campus backup worth naming.',
        undeclared_tactic: 'Undeclared is not a real path into this college.',
        essay_implication: 'Your essays must argue the CS story specifically.',
        what_to_verify_yourself: ['Confirm the direct-admit policy on the official CS page.'],
    },
    data_notes: ['Removed an unverifiable numeric claim from the synthesis: "Admit rate is 4%."'],
};

beforeEach(() => {
    vi.clearAllMocks();
    checkCredits.mockResolvedValue({ has_credits: true, credits_remaining: 5 });
});

describe('MajorStrategySynthesis — saved strategy', () => {
    it('renders every synthesis section with the inference chip', async () => {
        getMajorStrategy.mockResolvedValue({
            success: true, strategy: STRATEGY_FIXTURE, stale: false, current_kb_year: 2025,
        });
        render(<MajorStrategySynthesis userEmail="s@x.com" universityId="uw" />);
        expect(await screen.findByTestId('section-primary_call')).toHaveTextContent(/list Computer Science/);
        expect(screen.getByTestId('section-second_choice_play')).toBeInTheDocument();
        expect(screen.getByTestId('section-backup_rationale')).toBeInTheDocument();
        expect(screen.getByTestId('section-undeclared_tactic')).toBeInTheDocument();
        expect(screen.getByText("Stratia's read")).toBeInTheDocument();
    });

    it('emphasizes ESSAY IMPLICATION and lists the verify-yourself checklist', async () => {
        getMajorStrategy.mockResolvedValue({
            success: true, strategy: STRATEGY_FIXTURE, stale: false,
        });
        render(<MajorStrategySynthesis userEmail="s@x.com" universityId="uw" />);
        expect(await screen.findByTestId('section-essay_implication'))
            .toHaveTextContent(/argue the CS story/);
        expect(screen.getByTestId('section-verify'))
            .toHaveTextContent(/Confirm the direct-admit policy/);
    });

    it('surfaces data_notes — including validator-stripped claims', async () => {
        getMajorStrategy.mockResolvedValue({
            success: true, strategy: STRATEGY_FIXTURE, stale: false,
        });
        render(<MajorStrategySynthesis userEmail="s@x.com" universityId="uw" />);
        expect(await screen.findByTestId('strategy-data-notes'))
            .toHaveTextContent(/unverifiable numeric claim/);
    });

    it('shows the stale chip when the KB has newer data', async () => {
        getMajorStrategy.mockResolvedValue({
            success: true, strategy: STRATEGY_FIXTURE, stale: true, current_kb_year: 2026,
        });
        render(<MajorStrategySynthesis userEmail="s@x.com" universityId="uw" />);
        const chip = await screen.findByTestId('strategy-stale-chip');
        expect(chip).toHaveTextContent(/2025/);
        expect(chip).toHaveTextContent(/2026 available/);
    });

    it('no stale chip when current', async () => {
        getMajorStrategy.mockResolvedValue({
            success: true, strategy: STRATEGY_FIXTURE, stale: false,
        });
        render(<MajorStrategySynthesis userEmail="s@x.com" universityId="uw" />);
        await screen.findByTestId('section-primary_call');
        expect(screen.queryByTestId('strategy-stale-chip')).toBeNull();
    });
});

describe('MajorStrategySynthesis — empty state and generation', () => {
    beforeEach(() => {
        getMajorStrategy.mockResolvedValue({ success: true, strategy: null, stale: false });
    });

    it('shows the priced CTA when nothing is saved', async () => {
        render(<MajorStrategySynthesis userEmail="s@x.com" universityId="uw" />);
        expect(await screen.findByRole('button', { name: /Generate strategy — 1 credit/i }))
            .toBeInTheDocument();
    });

    it('generates and renders the strategy', async () => {
        generateMajorStrategy.mockResolvedValue({
            success: true, strategy: STRATEGY_FIXTURE, gaps: [], charged: true,
        });
        render(<MajorStrategySynthesis userEmail="s@x.com" universityId="uw" />);
        fireEvent.click(await screen.findByRole('button', { name: /Generate strategy/i }));
        await waitFor(() => expect(generateMajorStrategy).toHaveBeenCalledWith('s@x.com', 'uw'));
        expect(await screen.findByTestId('section-primary_call')).toBeInTheDocument();
    });

    it('renders the never-charged KB miss honestly', async () => {
        generateMajorStrategy.mockResolvedValue({
            success: true, strategy: null, gaps: ['Underwater Basket Weaving'],
        });
        render(<MajorStrategySynthesis userEmail="s@x.com" universityId="uw" />);
        fireEvent.click(await screen.findByRole('button', { name: /Generate strategy/i }));
        const gapNote = await screen.findByTestId('strategy-gaps');
        expect(gapNote).toHaveTextContent(/Underwater Basket Weaving/);
        expect(gapNote).toHaveTextContent(/you weren't charged/i);
    });

    it('no credits opens the upgrade modal without calling generate', async () => {
        checkCredits.mockResolvedValue({ has_credits: false, credits_remaining: 0 });
        render(<MajorStrategySynthesis userEmail="s@x.com" universityId="uw" />);
        fireEvent.click(await screen.findByRole('button', { name: /Generate strategy/i }));
        expect(await screen.findByTestId('upgrade-modal')).toBeInTheDocument();
        expect(generateMajorStrategy).not.toHaveBeenCalled();
    });

    it('a server 402 opens the upgrade modal', async () => {
        generateMajorStrategy.mockResolvedValue({
            success: false, insufficientCredits: true, creditsRemaining: 0,
        });
        render(<MajorStrategySynthesis userEmail="s@x.com" universityId="uw" />);
        fireEvent.click(await screen.findByRole('button', { name: /Generate strategy/i }));
        expect(await screen.findByTestId('upgrade-modal')).toBeInTheDocument();
    });
});
