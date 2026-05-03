import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
    SparklesIcon,
    PencilSquareIcon,
    AcademicCapIcon,
    BuildingLibraryIcon,
    ArrowRightIcon,
    ClockIcon,
} from '@heroicons/react/24/outline';
import { fetchWorkFeed } from '../../services/api';
import NotesAffordance from './NotesAffordance';

// Source → icon mapping; mirrors the tab strip in RoadmapPage so the user
// can recognize which surface a focus item belongs to at a glance.
const SOURCE_ICONS = {
    roadmap_task: SparklesIcon,
    essay: PencilSquareIcon,
    scholarship: AcademicCapIcon,
    college_deadline: BuildingLibraryIcon,
};

const SOURCE_LABELS = {
    roadmap_task: 'Plan',
    essay: 'Essay',
    scholarship: 'Scholarship',
    college_deadline: 'Deadline',
};

// Map a work-feed item's `source` to the Firestore collection that owns
// its `notes` field. Items sourced from college_deadline are KB-derived
// (not user-owned), so they don't get a notes affordance.
const SOURCE_TO_NOTES_COLLECTION = {
    roadmap_task: 'roadmap_tasks',
    essay: 'essay_tracker',
    scholarship: 'scholarship_tracker',
};

// Urgency → Tailwind color classes. Matches RoadmapView's red/amber/emerald
// scheme so the two surfaces feel like one app.
const URGENCY_STYLES = {
    overdue: 'bg-red-100 text-red-800 border-red-200',
    urgent: 'bg-red-50 text-red-700 border-red-200',
    soon: 'bg-amber-50 text-amber-800 border-amber-200',
    later: 'bg-emerald-50 text-emerald-800 border-emerald-200',
};

const formatDueLabel = (item) => {
    const { days_until: days, due_date: due, urgency } = item;
    if (days === null || days === undefined) return null;
    if (days < 0) return `Overdue · ${Math.abs(days)}d`;
    if (days === 0) return 'Due today';
    if (days === 1) return 'Due tomorrow';
    if (days <= 30) return `Due in ${days}d`;
    if (due) {
        try {
            return `Due ${new Date(due + 'T00:00:00').toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}`;
        } catch {
            return `Due ${due}`;
        }
    }
    return urgency || null;
};

const ThisWeekFocusCard = ({ userEmail, limit = 8 }) => {
    const navigate = useNavigate();
    const [items, setItems] = useState([]);
    const [total, setTotal] = useState(0);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (!userEmail) return;
        let cancelled = false;
        const load = async () => {
            setLoading(true);
            const data = await fetchWorkFeed(userEmail, limit);
            if (cancelled) return;
            setItems(Array.isArray(data.items) ? data.items : []);
            setTotal(typeof data.total === 'number' ? data.total : 0);
            setLoading(false);
        };
        load();
        return () => { cancelled = true; };
    }, [userEmail, limit]);

    const handleItemClick = (item) => {
        if (item.deep_link) navigate(item.deep_link);
    };

    return (
        <section className="mb-6 bg-white border border-[#E0DED8] rounded-xl shadow-sm overflow-hidden">
            <header className="flex items-center justify-between px-5 py-3 border-b border-[#E0DED8] bg-[#F8F6F0]">
                <div className="flex items-center gap-2">
                    <ClockIcon className="w-5 h-5 text-[#1A4D2E]" />
                    <h2 className="text-sm font-semibold text-[#1A4D2E] tracking-wide uppercase">
                        This Week
                    </h2>
                </div>
                {!loading && total > items.length && (
                    <span className="text-xs text-[#6B6B6B]">
                        Showing {items.length} of {total}
                    </span>
                )}
            </header>

            {loading ? (
                <FocusCardSkeleton />
            ) : items.length === 0 ? (
                <FocusCardEmptyState />
            ) : (
                <ul className="divide-y divide-[#E0DED8]">
                    {items.map((item) => (
                        <FocusItemRow
                            key={`${item.source}-${item.id}`}
                            item={item}
                            userEmail={userEmail}
                            onClick={() => handleItemClick(item)}
                        />
                    ))}
                </ul>
            )}
        </section>
    );
};

