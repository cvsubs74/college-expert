/**
 * OnboardingModal — majors step + major_openness (#283).
 *
 * The interests step gains an "Undecided — exploring" chip that lets students
 * finish with zero majors (major_openness:'undecided'); picking majors stamps
 * 'exploring'. The chip and majors are mutually exclusive.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import OnboardingModal from '../components/OnboardingModal';

// Step transitions animate via a 200ms setTimeout; waitFor rides it out.
const nextStep = async (stepTitle) => {
    fireEvent.click(screen.getByRole('button', { name: /continue/i }));
    await waitFor(() => expect(screen.getByText(stepTitle)).toBeInTheDocument());
};

const goToInterestsStep = async () => {
    await nextStep('Your academics');
    await nextStep('Your interests');
};

const completeFromInterests = async () => {
    await nextStep('Your preferences');
    fireEvent.click(screen.getByRole('button', { name: /complete setup/i }));
};

const renderModal = () => {
    const onComplete = vi.fn();
    render(
        <OnboardingModal
            isOpen={true}
            onComplete={onComplete}
            onSkip={vi.fn()}
            userEmail="test.user@example.com"
        />
    );
    return onComplete;
};

describe('OnboardingModal — majors step', () => {
    it('shows the exploration subline on the interests step', async () => {
        renderModal();
        await goToInterestsStep();
        expect(
            screen.getByText(/not sure\? pick what's interesting — stratia helps you find majors you haven't considered/i)
        ).toBeInTheDocument();
    });

    it('Undecided chip completes with zero majors and major_openness undecided', async () => {
        const onComplete = renderModal();
        await goToInterestsStep();

        fireEvent.click(screen.getByRole('button', { name: /undecided — exploring/i }));
        await completeFromInterests();

        expect(onComplete).toHaveBeenCalledTimes(1);
        const payload = onComplete.mock.calls[0][0];
        expect(payload.major_openness).toBe('undecided');
        expect(payload.interests.intended_majors).toEqual([]);
    });

    it('selected majors stamp major_openness exploring', async () => {
        const onComplete = renderModal();
        await goToInterestsStep();

        fireEvent.click(screen.getByRole('button', { name: 'Computer Science' }));
        fireEvent.click(screen.getByRole('button', { name: 'Biology' }));
        await completeFromInterests();

        const payload = onComplete.mock.calls[0][0];
        expect(payload.major_openness).toBe('exploring');
        expect(payload.interests.intended_majors).toEqual(['Computer Science', 'Biology']);
    });

    it('picking a major clears Undecided (mutually exclusive)', async () => {
        const onComplete = renderModal();
        await goToInterestsStep();

        fireEvent.click(screen.getByRole('button', { name: /undecided — exploring/i }));
        fireEvent.click(screen.getByRole('button', { name: 'Computer Science' }));
        await completeFromInterests();

        const payload = onComplete.mock.calls[0][0];
        expect(payload.major_openness).toBe('exploring');
        expect(payload.interests.intended_majors).toEqual(['Computer Science']);
    });

    it('turning Undecided on clears any picked majors', async () => {
        const onComplete = renderModal();
        await goToInterestsStep();

        fireEvent.click(screen.getByRole('button', { name: 'Computer Science' }));
        fireEvent.click(screen.getByRole('button', { name: /undecided — exploring/i }));
        await completeFromInterests();

        const payload = onComplete.mock.calls[0][0];
        expect(payload.major_openness).toBe('undecided');
        expect(payload.interests.intended_majors).toEqual([]);
    });

    it('omits major_openness when nothing was chosen either way', async () => {
        const onComplete = renderModal();
        await goToInterestsStep();
        await completeFromInterests();

        const payload = onComplete.mock.calls[0][0];
        expect(payload).not.toHaveProperty('major_openness');
    });
});
