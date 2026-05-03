/**
 * SynthesizedBadge marks scenarios that the LLM generated on the fly,
 * with a tooltip-friendly explanation of why.
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import SynthesizedBadge from '../components/qa/SynthesizedBadge';

describe('SynthesizedBadge', () => {
    it('renders nothing when scenario is not synthesized', () => {
        const { container } = render(
            <SynthesizedBadge synthesized={false} rationale="" />
        );
        expect(container.firstChild).toBeNull();
    });

    it('renders the LLM-generated badge when synthesized', () => {
        render(<SynthesizedBadge synthesized={true} rationale="Tests low GPA" />);
        expect(screen.getByText(/LLM[\s-]?generated/i)).toBeInTheDocument();
    });

    it('renders the rationale block when provided', () => {
        render(
            <SynthesizedBadge
                synthesized={true}
                rationale="This scenario targets the under-tested fit surface."
            />
        );
        expect(
            screen.getByText(/under-tested fit surface/i)
        ).toBeInTheDocument();
    });
});
