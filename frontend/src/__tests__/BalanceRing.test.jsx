import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import BalanceRing from '../components/stratia/BalanceRing';

describe('BalanceRing', () => {
  it('renders nothing when there are no colleges', () => {
    const { container } = render(<BalanceRing reach={0} target={0} safety={0} />);
    expect(container).toBeEmptyDOMElement();
  });

  it('shows the total, the verdict and the band legend', () => {
    render(<BalanceRing reach={3} target={4} safety={2} />);
    expect(screen.getByTestId('balance-ring')).toBeInTheDocument();
    expect(screen.getByText('9')).toBeInTheDocument();               // total in the donut
    expect(screen.getByTestId('balance-verdict')).toHaveTextContent(/balanced/i);
  });

  it('offers a "Fix my balance" hand-off only when the list is unbalanced', () => {
    const fixLinks = { claude: 'https://claude.ai/new?q=x', chatgpt: 'https://chatgpt.com/?q=x' };
    // Unbalanced (no safety) → show the fix links.
    const { rerender } = render(<BalanceRing reach={4} target={2} safety={0} fixLinks={fixLinks} />);
    expect(screen.getByRole('link', { name: /claude/i }).getAttribute('href')).toBe(fixLinks.claude);
    expect(screen.getByRole('link', { name: /chatgpt/i }).getAttribute('href')).toBe(fixLinks.chatgpt);
    // Balanced → no fix prompt needed.
    rerender(<BalanceRing reach={3} target={4} safety={2} fixLinks={fixLinks} />);
    expect(screen.queryByRole('link', { name: /claude/i })).not.toBeInTheDocument();
  });

  it('discloses how many fits are estimated rather than personalized', () => {
    render(<BalanceRing reach={2} target={2} safety={2} estimated={3} />);
    expect(screen.getByText(/3 estimated/i)).toBeInTheDocument();
  });
});
