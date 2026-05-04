/**
 * TabBar — tab strip used on the QA dashboard. Reads its active tab
 * from props; emits onChange(id) when the user clicks a tab.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import TabBar from '../components/qa/TabBar';

const tabs = [
    { id: 'overview', label: 'Overview' },
    { id: 'runs', label: 'Runs', badge: 2 },
    { id: 'ask', label: 'Ask' },
    { id: 'steer', label: 'Steer' },
];

describe('TabBar', () => {
    it('renders one button per tab', () => {
        render(<TabBar tabs={tabs} activeId="overview" onChange={() => {}} />);
        expect(screen.getByRole('tab', { name: /overview/i })).toBeInTheDocument();
        expect(screen.getByRole('tab', { name: /runs/i })).toBeInTheDocument();
        expect(screen.getByRole('tab', { name: /ask/i })).toBeInTheDocument();
        expect(screen.getByRole('tab', { name: /steer/i })).toBeInTheDocument();
    });

    it('marks the active tab with aria-selected=true', () => {
        render(<TabBar tabs={tabs} activeId="runs" onChange={() => {}} />);
        const runsTab = screen.getByRole('tab', { name: /runs/i });
        expect(runsTab).toHaveAttribute('aria-selected', 'true');
        const overviewTab = screen.getByRole('tab', { name: /overview/i });
        expect(overviewTab).toHaveAttribute('aria-selected', 'false');
    });

    it('renders badge counts when > 0', () => {
        render(<TabBar tabs={tabs} activeId="overview" onChange={() => {}} />);
        // Runs tab has badge=2 → "2" should appear inside its button.
        const runsTab = screen.getByRole('tab', { name: /runs.*2/i });
        expect(runsTab).toBeInTheDocument();
    });

    it('omits badge when count is 0', () => {
        const noBadgeTabs = tabs.map((t) =>
            t.id === 'runs' ? { ...t, badge: 0 } : t,
        );
        render(<TabBar tabs={noBadgeTabs} activeId="overview" onChange={() => {}} />);
        const runsTab = screen.getByRole('tab', { name: /^runs$/i });
        expect(runsTab).toBeInTheDocument();
    });

    it('calls onChange with the clicked tab id', async () => {
        const user = userEvent.setup();
        const onChange = vi.fn();
        render(<TabBar tabs={tabs} activeId="overview" onChange={onChange} />);
        await user.click(screen.getByRole('tab', { name: /ask/i }));
        expect(onChange).toHaveBeenCalledWith('ask');
    });
});
