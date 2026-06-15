import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import DecisionLedger from '../components/stratia/DecisionLedger';

const THREE_DECIDED = [
  { university_id: 'umich', name: 'Michigan', predicted: 'TARGET', decision: 'accepted' },
  { university_id: 'cornell', name: 'Cornell', predicted: 'REACH', decision: 'denied' },
  { university_id: 'uw', name: 'Washington', predicted: 'SAFETY', decision: 'accepted' },
];

describe('DecisionLedger', () => {
  it('renders nothing when there are no colleges', () => {
    const { container } = render(<DecisionLedger outcomes={[]} />);
    expect(container).toBeEmptyDOMElement();
  });

  it('lists each college and suppresses the headline below 3 decisions', () => {
    render(<DecisionLedger outcomes={[
      { university_id: 'a', name: 'Alpha', predicted: 'TARGET', decision: 'accepted' },
      { university_id: 'b', name: 'Bravo', predicted: 'REACH', decision: null },
    ]} />);
    expect(screen.getAllByTestId('ledger-row')).toHaveLength(2);
    expect(screen.queryByTestId('calibration-headline')).not.toBeInTheDocument();
    expect(screen.getByText(/Record 2 more decisions/i)).toBeInTheDocument();
  });

  it('shows the predicted-vs-actual headline once 3 decisions are recorded', () => {
    render(<DecisionLedger outcomes={THREE_DECIDED} />);
    expect(screen.getByTestId('calibration-headline')).toHaveTextContent(/3 of 3 right/);
  });

  it('fires onSetDecision when a decision is chosen', () => {
    const onSetDecision = vi.fn();
    render(<DecisionLedger outcomes={THREE_DECIDED} onSetDecision={onSetDecision} />);
    const select = screen.getByLabelText('Decision for Cornell');
    fireEvent.change(select, { target: { value: 'waitlisted' } });
    expect(onSetDecision).toHaveBeenCalledWith('cornell', 'waitlisted');
  });

  it('shows a read-only decision pill when no setter is provided', () => {
    render(<DecisionLedger outcomes={[
      { university_id: 'umich', name: 'Michigan', predicted: 'TARGET', decision: 'accepted' },
    ]} />);
    expect(screen.queryByLabelText('Decision for Michigan')).not.toBeInTheDocument();
    expect(screen.getByText('Accepted')).toBeInTheDocument();
  });
});