const FocusItemRow = ({ item, userEmail, onClick }) => {
    const Icon = SOURCE_ICONS[item.source] || SparklesIcon;
    const dueLabel = formatDueLabel(item);
    const urgencyClass = URGENCY_STYLES[item.urgency] || 'bg-stone-50 text-stone-700 border-stone-200';
    const isClickable = !!item.deep_link;
    const notesCollection = SOURCE_TO_NOTES_COLLECTION[item.source];

    // The row is a <div> rather than <button> so it can host a separate
    // NotesAffordance button without invalid nested-button HTML. Keyboard
    // accessibility is preserved via role+tabIndex+onKeyDown on the row,
    // and the notes button stops propagation so its clicks don't navigate.
    const handleRowKeyDown = (e) => {
        if (!isClickable) return;
        if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            onClick();
        }
    };

    return (
        <li>
            <div
                role={isClickable ? 'button' : undefined}
                tabIndex={isClickable ? 0 : undefined}
                onClick={isClickable ? onClick : undefined}
                onKeyDown={handleRowKeyDown}
                className={`flex items-start gap-3 px-5 py-3 transition-colors
                    ${isClickable ? 'hover:bg-[#F8F6F0] cursor-pointer focus:outline-none focus:bg-[#F8F6F0]' : 'cursor-default'}`}
            >
                <Icon className="w-5 h-5 text-[#1A4D2E] flex-shrink-0 mt-0.5" />
                <div className="flex-1 min-w-0">
                    <div className="flex items-baseline gap-2 flex-wrap">
                        <span className="text-sm font-medium text-[#2C2C2C] truncate">
                            {item.title}
                        </span>
                        <span className="text-xs uppercase tracking-wide text-[#6B6B6B]">
                            {SOURCE_LABELS[item.source] || item.source}
                        </span>
                    </div>
                    {item.subtitle && (
                        <p className="text-xs text-[#6B6B6B] mt-0.5 truncate">
                            {item.subtitle}
                        </p>
                    )}
                </div>
                {dueLabel && (
                    <span className={`text-xs px-2 py-0.5 rounded-full border whitespace-nowrap ${urgencyClass}`}>
                        {dueLabel}
                    </span>
                )}
                {notesCollection && item.id && (
                    <div onClick={(e) => e.stopPropagation()} className="flex-shrink-0">
                        <NotesAffordance
                            userEmail={userEmail}
                            collection={notesCollection}
                            itemId={item.id}
                            initialValue={item.notes}
                        />
                    </div>
                )}
                {isClickable && (
                    <ArrowRightIcon className="w-4 h-4 text-[#9A9A9A] flex-shrink-0 mt-1" />
                )}
            </div>
        </li>
    );
};

const FocusCardSkeleton = () => (
    <ul className="divide-y divide-[#E0DED8]">
        {[0, 1, 2].map((i) => (
            <li key={i} className="px-5 py-3 flex items-center gap-3 animate-pulse">
                <div className="w-5 h-5 rounded bg-stone-200" />
                <div className="flex-1 space-y-2">
                    <div className="h-3 bg-stone-200 rounded w-2/3" />
                    <div className="h-2 bg-stone-100 rounded w-1/3" />
                </div>
                <div className="h-4 w-16 bg-stone-200 rounded-full" />
            </li>
        ))}
    </ul>
);

const FocusCardEmptyState = () => (
    <div className="px-5 py-6 text-center">
        <p className="text-sm text-[#6B6B6B]">
            Nothing urgent right now. Add schools to your launchpad to start tracking deadlines and tasks.
        </p>
    </div>
);

export default ThisWeekFocusCard;
