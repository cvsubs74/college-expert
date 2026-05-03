/**
 * AssertionDiff renders cross-reference assertion results with a
 * side-by-side expected vs actual view.
 *
 * Standard assertions (status_is_2xx etc.) → just name + pass/fail.
 * Cross-reference assertions (with `expected` + `actual` fields) →
 *   name + status + expected/actual diff block.
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import AssertionDiff from '../components/qa/AssertionDiff';

describe('AssertionDiff', () => {
    it('renders a passing standard assertion as a single line', () => {
        const result = { name: 'status==200', passed: true };
        render(<AssertionDiff result={result} />);
        expect(screen.getByText(/status==200/)).toBeInTheDocument();
    });

    it('renders the message when an assertion fails', () => {
        const result = {
            name: 'status==200',
            passed: false,
            message: 'got 500',
        };
        render(<AssertionDiff result={result} />);
        expect(screen.getByText(/got 500/)).toBeInTheDocument();
    });

    it('renders side-by-side expected/actual when available', () => {
        const result = {
            name: 'college_list[0].deadline == truth.mit.application_deadline',
            passed: false,
            expected: '2027-01-05',
            actual: '2027-01-15',
            message: 'value mismatch',
        };
        render(<AssertionDiff result={result} />);
        // Labels (expected: / actual:) are exact strings rendered in
        // the diff block. Values appear once each.
        expect(screen.getByText('expected:')).toBeInTheDocument();
        expect(screen.getByText('actual:')).toBeInTheDocument();
        expect(screen.getByText('2027-01-05')).toBeInTheDocument();
        expect(screen.getByText('2027-01-15')).toBeInTheDocument();
    });

    it('renders skipped assertions in a muted style', () => {
        const result = {
            name: 'truth lookup',
            passed: false,
            skipped: true,
            message: 'kb missed for unknown_school',
        };
        render(<AssertionDiff result={result} />);
        expect(screen.getByText(/skip/i)).toBeInTheDocument();
    });
});
