/**
 * AdminGate tests.
 *
 * The dashboard is internal-only — non-admins must see a 404, not a 403,
 * so the route is invisible to customers. Tests pin down:
 *   - admin email → child renders
 *   - non-admin email → "404 Page not found" instead of child
 *   - signed-out → 404 (same as non-admin)
 *   - while auth is loading, neither child nor 404 renders (prevents flicker)
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, cleanup } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

let authState = { currentUser: null, loading: false };

vi.mock('../context/AuthContext', () => ({
    useAuth: () => authState,
    AuthProvider: ({ children }) => children,
}));

import AdminGate from '../components/qa/AdminGate';

beforeEach(() => {
    cleanup();
    authState = { currentUser: null, loading: false };
});

const renderGate = () =>
    render(
        <MemoryRouter>
            <AdminGate>
                <div data-testid="dashboard">Admin dashboard content</div>
            </AdminGate>
        </MemoryRouter>
    );

describe('AdminGate', () => {
    it('renders the protected child when current user is on the allowlist', () => {
        authState = {
            currentUser: { email: 'cvsubs@gmail.com' },
            loading: false,
        };
        renderGate();
        expect(screen.getByTestId('dashboard')).toBeInTheDocument();
    });

    it('hides the child behind a 404 page for non-admin emails', () => {
        authState = {
            currentUser: { email: 'random.user@example.com' },
            loading: false,
        };
        renderGate();
        expect(screen.queryByTestId('dashboard')).toBeNull();
        expect(screen.getByText('404')).toBeInTheDocument();
        expect(screen.getByText(/Page not found/i)).toBeInTheDocument();
    });

    it('shows 404 (not 403) for signed-out visitors', () => {
        authState = { currentUser: null, loading: false };
        renderGate();
        expect(screen.queryByTestId('dashboard')).toBeNull();
        expect(screen.getByText('404')).toBeInTheDocument();
    });

    it('renders nothing while auth is still resolving (prevents flicker)', () => {
        authState = { currentUser: null, loading: true };
        renderGate();
        expect(screen.queryByTestId('dashboard')).toBeNull();
        expect(screen.queryByText('404')).toBeNull();
    });

    it('email comparison is case-insensitive', () => {
        authState = {
            currentUser: { email: 'CVSUBS@gmail.com' },
            loading: false,
        };
        renderGate();
        expect(screen.getByTestId('dashboard')).toBeInTheDocument();
    });
});
