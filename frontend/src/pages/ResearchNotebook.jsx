import React, { useEffect, useMemo, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { listResearch, deleteResearch, getCollegeList } from '../services/api';
import { kindsPresent, kindMeta } from '../utils/research';
import ResearchCard from '../components/research/ResearchCard';
import { BeakerIcon, ArrowPathIcon, SparklesIcon } from '@heroicons/react/24/outline';

/**
 * Research Notebook — durable, structured research saved from Claude (via the
 * MCP connector) or the app, linked to the student's colleges, with provenance
 * and a staleness signal. Read + delete here; new entries come from Claude.
 */
export default function ResearchNotebook() {
  const { currentUser: user } = useAuth();
  const [notes, setNotes] = useState([]);
  const [collegeNames, setCollegeNames] = useState({});
  const [isLoading, setIsLoading] = useState(true);
  const [activeKind, setActiveKind] = useState('all');

  const load = async () => {
    if (!user?.email) return;
    setIsLoading(true);
    try {
      const [research, list] = await Promise.all([
        listResearch(user.email),
        getCollegeList(user.email),
      ]);
      if (research?.success) setNotes(research.research || []);
      const names = {};
      for (const c of (list?.colleges || list?.college_list || [])) {
        const id = c.university_id || c.id;
        if (id) names[id] = c.university_name || c.name || id;
      }
      setCollegeNames(names);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    load();
    // Depend on the email (a stable string), not the user object, so a new
    // context wrapper object per render can't trigger a reload loop.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user?.email]);

  const handleDelete = async (researchId) => {
    if (!user?.email) return;
    if (!window.confirm('Delete this research note? This cannot be undone.')) return;
    const prev = notes;
    setNotes((n) => n.filter((r) => r.research_id !== researchId)); // optimistic
    const res = await deleteResearch(user.email, researchId);
    if (!res?.success) setNotes(prev); // rollback on failure
  };

  const availableKinds = useMemo(() => kindsPresent(notes), [notes]);
  const visible = useMemo(
    () => (activeKind === 'all' ? notes : notes.filter((n) => (n.kind || 'note') === activeKind)),
    [notes, activeKind]
  );

  return (
    <div className="mx-auto max-w-5xl px-4 py-6 sm:px-6">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-bold text-gray-900">
            <BeakerIcon className="h-6 w-6 text-indigo-600" />
            Research Notebook
          </h1>
          <p className="mt-1 max-w-2xl text-sm text-gray-600">
            Analyses you save from Claude land here — comparisons, timelines, essay angles,
            scholarship plans and strategy — linked to your colleges, with the data cycle they
            were based on so you know when they go stale.
          </p>
        </div>
        <button
          type="button"
          onClick={load}
          className="inline-flex shrink-0 items-center gap-1.5 rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50"
        >
          <ArrowPathIcon className="h-4 w-4" />
          Refresh
        </button>
      </div>

      {!isLoading && notes.length > 0 && availableKinds.length > 1 && (
        <div className="mt-5 flex flex-wrap gap-2" role="tablist" aria-label="Filter by kind">
          <FilterChip active={activeKind === 'all'} onClick={() => setActiveKind('all')} label={`All (${notes.length})`} />
          {availableKinds.map((k) => (
            <FilterChip
              key={k}
              active={activeKind === k}
              onClick={() => setActiveKind(k)}
              label={`${kindMeta(k).emoji} ${kindMeta(k).label}`}
            />
          ))}
        </div>
      )}

      {isLoading ? (
        <div className="mt-10 text-center text-gray-500">Loading your research…</div>
      ) : notes.length === 0 ? (
        <EmptyState />
      ) : (
        <div className="mt-5 grid grid-cols-1 gap-4 md:grid-cols-2">
          {visible.map((note) => (
            <ResearchCard
              key={note.research_id}
              note={note}
              collegeNames={collegeNames}
              onDelete={handleDelete}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function FilterChip({ active, onClick, label }) {
  return (
    <button
      type="button"
      role="tab"
      aria-selected={active}
      onClick={onClick}
      className={`rounded-full border px-3 py-1 text-sm font-medium transition ${
        active
          ? 'border-indigo-300 bg-indigo-50 text-indigo-700'
          : 'border-gray-200 bg-white text-gray-600 hover:bg-gray-50'
      }`}
    >
      {label}
    </button>
  );
}

function EmptyState() {
  return (
    <div
      data-testid="research-empty"
      className="mt-8 rounded-xl border border-dashed border-gray-300 bg-gray-50 p-8 text-center"
    >
      <SparklesIcon className="mx-auto h-8 w-8 text-indigo-400" />
      <h2 className="mt-2 text-lg font-semibold text-gray-900">No research saved yet</h2>
      <p className="mx-auto mt-1 max-w-md text-sm text-gray-600">
        Connect the <span className="font-medium">Stratia Admissions</span> connector in Claude,
        then ask Claude to analyze your colleges. When it produces something useful, tell it to
        “save this to my Stratia notebook” — it’ll appear here, linked to your schools.
      </p>
    </div>
  );
}
