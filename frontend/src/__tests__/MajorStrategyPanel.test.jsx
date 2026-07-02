/**
 * MajorStrategyPanel — the facts-only Majors tab (#283).
 *
 * The panel's whole job is honest rendering of the KB's trust-labeled major
 * extract, so these tests pin the trust rules themselves:
 *   - verified vs legacy verification chips
 *   - entry-path badges; 'unclear' gets NO badge, the verbatim quote instead
 *   - capped_door amber callout with the school's own wording
 *   - is_impacted:false NEVER rendered as safe; chip only when value===true
 *   - hedged "Reported ~X% (unverified)" and explicit not-published sentences
 *   - data_notes footer + counselor-take labeling
 *   - loading / error / retry states and the client-side filter
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';

vi.mock('../services/api', () => ({
    getUniversityMajors: vi.fn(),
}));
import { getUniversityMajors } from '../services/api';
import MajorStrategyPanel from '../components/majors/MajorStrategyPanel';

const LEGACY_FIXTURE = {
    success: true,
    university_id: 'university_of_washington',
    official_name: 'University of Washington',
    data_year: 2026,
    verification_status: 'legacy',
    richness_tier: 2,
    structure_type: 'colleges',
    colleges: [
        {
            name: 'College of Engineering',
            admissions_model: 'Direct to College',
            is_restricted_or_capped: true,
            acceptance_rate_estimate: { value: '25%', basis: 'kb_reported' },
            strategic_fit_advice: { text: 'Apply directly if engineering is the goal.', basis: 'opinion' },
            majors: [
                {
                    // The UIUC trap shape: capped door, is_impacted false —
                    // must NEVER read as "not competitive".
                    name: 'Computer Science',
                    degree_type: 'BS',
                    entry_path: { value: 'direct_admit', raw: 'Admission to the CS major is by direct admission only.', basis: 'kb_reported' },
                    entry_risk: 'capped_door',
                    is_impacted: { value: false, basis: 'kb_reported', note: null },
                    door_policy: { direct_admit_only: true, internal_transfer_allowed: false, internal_transfer_gpa: null, basis: 'kb_reported' },
                    prerequisite_courses: [],
                    special_requirements: null,
                    reported_stats: { acceptance_rate: 7, basis: 'kb_reported' },
                },
                {
                    // 'unclear' bucket: no badge, verbatim wording in quotes.
                    name: 'Bioengineering',
                    degree_type: 'BS',
                    entry_path: { value: 'unclear', raw: 'Admission by holistic faculty review after the first year.', basis: null },
                    entry_risk: 'unknown',
                    is_impacted: { value: null, basis: null, note: null },
                    door_policy: { direct_admit_only: null, internal_transfer_allowed: null, internal_transfer_gpa: null, basis: 'kb_reported' },
                    prerequisite_courses: [],
                    special_requirements: null,
                    reported_stats: null,
                },
                {
                    // Officially impacted + elevated risk + transfer GPA bar.
                    name: 'Mechanical Engineering',
                    degree_type: 'BS',
                    entry_path: { value: 'pre_major', raw: 'Pre-engineering, then apply to the major.', basis: 'kb_reported' },
                    entry_risk: 'elevated',
                    is_impacted: { value: true, basis: 'kb_reported', note: null },
                    door_policy: { direct_admit_only: false, internal_transfer_allowed: true, internal_transfer_gpa: 3.5, basis: 'kb_reported' },
                    prerequisite_courses: [],
                    special_requirements: null,
                    reported_stats: null,
                },
            ],
        },
    ],
    strategy_notes: {
        major_selection_tactics: { items: ['Lead with the college choice, not the major name.'], basis: 'opinion' },
        alternate_major_strategy: { text: null, basis: 'opinion' },
    },
    data_notes: ['Numeric per-major stats here are unverified legacy research.'],
};

beforeEach(() => {
    getUniversityMajors.mockReset();
});

const renderPanel = () =>
    render(<MajorStrategyPanel universityId="university_of_washington" universityName="University of Washington" />);

describe('MajorStrategyPanel — states', () => {
    it('shows a loading skeleton while fetching', () => {
        getUniversityMajors.mockReturnValue(new Promise(() => {})); // never resolves
        renderPanel();
        expect(screen.getByTestId('majors-loading')).toBeInTheDocument();
    });

    it('shows an error state with a working retry', async () => {
        getUniversityMajors
            .mockResolvedValueOnce({ success: false, error: 'kb unreachable' })
            .mockResolvedValueOnce(LEGACY_FIXTURE);
        renderPanel();

        expect(await screen.findByText(/couldn't load major facts/i)).toBeInTheDocument();
        expect(screen.getByText('kb unreachable')).toBeInTheDocument();

        fireEvent.click(screen.getByRole('button', { name: /try again/i }));
        expect(await screen.findByText('Computer Science')).toBeInTheDocument();
        expect(getUniversityMajors).toHaveBeenCalledTimes(2);
    });

    it('renders the empty message when no majors are stored', async () => {
        getUniversityMajors.mockResolvedValue({ ...LEGACY_FIXTURE, colleges: [], data_notes: [] });
        renderPanel();
        expect(await screen.findByText(/no majors are stored for this school yet/i)).toBeInTheDocument();
    });
});

describe('MajorStrategyPanel — trust rendering', () => {
    it('legacy data gets the outline "Reported — not yet verified" chip and explainer', async () => {
        getUniversityMajors.mockResolvedValue(LEGACY_FIXTURE);
        renderPanel();
        expect(await screen.findByText('Reported — not yet verified')).toBeInTheDocument();
        expect(screen.getByText(/not yet checked against the school's official publications/i)).toBeInTheDocument();
        expect(screen.queryByText('From official publications')).toBeNull();
    });

    it('verified data gets the green "From official publications" chip', async () => {
        getUniversityMajors.mockResolvedValue({ ...LEGACY_FIXTURE, verification_status: 'verified' });
        renderPanel();
        expect(await screen.findByText('From official publications')).toBeInTheDocument();
        expect(screen.queryByText('Reported — not yet verified')).toBeNull();
    });

    it('renders college name, admissions model badge, capped chip and counselor take', async () => {
        getUniversityMajors.mockResolvedValue(LEGACY_FIXTURE);
        renderPanel();
        expect(await screen.findByText('College of Engineering')).toBeInTheDocument();
        expect(screen.getByText('Direct to College')).toBeInTheDocument();
        expect(screen.getByText('Capped')).toBeInTheDocument();
        expect(screen.getByText('Apply directly if engineering is the goal.')).toBeInTheDocument();
        // Opinion content is labeled: college advice + footer tactics section.
        expect(screen.getAllByText('Counselor take').length).toBeGreaterThanOrEqual(2);
    });

    it('shows entry-path badges, but NO badge for unclear — verbatim quote instead', async () => {
        getUniversityMajors.mockResolvedValue(LEGACY_FIXTURE);
        renderPanel();
        expect(await screen.findByText('Direct admit')).toBeInTheDocument();
        expect(screen.getByText('Pre-major')).toBeInTheDocument();
        // Bioengineering is 'unclear': its verbatim wording renders in quotes.
        expect(screen.getByText(/"Admission by holistic faculty review after the first year\."/)).toBeInTheDocument();
        expect(screen.queryByText('Unclear')).toBeNull();
    });

    it('renders the capped-door callout with the school\'s own wording', async () => {
        getUniversityMajors.mockResolvedValue(LEGACY_FIXTURE);
        renderPanel();
        expect(await screen.findByText(/if you're not admitted to this major directly, you can't switch in later/i)).toBeInTheDocument();
        expect(screen.getByText(/school's own wording/i)).toBeInTheDocument();
        expect(screen.getByText(/"Admission to the CS major is by direct admission only\."/)).toBeInTheDocument();
    });

    it('never renders is_impacted:false as safe — chip only for value===true', async () => {
        getUniversityMajors.mockResolvedValue(LEGACY_FIXTURE);
        renderPanel();
        await screen.findByText('Computer Science');
        // Exactly one chip: Mechanical Engineering (value === true). CS is
        // false and Bioengineering null — neither may render impact wording.
        expect(screen.getAllByText('Officially impacted')).toHaveLength(1);
        expect(screen.queryByText(/not impacted/i)).toBeNull();
        expect(screen.queryByText(/not competitive/i)).toBeNull();
    });

    it('renders elevated risk as a small amber chip and the door-policy line', async () => {
        getUniversityMajors.mockResolvedValue(LEGACY_FIXTURE);
        renderPanel();
        expect(await screen.findByText('Elevated entry risk')).toBeInTheDocument();
        expect(screen.getByText(/internal transfer allowed \(GPA ≥ 3\.5\)/i)).toBeInTheDocument();
        expect(screen.getByText(/direct admit only · internal transfer not allowed/i)).toBeInTheDocument();
    });

    it('hedges reported stats and states not-published explicitly — never blank', async () => {
        getUniversityMajors.mockResolvedValue(LEGACY_FIXTURE);
        renderPanel();
        expect(await screen.findByText('Reported ~7% (unverified)')).toBeInTheDocument();
        // Bioengineering + Mechanical have no reported admit rate.
        expect(screen.getAllByText('No per-major admit rate published.')).toHaveLength(2);
        // College-level estimate is hedged too.
        expect(screen.getByText(/reported acceptance estimate: 25% \(unverified\)/i)).toBeInTheDocument();
    });

    it('renders data notes and counselor tactics in the footer', async () => {
        getUniversityMajors.mockResolvedValue(LEGACY_FIXTURE);
        renderPanel();
        expect(await screen.findByText('Numeric per-major stats here are unverified legacy research.')).toBeInTheDocument();
        expect(screen.getByText('Major selection tactics')).toBeInTheDocument();
        expect(screen.getByText('Lead with the college choice, not the major name.')).toBeInTheDocument();
    });
});

describe('MajorStrategyPanel — filter', () => {
    it('filters majors client-side by name', async () => {
        getUniversityMajors.mockResolvedValue(LEGACY_FIXTURE);
        renderPanel();
        await screen.findByText('Computer Science');

        fireEvent.change(screen.getByLabelText(/filter majors/i), { target: { value: 'bio' } });
        expect(screen.getByText('Bioengineering')).toBeInTheDocument();
        expect(screen.queryByText('Computer Science')).toBeNull();
        expect(screen.queryByText('Mechanical Engineering')).toBeNull();

        fireEvent.change(screen.getByLabelText(/filter majors/i), { target: { value: 'zzz' } });
        expect(screen.getByText(/no majors match "zzz"/i)).toBeInTheDocument();
    });
});
