/**
 * MajorChancesView — the per-college ranked view opened from the Launchpad
 * UniversityCard (#302).
 *
 * Rules pinned here:
 *   - a saved ranking renders the four tiers as labeled sections (Strong match /
 *     Possible / Reach / Long shot), each major with entry-path / entry-risk
 *     badges, the "Stratia's read — inference" chip, and a hedged reported-rate
 *     line ONLY where the KB has one
 *   - no saved ranking → an explicit, priced CTA (1 credit)
 *   - the never-charged KB miss ({ranking: null, gaps}) renders honestly
 *   - stale chip + verification chip
 *   - no credits → CreditsUpgradeModal (no generate call); 402 → modal
 *     (server-billed; no client deduction)
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';

vi.mock('../services/api', () => ({
    getCollegeMajorChances: vi.fn(),
    rankCollegeMajors: vi.fn(),
    checkCredits: vi.fn(),
}));
vi.mock('../components/CreditsUpgradeModal', () => ({
    default: ({ isOpen }) => (isOpen ? <div data-testid="upgrade-modal" /> : null),
}));

import { getCollegeMajorChances, rankCollegeMajors, checkCredits } from '../services/api';
import MajorChancesView from '../components/majors/MajorChancesView';

const RANKING_FIXTURE = {
    university_id: 'uw',
    kb_data_year: 2025,
    verification_status: 'legacy',
    tiers: {
        strong: [{
            name: 'Computer Engineering', college: 'College of Engineering',
            entry_path: 'direct_admit', entry_risk: 'standard', tier: 'strong',
            rationale: 'Your robotics work maps well here.',
        }],
        possible: [],
        reach: [{
            name: 'Computer Science', college: 'College of Engineering',
            entry_path: 'direct_admit', entry_risk: 'capped_door', tier: 'reach',
            rationale: "A stretch — and the door locks; you can't switch in later.",
            reported_rate: { value: 7, label: 'reported (unverified)' },
        }],
        long_shot: [],
    },
    data_notes: ['Removed an unverifiable numeric claim from the ranking: "Admit is 3%."'],
};

beforeEach(() => {
    vi.clearAllMocks();
    checkCredits.mockResolvedValue({ has_credits: true, credits_remaining: 5 });
});

describe('MajorChancesView — saved ranking', () => {
    it('renders the tiers with majors and the inference chip', async () => {
        getCollegeMajorChances.mockResolvedValue({
            success: true, ranking: RANKING_FIXTURE, stale: false, current_kb_year: 2025,
        });
        render(<MajorChancesView userEmail="s@x.com" universityId="uw" universityName="UW" />);
        expect(await screen.findByTestId('tier-strong')).toHaveTextContent(/Computer Engineering/);
        expect(screen.getByTestId('tier-reach')).toHaveTextContent(/Computer Science/);
        // empty tiers are not rendered
        expect(screen.queryByTestId('tier-possible')).toBeNull();
        expect(screen.getByTestId('tier-strong')).toHaveTextContent(/Strong match/);
        expect(screen.getAllByText(/Stratia's read/i).length).toBeGreaterThan(0);
    });

    it('shows the reported rate ONLY where the KB has one', async () => {
        getCollegeMajorChances.mockResolvedValue({
            success: true, ranking: RANKING_FIXTURE, stale: false,
        });
        render(<MajorChancesView userEmail="s@x.com" universityId="uw" universityName="UW" />);
        const rate = await screen.findByTestId('chances-reported-rate');
        expect(rate).toHaveTextContent(/Reported ~7%/);
        expect(rate).toHaveTextContent(/reported \(unverified\)/);
        // only one row carries a reported rate (CS); CE has none
        expect(screen.getAllByTestId('chances-reported-rate')).toHaveLength(1);
    });

    it('flags a capped_door major with the Door locks badge', async () => {
        getCollegeMajorChances.mockResolvedValue({
            success: true, ranking: RANKING_FIXTURE, stale: false,
        });
        render(<MajorChancesView userEmail="s@x.com" universityId="uw" universityName="UW" />);
        expect(await screen.findByText('Door locks')).toBeInTheDocument();
    });

    it('shows the verification + stale chips', async () => {
        getCollegeMajorChances.mockResolvedValue({
            success: true, ranking: RANKING_FIXTURE, stale: true, current_kb_year: 2026,
        });
        render(<MajorChancesView userEmail="s@x.com" universityId="uw" universityName="UW" />);
        expect(await screen.findByTestId('chances-verification-chip')).toHaveTextContent(/Reported/);
        const stale = screen.getByTestId('chances-stale-chip');
        expect(stale).toHaveTextContent(/2025/);
        expect(stale).toHaveTextContent(/2026 available/);
    });

    it('surfaces data_notes — including validator-stripped claims', async () => {
        getCollegeMajorChances.mockResolvedValue({
            success: true, ranking: RANKING_FIXTURE, stale: false,
        });
        render(<MajorChancesView userEmail="s@x.com" universityId="uw" universityName="UW" />);
        expect(await screen.findByTestId('chances-data-notes'))
            .toHaveTextContent(/unverifiable numeric claim/);
    });
});

describe('MajorChancesView — empty state and generation', () => {
    beforeEach(() => {
        getCollegeMajorChances.mockResolvedValue({ success: true, ranking: null, stale: false });
    });

    it('shows the priced CTA when nothing is saved', async () => {
        render(<MajorChancesView userEmail="s@x.com" universityId="uw" universityName="UW" />);
        expect(await screen.findByRole('button', { name: /Rank my chances — 1 credit/i }))
            .toBeInTheDocument();
    });

    it('generates and renders the ranking', async () => {
        rankCollegeMajors.mockResolvedValue({
            success: true, ranking: RANKING_FIXTURE, gaps: [], charged: true,
        });
        render(<MajorChancesView userEmail="s@x.com" universityId="uw" universityName="UW" />);
        fireEvent.click(await screen.findByTestId('chances-generate-cta'));
        await waitFor(() => expect(rankCollegeMajors).toHaveBeenCalledWith('s@x.com', 'uw'));
        expect(await screen.findByTestId('tier-strong')).toBeInTheDocument();
    });

    it('renders the never-charged KB miss honestly', async () => {
        rankCollegeMajors.mockResolvedValue({
            success: true, ranking: null, gaps: ['Computer Science'],
        });
        render(<MajorChancesView userEmail="s@x.com" universityId="uw" universityName="UW" />);
        fireEvent.click(await screen.findByTestId('chances-generate-cta'));
        const gapNote = await screen.findByTestId('chances-gaps');
        expect(gapNote).toHaveTextContent(/you weren't charged/i);
    });

    it('no credits opens the upgrade modal without calling rank', async () => {
        checkCredits.mockResolvedValue({ has_credits: false, credits_remaining: 0 });
        render(<MajorChancesView userEmail="s@x.com" universityId="uw" universityName="UW" />);
        fireEvent.click(await screen.findByTestId('chances-generate-cta'));
        expect(await screen.findByTestId('upgrade-modal')).toBeInTheDocument();
        expect(rankCollegeMajors).not.toHaveBeenCalled();
    });

    it('a server 402 opens the upgrade modal', async () => {
        rankCollegeMajors.mockResolvedValue({
            success: false, insufficientCredits: true, creditsRemaining: 0,
        });
        render(<MajorChancesView userEmail="s@x.com" universityId="uw" universityName="UW" />);
        fireEvent.click(await screen.findByTestId('chances-generate-cta'));
        expect(await screen.findByTestId('upgrade-modal')).toBeInTheDocument();
    });
});
