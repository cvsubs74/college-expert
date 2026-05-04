/**
 * SparklineByDay — top-of-page 30-day pass/fail bar chart with a
 * headline pass-rate.
 *
 * Bug repro: the original code computed pass rate from DAYS where any
 * fail in a day turned the whole day red, so 5-of-6 passing runs in
 * one day still counted as a fail-day. With most days containing at
 * least one historical fail, the headline read "0% green" while the
 * recent-N pill said 100%. Fix: compute pass rate from RUN counts.
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import SparklineByDay from '../components/qa/SparklineByDay';

const dayAgo = (days) => {
    const d = new Date();
    d.setHours(0, 0, 0, 0);
    d.setDate(d.getDate() - days);
    return d.toISOString();
};

describe('SparklineByDay headline', () => {
    it('100% pass when every run passed', () => {
        render(
            <SparklineByDay
                runs={[
                    { run_id: 'r1', started_at: dayAgo(0), summary: { pass: 4, fail: 0, total: 4 } },
                    { run_id: 'r2', started_at: dayAgo(1), summary: { pass: 4, fail: 0, total: 4 } },
                ]}
            />
        );
        expect(screen.getByText('100% green')).toBeInTheDocument();
        expect(screen.getByText(/2 runs/)).toBeInTheDocument();
    });

    it('counts a day with any fail as red, but pass rate is run-weighted', () => {
        // Day 0: 5 pass + 1 fail = day is red but only 1 run failed.
        // Day 1: 4 pass = clean.
        // Total 10 runs, 9 passed → 90% green.
        const runs = [
            ...Array.from({ length: 5 }, (_, i) => ({
                run_id: `r_pass_${i}`, started_at: dayAgo(0),
                summary: { pass: 4, fail: 0, total: 4 },
            })),
            { run_id: 'r_fail', started_at: dayAgo(0),
              summary: { pass: 3, fail: 1, total: 4 } },
            ...Array.from({ length: 4 }, (_, i) => ({
                run_id: `r_pass_d1_${i}`, started_at: dayAgo(1),
                summary: { pass: 4, fail: 0, total: 4 },
            })),
        ];
        render(<SparklineByDay runs={runs} />);
        expect(screen.getByText('90% green')).toBeInTheDocument();
        expect(screen.getByText(/10 runs/)).toBeInTheDocument();
    });

    it("does NOT show 0% green when most runs passed (regression for the original bug)", () => {
        // 21 runs across 5 days; 18 passed, 3 failed (one fail per
        // day across 3 of the 5 days). The OLD computation would say
        // 2/5 days clean = 40%; with severe distribution it could
        // even read 0%. The new computation: 18/21 ≈ 86%.
        const runs = [];
        for (let day = 0; day < 5; day++) {
            // 4 passes per day
            for (let i = 0; i < 4; i++) {
                runs.push({
                    run_id: `r_p_${day}_${i}`, started_at: dayAgo(day),
                    summary: { pass: 4, fail: 0, total: 4 },
                });
            }
            // 1 fail on days 0, 1, 2 (so 3 of 5 days are 'red' under the
            // old day-level logic)
            if (day < 3) {
                runs.push({
                    run_id: `r_f_${day}`, started_at: dayAgo(day),
                    summary: { pass: 2, fail: 2, total: 4 },
                });
            }
        }
        // Total 23 runs, 20 passed = 87%.
        expect(runs.length).toBe(23);
        const passed = runs.filter((r) => r.summary.fail === 0).length;
        expect(passed).toBe(20);

        render(<SparklineByDay runs={runs} />);
        expect(screen.getByText('87% green')).toBeInTheDocument();
        // And definitely not 0% — that was the bug.
        expect(screen.queryByText('0% green')).toBeNull();
        expect(screen.queryByText('40% green')).toBeNull();
    });

    it('renders em-dash when no runs', () => {
        render(<SparklineByDay runs={[]} />);
        expect(screen.getByText(/—/)).toBeInTheDocument();
    });

    it('ignores runs without started_at', () => {
        render(
            <SparklineByDay
                runs={[
                    { run_id: 'no_ts', summary: { pass: 4, fail: 0 } },
                    { run_id: 'r1', started_at: dayAgo(0), summary: { pass: 4, fail: 0 } },
                ]}
            />
        );
        expect(screen.getByText('100% green')).toBeInTheDocument();
        expect(screen.getByText(/1 runs/)).toBeInTheDocument();
    });
});
