import React, { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { listResearch, deleteResearch, getCollegeList, getPopularWorkflows } from '../services/api';
import { kindsPresent, kindMeta, groupByWorkflow } from '../utils/research';
import ResearchCard from '../components/research/ResearchCard';
import ResearchEditorModal from '../components/research/ResearchEditorModal';
import WorkflowGroupCard from '../components/research/WorkflowGroupCard';
import PopularWorkflowCard from '../components/research/PopularWorkflowCard';
import { BeakerIcon, ArrowPathIcon, PlusIcon, SparklesIcon } from '@heroicons/react/24/outline';

/**
 * Research Notebook — durable, structured research saved from Claude (via the
 * MCP connector) or the app, linked to the student's colleges, with provenance
 * and a staleness signal. Read + delete here; new entries come from Claude.
 */
export default function ResearchNotebook() {
  const { currentUser: user } = useAuth();
  const [notes, setNotes] = useState([]);
  const [colleges, setColleges] = useState([]);
  const [collegeNames, setCollegeNames] = useState({});
  const [isLoading, setIsLoading] = useState(true);
  const [activeKind, setActiveKind] = useState('all');
  const [editorOpen, setEditorOpen] = useState(false);
  const [editing, setEditing] = useState(null); // a note (edit) or null (create)
  const [viewMode, setViewMode] = useState('research'); // 'research' | 'workflows' | 'popular'
  const [popular, setPopular] = useState([]);

  const load = async () => {
    if (!user?.email) return;
    setIsLoading(true);
    try {
      const [research, list, pop] = await Promise.all([
        listResearch(user.email),
        getCollegeList(user.email),
        getPopularWorkflows(user.email),
      ]);
      if (research?.success) setNotes(research.research || []);
      if (pop?.success) setPopular(pop.workflows || []);
      const raw = list?.colleges || list?.college_list || [];
      setColleges(raw);
      const names = {};
      for (const c of raw) {
        const id = c.university_id || c.id;
        if (id) names[id] = c.university_name || c.name || id;
      }
      setCollegeNames(names);
    } finally {
      setIsLoading(false);
    }
  };

  const openNew = () => { setEditing(null); setEditorOpen(true); };
  const openEdit = (note) => { setEditing(note); setEditorOpen(true); };

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
  const workflowGroups = useMemo(() => groupByWorkflow(notes), [notes]);
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
            Comparisons, timelines, essay angles, scholarship plans and strategy — linked to your
            colleges, with the data cycle they were based on so you know when they go stale. Add
            research yourself, or let a connected AI agent save it for you.
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <button
            type="button"
            onClick={load}
            aria-label="Refresh"
            className="inline-flex items-center gap-1.5 rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            <ArrowPathIcon className="h-4 w-4" />
            Refresh
          </button>
          <button
            type="button"
            onClick={openNew}
            className="inline-flex items-center gap-1.5 rounded-lg bg-[#1A4D2E] px-3 py-1.5 text-sm font-medium text-white hover:bg-[#2D6B45]"
          >
            <PlusIcon className="h-4 w-4" />
            New research
          </button>
        </div>
      </div>

      {!isLoading && (notes.length > 0 || popular.length > 0) && (
        <div className="mt-5 flex gap-1 rounded-lg border border-gray-200 bg-white p-1 w-max" role="tablist" aria-label="View mode">
          <ViewTab active={viewMode === 'research'} onClick={() => setViewMode('research')} label="Research" />
          <ViewTab active={viewMode === 'workflows'} onClick={() => setViewMode('workflows')} label={`Workflows${workflowGroups.length ? ` (${workflowGroups.length})` : ''}`} />
          <ViewTab active={viewMode === 'popular'} onClick={() => setViewMode('popular')} label={`Popular${popular.length ? ` (${popular.length})` : ''}`} />
        </div>
      )}

      {!isLoading && notes.length > 0 && viewMode === 'research' && availableKinds.length > 1 && (
        <div className="mt-3 flex flex-wrap gap-2" role="tablist" aria-label="Filter by kind">
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
      ) : viewMode === 'popular' ? (
        popular.length === 0 ? (
          <div className="mt-8 rounded-xl border border-dashed border-gray-300 bg-gray-50 p-8 text-center text-sm text-gray-600">
            No popular workflows yet. As people run multi-step workflows in their AI agents and
            save the results, the most-used ones show up here to launch with one click.
          </div>
        ) : (
          <div className="mt-5 space-y-4">
            {popular.map((wf) => (
              <PopularWorkflowCard key={wf.signature} wf={wf} />
            ))}
          </div>
        )
      ) : notes.length === 0 ? (
        <EmptyState onNew={openNew} />
      ) : viewMode === 'workflows' ? (
        workflowGroups.length === 0 ? (
          <div className="mt-8 rounded-xl border border-dashed border-gray-300 bg-gray-50 p-8 text-center text-sm text-gray-600">
            No saved workflows yet. When an AI agent saves research, the steps it ran are
            captured here as a reusable workflow — with everything that workflow produced.
          </div>
        ) : (
          <div className="mt-5 space-y-4">
            {workflowGroups.map((g) => (
              <WorkflowGroupCard key={g.signature} group={g} />
            ))}
          </div>
        )
      ) : (
        <div className="mt-5 grid grid-cols-1 gap-4 md:grid-cols-2">
          {visible.map((note) => (
            <ResearchCard
              key={note.research_id}
              note={note}
              collegeNames={collegeNames}
              onDelete={handleDelete}
              onEdit={openEdit}
            />
          ))}
        </div>
      )}

      <ResearchEditorModal
        userEmail={user?.email}
        isOpen={editorOpen}
        onClose={() => setEditorOpen(false)}
        onSaved={load}
        colleges={colleges}
        existing={editing}
      />
    </div>
  );
}

function ViewTab({ active, onClick, label }) {
  return (
    <button
      type="button"
      role="tab"
      aria-selected={active}
      onClick={onClick}
      className={`rounded-md px-3 py-1.5 text-sm font-medium transition ${
        active ? 'bg-[#1A4D2E] text-white' : 'text-gray-600 hover:bg-gray-50'
      }`}
    >
      {label}
    </button>
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

function EmptyState({ onNew }) {
  return (
    <div
      data-testid="research-empty"
      className="mt-8 rounded-xl border border-dashed border-gray-300 bg-gray-50 p-8 text-center"
    >
      <SparklesIcon className="mx-auto h-8 w-8 text-indigo-400" />
      <h2 className="mt-2 text-lg font-semibold text-gray-900">No research saved yet</h2>
      <p className="mx-auto mt-1 max-w-md text-sm text-gray-600">
        Write up a comparison, timeline or strategy yourself — or{' '}
        <Link to="/connect" className="font-medium text-indigo-600 hover:text-indigo-800">connect an AI agent</Link>{' '}
        (Claude, ChatGPT and more) and have it save research here, linked to your colleges.
      </p>
      <button
        type="button"
        onClick={onNew}
        className="mt-4 inline-flex items-center gap-1.5 rounded-lg bg-[#1A4D2E] px-4 py-2 text-sm font-medium text-white hover:bg-[#2D6B45]"
      >
        <PlusIcon className="h-4 w-4" />
        New research
      </button>
    </div>
  );
}
