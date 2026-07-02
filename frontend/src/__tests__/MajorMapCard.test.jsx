/**
 * MajorMapCard — the Profile page's Major Map surface (#284).
 *
 * Rules pinned here:
 *   - readiness-aware empty state (CTA disabled + missing hints when the
 *     profile can't support a map)
 *   - generation is server-billed: no-credits pre-check AND a 402 result
 *     both open CreditsUpgradeModal, never a client-side deduction
 *   - generated clusters render evidence chips + relation badges + watch_out
 *   - staleness banner informs and offers regenerate — NEVER auto-regenerates
 *   - "Set as my majors" persists up to 5 selected chips via set-intended-majors
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';

vi.mock('../services/api', () => ({
    getMajorMap: vi.fn(),
    generateMajorMap: vi.fn(),
    setIntendedMajors: vi.fn(),
    checkCredits: vi.fn(),
}));
vi.mock('../components/CreditsUpgradeModal', () => ({
    default: ({ isOpen }) => (isOpen ? <div data-testid="upgrade-modal" /> : null),
}));

import { getMajorMap, generateMajorMap, setIntendedMajors, checkCredits } from '../services/api';
import MajorMapCard from '../components/majors/MajorMapCard';

const READY_PROFILE = {
    grade: '11',
    gpa_weighted: 4.2,
    courses: [{ name: 'AP Computer Science A' }],
    extracurriculars: [{ name: 'Robotics Club' }],
};

const MAP_FIXTURE = {
    clusters: [
        {
            theme: 'Building intelligent systems',
            why_you: 'AP CS A and Robotics captaincy show sustained making.',
            evidence: ['AP Computer Science A', 'Robotics Club'],
            majors: [
                { name: 'Computer Science', relation: 'core', why: 'the direct door', watch_out: 'capped at many public flagships' },
                { name: 'Computer Engineering', relation: 'adjacent', why: 'hardware too', watch_out: '' },
                { name: 'Data Science', relation: 'strategic_alternative', why: 'another door', watch_out: '' },
            ],
        },
    ],
    questions_to_explore: ['Do you prefer building or analyzing?'],
    generated_at: '2026-07-01T00:00:00',
    basis: 'inference',
};

beforeEach(() => {
    vi.clearAllMocks();
    checkCredits.mockResolvedValue({ has_credits: true, credits_remaining: 5 });
});

describe('MajorMapCard — empty state', () => {
    it('shows the readiness-aware pitch and priced CTA when ready', async () => {
        getMajorMap.mockResolvedValue({ success: true, map: null, stale: false, stale_reasons: [] });
        render(<MajorMapCard userEmail="s@x.com" profile={READY_PROFILE} />);
        expect(await screen.findByText(/turn that into a map of majors/i)).toBeInTheDocument();
        const cta = screen.getByRole('button', { name: /Map my majors — 1 credit/i });
        expect(cta).toBeEnabled();
    });

    it('disables the CTA and names what is missing when the profile is thin', async () => {
        getMajorMap.mockResolvedValue({ success: true, map: null, stale: false, stale_reasons: [] });
        render(<MajorMapCard userEmail="s@x.com" profile={{ grade: '11' }} />);
        expect(await screen.findByTestId('map-missing')).toHaveTextContent(/your courses/);
        expect(screen.getByRole('button', { name: /Map my majors/i })).toBeDisabled();
        expect(generateMajorMap).not.toHaveBeenCalled();
    });

    it('opens the upgrade modal instead of generating when credits are gone', async () => {
        getMajorMap.mockResolvedValue({ success: true, map: null, stale: false, stale_reasons: [] });
        checkCredits.mockResolvedValue({ has_credits: false, credits_remaining: 0 });
        render(<MajorMapCard userEmail="s@x.com" profile={READY_PROFILE} />);
        fireEvent.click(await screen.findByRole('button', { name: /Map my majors/i }));
        expect(await screen.findByTestId('upgrade-modal')).toBeInTheDocument();
        expect(generateMajorMap).not.toHaveBeenCalled();
    });

    it('a server 402 also opens the upgrade modal (no client deduction anywhere)', async () => {
        getMajorMap.mockResolvedValue({ success: true, map: null, stale: false, stale_reasons: [] });
        generateMajorMap.mockResolvedValue({
            success: false, insufficientCredits: true, creditsRemaining: 0,
        });
        render(<MajorMapCard userEmail="s@x.com" profile={READY_PROFILE} />);
        fireEvent.click(await screen.findByRole('button', { name: /Map my majors/i }));
        expect(await screen.findByTestId('upgrade-modal')).toBeInTheDocument();
    });

    it('a server 422 surfaces the missing list', async () => {
        getMajorMap.mockResolvedValue({ success: true, map: null, stale: false, stale_reasons: [] });
        generateMajorMap.mockResolvedValue({
            success: false, profileIncomplete: true, missing: ['gpa'],
        });
        render(<MajorMapCard userEmail="s@x.com" profile={READY_PROFILE} />);
        fireEvent.click(await screen.findByRole('button', { name: /Map my majors/i }));
        expect(await screen.findByTestId('map-missing')).toHaveTextContent(/GPA/i);
    });
});

describe('MajorMapCard — generated state', () => {
    beforeEach(() => {
        getMajorMap.mockResolvedValue({ success: true, map: MAP_FIXTURE, stale: false, stale_reasons: [] });
    });

    it('renders theme, evidence chips, relation badges, and the inference chip', async () => {
        render(<MajorMapCard userEmail="s@x.com" profile={READY_PROFILE} />);
        expect(await screen.findByText('Building intelligent systems')).toBeInTheDocument();
        const chips = screen.getAllByTestId('evidence-chip');
        expect(chips.map(c => c.textContent)).toEqual(['AP Computer Science A', 'Robotics Club']);
        expect(screen.getByText('Core')).toBeInTheDocument();
        expect(screen.getByText('Adjacent')).toBeInTheDocument();
        expect(screen.getByText('Strategic alternative')).toBeInTheDocument();
        expect(screen.getByText(/inference, not school facts/i)).toBeInTheDocument();
    });

    it('watch_out lives in an expander, not inline', async () => {
        render(<MajorMapCard userEmail="s@x.com" profile={READY_PROFILE} />);
        await screen.findByText('Building intelligent systems');
        expect(screen.getByText('capped at many public flagships')).toBeInTheDocument();
        // Inside a <details> so it's collapsed by default.
        expect(screen.getByText('capped at many public flagships').closest('details')).not.toBeNull();
    });

    it('selecting chips and clicking Set as my majors persists via set-intended-majors', async () => {
        setIntendedMajors.mockResolvedValue({
            success: true,
            intended_majors: ['Computer Science', 'Data Science'],
            intended_major: 'Computer Science',
        });
        render(<MajorMapCard userEmail="s@x.com" profile={READY_PROFILE} />);
        await screen.findByText('Building intelligent systems');

        fireEvent.click(screen.getByRole('button', { name: 'Select Computer Science' }));
        fireEvent.click(screen.getByRole('button', { name: 'Select Data Science' }));
        fireEvent.click(screen.getByRole('button', { name: /Set as my majors \(2\)/i }));

        await waitFor(() => expect(setIntendedMajors).toHaveBeenCalledWith(
            's@x.com', ['Computer Science', 'Data Science']));
        expect(await screen.findByTestId('majors-saved-note')).toHaveTextContent(/Computer Science/);
    });

    it('the action button is disabled with no selection', async () => {
        render(<MajorMapCard userEmail="s@x.com" profile={READY_PROFILE} />);
        await screen.findByText('Building intelligent systems');
        expect(screen.getByRole('button', { name: /Set as my majors/i })).toBeDisabled();
    });
});

describe('MajorMapCard — staleness', () => {
    it('shows the profile-change banner + reasons; never auto-regenerates (#311)', async () => {
        getMajorMap.mockResolvedValue({
            success: true, map: MAP_FIXTURE, stale: true,
            stale_reasons: ['courses changed since this map was generated'],
        });
        render(<MajorMapCard userEmail="s@x.com" profile={READY_PROFILE} />);
        const banner = await screen.findByTestId('map-stale-banner');
        expect(banner).toHaveTextContent(/Your profile changed since this map — regenerate to refresh it/);
        expect(banner).toHaveTextContent(/courses changed/);
        // No generation happened just from rendering the stale state.
        expect(generateMajorMap).not.toHaveBeenCalled();
    });

    it('regenerate passes force=true', async () => {
        getMajorMap.mockResolvedValue({
            success: true, map: MAP_FIXTURE, stale: true, stale_reasons: [],
        });
        generateMajorMap.mockResolvedValue({ success: true, map: MAP_FIXTURE });
        render(<MajorMapCard userEmail="s@x.com" profile={READY_PROFILE} />);
        fireEvent.click(await screen.findByRole('button', { name: /Regenerate — 1 credit/i }));
        await waitFor(() => expect(generateMajorMap).toHaveBeenCalledWith('s@x.com', true));
    });
});

describe('MajorMapCard — #311 regenerate always available, banner only on profile change', () => {
    beforeEach(() => { vi.clearAllMocks(); });

    it('shows a Regenerate control when a map exists even if NOT stale (no false banner)', async () => {
        getMajorMap.mockResolvedValue({ success: true, map: MAP_FIXTURE, stale: false, stale_reasons: [] });
        render(<MajorMapCard userEmail="s@x.com" profile={READY_PROFILE} />);
        // regenerate is available (header)…
        expect(await screen.findByTestId('map-regenerate')).toBeInTheDocument();
        // …and NO stale/profile-changed banner is shown.
        expect(screen.queryByTestId('map-stale-banner')).not.toBeInTheDocument();
    });

    it('header regenerate passes force=true', async () => {
        getMajorMap.mockResolvedValue({ success: true, map: MAP_FIXTURE, stale: false, stale_reasons: [] });
        generateMajorMap.mockResolvedValue({ success: true, map: MAP_FIXTURE });
        render(<MajorMapCard userEmail="s@x.com" profile={READY_PROFILE} />);
        fireEvent.click(await screen.findByTestId('map-regenerate'));
        await waitFor(() => expect(generateMajorMap).toHaveBeenCalledWith('s@x.com', true));
    });
});
