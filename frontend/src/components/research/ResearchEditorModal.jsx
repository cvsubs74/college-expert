import React, { useEffect, useState } from 'react';
import { XMarkIcon } from '@heroicons/react/24/outline';
import { saveResearch, updateResearch } from '../../services/api';
import { RESEARCH_KINDS } from '../../utils/research';
import { useToast } from '../Toast';

/**
 * Create / edit a Research Notebook entry from inside the app — research is NOT
 * Claude-only; you can author it here too. AI agents write the same notes via
 * the connector's save_research tool.
 *
 * @param {{ userEmail: string, isOpen: boolean, onClose: () => void,
 *   onSaved: () => void, colleges?: Array<{university_id?:string,id?:string,
 *   university_name?:string,name?:string}>, existing?: object|null }} props
 *   `existing` (a note) switches the modal to edit mode.
 */
const ResearchEditorModal = ({ userEmail, isOpen, onClose, onSaved, colleges = [], existing = null }) => {
  const toast = useToast();
  const isEdit = Boolean(existing);
  const [title, setTitle] = useState('');
  const [kind, setKind] = useState('note');
  const [summary, setSummary] = useState('');
  const [body, setBody] = useState('');
  const [universityIds, setUniversityIds] = useState([]);
  const [tagsText, setTagsText] = useState('');
  const [saving, setSaving] = useState(false);

  // (Re)seed the form whenever the modal opens — prefilled in edit mode.
  useEffect(() => {
    if (!isOpen) return;
    setTitle(existing?.title || '');
    setKind(RESEARCH_KINDS[existing?.kind] ? existing.kind : 'note');
    setSummary(existing?.summary || '');
    setBody(existing?.body_markdown || '');
    setUniversityIds(existing?.university_ids || []);
    setTagsText((existing?.tags || []).join(', '));
  }, [isOpen, existing]);

  // Esc closes; lock body scroll while open.
  useEffect(() => {
    if (!isOpen) return;
    const onKeyDown = (e) => { if (e.key === 'Escape') onClose(); };
    document.addEventListener('keydown', onKeyDown);
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', onKeyDown);
      document.body.style.overflow = prev;
    };
  }, [isOpen, onClose]);

  const toggleCollege = (id) =>
    setUniversityIds((ids) => (ids.includes(id) ? ids.filter((x) => x !== id) : [...ids, id]));

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!title.trim() || !body.trim() || saving) return;
    setSaving(true);
    const tags = tagsText.split(',').map((t) => t.trim()).filter(Boolean);
    const payload = { title: title.trim(), summary: summary.trim(), bodyMarkdown: body, kind, universityIds, tags };
    const result = isEdit
      ? await updateResearch(userEmail, existing.research_id, payload)
      : await saveResearch(userEmail, payload);
    setSaving(false);
    if (result?.success) {
      toast.success(isEdit ? 'Research updated' : 'Research saved', `"${title.trim()}" is in your notebook.`);
      if (onSaved) onSaved();
      onClose();
    } else {
      toast.error('Could not save research', result?.error || 'Please try again.');
    }
  };

  if (!isOpen) return null;

  const inputCls =
    'w-full text-sm rounded-md border border-[#E0DED8] bg-white px-3 py-2 placeholder-[#9A9A9A] ' +
    'focus:outline-none focus:ring-2 focus:ring-[#1A4D2E] focus:border-transparent';
  const labelCls = 'block text-xs font-medium text-[#4A4A4A] uppercase tracking-wide mb-1';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4" onClick={onClose} role="presentation">
      <div
        className="bg-white rounded-2xl shadow-xl w-full max-w-lg max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="research-editor-title"
      >
        <header className="flex items-center justify-between px-5 py-4 border-b border-[#E0DED8]">
          <h2 id="research-editor-title" className="text-lg font-medium text-[#1A4D2E]">
            {isEdit ? 'Edit research' : 'New research'}
          </h2>
          <button type="button" onClick={onClose} aria-label="Close"
            className="p-1 text-stone-500 hover:text-[#1A4D2E] hover:bg-stone-100 rounded-md transition-colors">
            <XMarkIcon className="w-5 h-5" />
          </button>
        </header>

        <form onSubmit={handleSubmit} className="px-5 py-4 space-y-4">
          <div>
            <label htmlFor="rsh-title" className={labelCls}>Title</label>
            <input id="rsh-title" type="text" value={title} onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g., Duke vs UCSD for Computer Science" maxLength={200} autoFocus required className={inputCls} />
          </div>

          <div>
            <label htmlFor="rsh-kind" className={labelCls}>Kind</label>
            <select id="rsh-kind" value={kind} onChange={(e) => setKind(e.target.value)} className={inputCls}>
              {Object.entries(RESEARCH_KINDS).map(([k, meta]) => (
                <option key={k} value={k}>{meta.emoji} {meta.label}</option>
              ))}
            </select>
          </div>

          <div>
            <label htmlFor="rsh-summary" className={labelCls}>
              Summary <span className="font-normal text-[#9A9A9A] normal-case">(one-line, optional)</span>
            </label>
            <input id="rsh-summary" type="text" value={summary} onChange={(e) => setSummary(e.target.value)}
              placeholder="A short TL;DR shown in the feed" maxLength={500} className={inputCls} />
          </div>

          <div>
            <label htmlFor="rsh-body" className={labelCls}>Details (Markdown)</label>
            <textarea id="rsh-body" value={body} onChange={(e) => setBody(e.target.value)} rows={8} required
              placeholder={'## Notes\n\nWrite your analysis here. Markdown is supported.'} className={`${inputCls} font-mono`} />
          </div>

          {colleges.length > 0 && (
            <div>
              <span className={labelCls}>Link colleges <span className="font-normal text-[#9A9A9A] normal-case">(optional)</span></span>
              <div className="max-h-32 overflow-y-auto rounded-md border border-[#E0DED8] p-2 space-y-1">
                {colleges.map((c) => {
                  const id = c.university_id || c.id;
                  const name = c.university_name || c.name || id;
                  return (
                    <label key={id} className="flex items-center gap-2 text-sm text-[#4A4A4A] cursor-pointer">
                      <input type="checkbox" checked={universityIds.includes(id)} onChange={() => toggleCollege(id)}
                        className="rounded border-gray-300 text-[#1A4D2E] focus:ring-[#1A4D2E]" />
                      {name}
                    </label>
                  );
                })}
              </div>
            </div>
          )}

          <div>
            <label htmlFor="rsh-tags" className={labelCls}>
              Tags <span className="font-normal text-[#9A9A9A] normal-case">(comma-separated, optional)</span>
            </label>
            <input id="rsh-tags" type="text" value={tagsText} onChange={(e) => setTagsText(e.target.value)}
              placeholder="cs, reach, scholarships" className={inputCls} />
          </div>

          <div className="flex items-center justify-end gap-2 pt-2">
            <button type="button" onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-[#4A4A4A] rounded-full hover:bg-stone-100 transition-colors">
              Cancel
            </button>
            <button type="submit" disabled={!title.trim() || !body.trim() || saving}
              className="px-4 py-2 text-sm font-medium text-white rounded-full bg-[#1A4D2E] hover:bg-[#2D6B45] disabled:bg-stone-300 disabled:cursor-not-allowed transition-colors">
              {saving ? 'Saving…' : isEdit ? 'Save changes' : 'Save research'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default ResearchEditorModal;
