// Single source of truth for which emails see the QA admin dashboard.
// Mirror this when adding admins:
//   - QA_ADMIN_EMAILS env var on the qa-agent function
//   - the isQaAdmin() rule in firestore.rules
//
// Everything in /qa-runs is gated by this list. Non-admins (and
// non-signed-in visitors) get a 404 — same shape as any other unknown
// route — so the dashboard is invisible to customers.

export const QA_ADMIN_EMAILS = ['cvsubs@gmail.com'];

export function isQaAdmin(user) {
    if (!user || !user.email) return false;
    return QA_ADMIN_EMAILS.includes(user.email.toLowerCase());
}
