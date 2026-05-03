import React from 'react';
import { useAuth } from '../../context/AuthContext';
import { isQaAdmin } from './adminAllowlist';
import NotFoundPage from './NotFoundPage';

// Renders children only when the current user is on the QA admin
// allowlist. Otherwise renders a generic 404 — NOT a 403.
//
// Why 404 and not 403:
//   The dashboard is internal-only. A 403 ("forbidden") confirms the
//   route exists; a 404 ("not found") makes the route invisible to
//   anyone who isn't an admin. Combined with no nav entry anywhere in
//   the app and Firestore security rules on the data side, this is
//   three layers of "customers should never see this."

const AdminGate = ({ children }) => {
    const { currentUser, loading } = useAuth();

    // While auth resolves, render nothing — same as a route that hasn't
    // matched yet. Avoids flicker between 404 and content.
    if (loading) return null;

    if (!isQaAdmin(currentUser)) {
        return <NotFoundPage />;
    }

    return <>{children}</>;
};

export default AdminGate;
