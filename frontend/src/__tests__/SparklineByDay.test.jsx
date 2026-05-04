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


// ---- Per-run bar rendering ------------------------------------------------
//
// Bug repro 2026-05-04: bars were per-DAY ("worst run that day"), but
// with 21 runs spread across 30 days, 27 of 30 buckets were empty (gray)
// and the operator saw "no green bars" while the headline said "81%
// green". Per-run bars match the headline directly.

describe('SparklineByDay bars (per-run)', () => {
    it('renders one bar per run', () => {
        const { container } = render(
            <SparklineByDay
                runs={[
                    { run_id: 'r1', started_at: dayAgo(0), summary: { pass: 4, fail: 0 } },
                    { run_id: 'r2', started_at: dayAgo(1), summary: { pass: 4, fail: 0 } },
                    { run_id: 'r3', started_at: dayAgo(2), summary: { pass: 3, fail: 1 } },
                ]}
            />
        );
        const rects = container.querySelectorAll('rect');
        expect(rects.length).toBe(3);
    });

    it("colors each bar by that run's pass/fail (not its day)", () => {
        const { container } = render(
            <SparklineByDay
                runs={[
                    // Same day: 1 pass + 1 fail. Old per-day logic would
                    // paint the whole day red. Per-run logic must paint
                    // one green and one red bar.
                    { run_id: 'r_pass', started_at: dayAgo(0),
                      summary: { pass: 4, fail: 0 } },
                    { run_id: 'r_fail', started_at: dayAgo(0),
                      summary: { pass: 3, fail: 1 } },
                ]}
            />
        );
        const fills = Array.from(container.querySelectorAll('rect'))
            .map((r) => r.getAttribute('fill'));
        // One emerald, one red — order is chronological so r_pass comes
        // first if its timestamp is earlier in the array order.
        expect(fills).toContain('#10B981');
        expect(fills).toContain('#EF4444');
    });

    it('orders bars chronologically (oldest left, newest right)', () => {
        const { container } = render(
            <SparklineByDay
                runs={[
                    // Out of order in the input — expect chronological output.
                    { run_id: 'r_now', started_at: dayAgo(0),
                      summary: { pass: 4, fail: 0 } },
                    { run_id: 'r_oldest', started_at: dayAgo(5),
                      summary: { pass: 3, fail: 1 } },
                    { run_id: 'r_mid', started_at: dayAgo(2),
                      summary: { pass: 4, fail: 0 } },
                ]}
            />
        );
        const fills = Array.from(container.querySelectorAll('rect'))
            .map((r) => r.getAttribute('fill'));
        // Oldest first → red (the failing one is r_oldest), then green, green.
        expect(fills).toEqual(['#EF4444', '#10B981', '#10B981']);
    });

    it('caps bars when there are more runs than fit', () => {
        // Pump 60 runs in. The component should render only the most
        // recent N (where N is the cap) and not lay out 60 paper-thin
        // bars that don't read.
        const runs = Array.from({ length: 60 }, (_, i) => ({
            run_id: `r${i}`,
            started_at: new Date(Date.now() - i * 60000).toISOString(),
            summary: { pass: 4, fail: 0 },
        }));
        const { container } = render(<SparklineByDay runs={runs} />);
        const rects = container.querySelectorAll('rect');
        // Cap chosen in the component; at minimum we expect <60 bars.
        expect(rects.length).toBeLessThan(60);
        expect(rects.length).toBeGreaterThan(0);
    });

    it('does not produce empty/gray bars when runs are sparse over 30 days', () => {
        // The original bug: 21 runs over 30 days produced 27 gray
        // buckets + 3 colored bars. Per-run logic should produce
        // exactly 21 bars, all colored.
        const runs = [];
        for (let i = 0; i < 21; i++) {
            runs.push({
                run_id: `r${i}`,
                started_at: new Date(Date.now() - i * 12 * 60 * 60 * 1000).toISOString(),
                summary: { pass: 4, fail: 0 },
            });
        }
        const { container } = render(<SparklineByDay runs={runs} />);
        const fills = Array.from(container.querySelectorAll('rect'))
            .map((r) => r.getAttribute('fill'));
        // Every bar is colored — no gray "no runs this day" buckets.
        expect(fills.every((f) => f === '#10B981' || f === '#EF4444')).toBe(true);
        expect(fills.length).toBe(21);
    });
});
