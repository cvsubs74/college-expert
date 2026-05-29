/**
 * Date helpers for the Roadmap "Upcoming Deadlines" list.
 *
 * getDaysUntil guards against invalid dates: an unparseable due_date
 * (e.g. "Varies", "Rolling") returns null instead of NaN, so the UI shows
 * "Date TBD" rather than "NaN days left". See issue #187.
 */

// Days from today until `dateStr` (negative = overdue). Returns null when the
// value is missing or not a real date.
export const getDaysUntil = (dateStr) => {
    if (!dateStr) return null;
    const dueDate = new Date(dateStr);
    if (Number.isNaN(dueDate.getTime())) return null;
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    dueDate.setHours(0, 0, 0, 0);
    return Math.ceil((dueDate - today) / (1000 * 60 * 60 * 24));
};

// Urgency bucket for styling. null (no date) → neutral 'stone'.
export const getUrgencyColor = (daysUntil) => {
    if (daysUntil === null) return 'stone';
    if (daysUntil < 0) return 'red';   // overdue
    if (daysUntil <= 3) return 'red';
    if (daysUntil <= 7) return 'amber';
    return 'emerald';
};

// Human-readable badge label. null → "Date TBD" (never "NaN days left").
export const deadlineLabel = (daysUntil) => {
    if (daysUntil === null) return 'Date TBD';
    if (daysUntil < 0) return `${Math.abs(daysUntil)}d overdue`;
    if (daysUntil === 0) return 'Due today';
    if (daysUntil === 1) return 'Due tomorrow';
    return `${daysUntil} days left`;
};
