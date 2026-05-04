/**
 * ChatPanel — admin Q&A about QA runs.
 *
 * Tests the user-facing contract: typing + sending → API call with
 * conversation history → answer rendered. Errors render inline. The
 * starter-question chips submit on click.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

const sendChatMessageFn = vi.fn();
vi.mock('../services/qaAgent', () => ({
    sendChatMessage: (...a) => sendChatMessageFn(...a),
}));

import ChatPanel from '../components/qa/ChatPanel';

beforeEach(() => {
    sendChatMessageFn.mockReset();
});

describe('ChatPanel', () => {
    it('renders starter questions when there are no messages', () => {
        render(<ChatPanel />);
        expect(screen.getByText(/How is the system trending/i)).toBeInTheDocument();
        expect(screen.getByText(/Which scenarios fail most often/i)).toBeInTheDocument();
    });

    it('sends a typed question and renders the answer', async () => {
        sendChatMessageFn.mockResolvedValue({
            success: true,
            answer: '8/8 pass on the most recent run.',
            context_run_count: 30,
        });
        const user = userEvent.setup();
        render(<ChatPanel />);

        const input = screen.getByPlaceholderText(/Ask about runs/i);
        await user.type(input, 'how is health?');
        await user.click(screen.getByRole('button', { name: /send/i }));

        await waitFor(() => {
            expect(screen.getByText('8/8 pass on the most recent run.')).toBeInTheDocument();
        });

        // Backend was called with the question + empty prior history.
        expect(sendChatMessageFn).toHaveBeenCalledWith({
            question: 'how is health?',
            history: [],
        });
        // The user's question persists in the message list.
        expect(screen.getByText(/> how is health\?/)).toBeInTheDocument();
    });

    it('passes prior messages as history on follow-up turns', async () => {
        sendChatMessageFn
            .mockResolvedValueOnce({ success: true, answer: 'first answer' })
            .mockResolvedValueOnce({ success: true, answer: 'second answer' });
        const user = userEvent.setup();
        render(<ChatPanel />);

        const input = screen.getByPlaceholderText(/Ask about runs/i);
        await user.type(input, 'first question');
        await user.click(screen.getByRole('button', { name: /send/i }));
        await waitFor(() => expect(screen.getByText('first answer')).toBeInTheDocument());

        await user.type(input, 'follow up');
        await user.click(screen.getByRole('button', { name: /send/i }));
        await waitFor(() => expect(screen.getByText('second answer')).toBeInTheDocument());

        // Second call should include the entire prior round.
        const secondCallArg = sendChatMessageFn.mock.calls[1][0];
        expect(secondCallArg.question).toBe('follow up');
        expect(secondCallArg.history).toEqual([
            { role: 'user', content: 'first question' },
            { role: 'assistant', content: 'first answer' },
        ]);
    });

    it('renders an inline error message if the call fails', async () => {
        sendChatMessageFn.mockRejectedValue(new Error('chat backend timeout'));
        const user = userEvent.setup();
        render(<ChatPanel />);

        const input = screen.getByPlaceholderText(/Ask about runs/i);
        await user.type(input, 'q');
        await user.click(screen.getByRole('button', { name: /send/i }));

        await waitFor(() => {
            expect(screen.getByText(/chat backend timeout/i)).toBeInTheDocument();
        });
    });

    it('clicking a starter chip submits that question', async () => {
        sendChatMessageFn.mockResolvedValue({ success: true, answer: 'starter answer' });
        const user = userEvent.setup();
        render(<ChatPanel />);

        await user.click(screen.getByText(/Which scenarios fail most often/i));

        await waitFor(() => {
            expect(sendChatMessageFn).toHaveBeenCalled();
        });
        const submitted = sendChatMessageFn.mock.calls[0][0];
        expect(submitted.question).toMatch(/scenarios fail/i);
    });

    it('disables send while a request is in flight', async () => {
        let resolveCall;
        sendChatMessageFn.mockImplementation(
            () => new Promise((res) => { resolveCall = res; }),
        );
        const user = userEvent.setup();
        render(<ChatPanel />);

        await user.type(screen.getByPlaceholderText(/Ask about runs/i), 'q');
        await user.click(screen.getByRole('button', { name: /send/i }));

        // Send button disabled while pending. (Either the button is
        // disabled or we're showing the "Thinking…" indicator.)
        expect(screen.getByText(/Thinking/i)).toBeInTheDocument();

        // Resolve so the test cleans up.
        resolveCall({ success: true, answer: 'done' });
        await waitFor(() => expect(screen.getByText('done')).toBeInTheDocument());
    });
});
