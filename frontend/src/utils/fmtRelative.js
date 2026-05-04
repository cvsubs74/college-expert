// fmtRelative(iso) — short, dashboard-friendly relative-time string.
//
// Output:
//   - "" for falsy or unparseable input (silent fallback so cards don't
//     render "Invalid Date")
//   - "just now" for < 1 minute
//   - "Nm ago" for < 1 hour
//   - "Nh ago" for < 24 hours
//   - "Nd ago" beyond
//
// Previously duplicated inline across CoverageCard, ResolvedIssuesCard,
// and UniversitiesCard. Consolidated here.

export function fmtRelative(iso) {
    if (!iso) return '';
    const dt = new Date(iso);
    const ms = dt.getTime();
    if (Number.isNaN(ms)) return '';
    const diffMs = Date.now() - ms;
    const minutes = Math.floor(diffMs / 60000);
    if (minutes < 1) return 'just now';
    if (minutes < 60) return `${minutes}m ago`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours}h ago`;
    const days = Math.floor(hours / 24);
    return `${days}d ago`;
}
