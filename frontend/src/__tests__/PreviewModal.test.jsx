/**
 * PreviewModal — confirmation dialog shown after the user clicks "Run
 * now". Lists what the agent picked + each pick's rationale, with
 * [Run] / [Cancel].
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import PreviewModal from '../components/qa/PreviewModal';

const samplePicks = [
    {
        id: 'junior_spring_5school',
        description: 'Junior in spring with 5-school list',
        business_rationale: 'Validates the most common journey for top users.',
        surfaces_covered: ['profile', 'college_list', 'roadmap'],
        synthesized: false,
    },
    {
        id: 'synth_essay_focus',
        description: 'Synthesized essay-focused scenario',
        synthesized: true,
        synthesis_rationale: 'Targets fb_abc admin feedback re: essay tracker.',
        feedback_id: 'fb_abc',
        surfaces_covered: ['essay'],
    },
];

describe('PreviewModal', () => {
    it('renders one row per pick with id + description', () => {
        render(
            <PreviewModal
                picked={samplePicks}
                synthCount={1}
                staticCount={1}
                onConfirm={() => {}}
                onCancel={() => {}}
            />
        );
        expect(screen.getByText(/junior_spring_5school/)).toBeInTheDocument();
        expect(screen.getByText(/Junior in spring with 5-school list/)).toBeInTheDocument();
        expect(screen.getByText(/synth_essay_focus/)).toBeInTheDocument();
    });

    it('shows the synth/static counts in the header', () => {
        render(
            <PreviewModal
                picked={samplePicks}
                synthCount={1}
                staticCount={1}
                onConfirm={() => {}}
                onCancel={() => {}}
            />
        );
        expect(screen.getByText(/1 LLM-generated/)).toBeInTheDocument();
        expect(screen.getByText(/1 from corpus/)).toBeInTheDocument();
    });

    it('shows business_rationale + surfaces for each pick', () => {
        render(
            <PreviewModal
                picked={samplePicks}
                synthCount={1}
                staticCount={1}
                onConfirm={() => {}}
                onCancel={() => {}}
            />
        );
        expect(screen.getByText(/most common journey/i)).toBeInTheDocument();
        expect(screen.getByText('profile')).toBeInTheDocument();
        expect(screen.getByText('college_list')).toBeInTheDocument();
    });

    it('shows synthesized badge + feedback id when applicable', () => {
        render(
            <PreviewModal
                picked={samplePicks}
                synthCount={1}
                staticCount={1}
                onConfirm={() => {}}
                onCancel={() => {}}
            />
        );
        // "LLM-generated" appears both in the header summary and as the
        // per-row badge — we just want to confirm at least one is present.
        expect(screen.getAllByText(/LLM-generated/i).length).toBeGreaterThan(0);
        expect(screen.getByText(/addresses fb_abc/i)).toBeInTheDocument();
    });

    it('Run button calls onConfirm', async () => {
        const user = userEvent.setup();
        const onConfirm = vi.fn();
        render(
            <PreviewModal
                picked={samplePicks}
                synthCount={1}
                staticCount={1}
                onConfirm={onConfirm}
                onCancel={() => {}}
            />
        );
        await user.click(screen.getByRole('button', { name: /^run$/i }));
        expect(onConfirm).toHaveBeenCalled();
    });

    it('Cancel button calls onCancel', async () => {
        const user = userEvent.setup();
        const onCancel = vi.fn();
        render(
            <PreviewModal
                picked={samplePicks}
                synthCount={1}
                staticCount={1}
                onConfirm={() => {}}
                onCancel={onCancel}
            />
        );
        await user.click(screen.getByRole('button', { name: /^cancel$/i }));
        expect(onCancel).toHaveBeenCalled();
    });

    it('disables Run while busy', () => {
        render(
            <PreviewModal
                picked={samplePicks}
                synthCount={1}
                staticCount={1}
                busy={true}
                onConfirm={() => {}}
                onCancel={() => {}}
            />
        );
        expect(screen.getByRole('button', { name: /starting/i })).toBeDisabled();
    });

    it('renders empty state with no picks', () => {
        render(
            <PreviewModal
                picked={[]}
                onConfirm={() => {}}
                onCancel={() => {}}
            />
        );
        expect(screen.getByText(/No scenarios picked/i)).toBeInTheDocument();
        // Run button is disabled when there's nothing to run.
        expect(screen.getByRole('button', { name: /^run$/i })).toBeDisabled();
    });
});
