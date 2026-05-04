import React from 'react';

// Tab strip used by the QA dashboard. Each tab has a stable id (used
// in the URL ?tab= query param), a label, and an optional icon.
//
// Spec: docs/prd/qa-dashboard-tabbed-layout.md.

const TabBar = ({ tabs, activeId, onChange }) => {
    return (
        <nav
            role="tablist"
            aria-label="Dashboard sections"
            className="flex items-end gap-1 border-b border-[#E0DED8] bg-white sticky top-[68px] z-30"
        >
            <div className="max-w-6xl mx-auto px-6 w-full flex items-end gap-1">
                {tabs.map((t) => {
                    const isActive = t.id === activeId;
                    return (
                        <button
                            key={t.id}
                            type="button"
                            role="tab"
                            aria-selected={isActive}
                            aria-controls={`tab-panel-${t.id}`}
                            id={`tab-${t.id}`}
                            onClick={() => onChange(t.id)}
                            className={`
                                relative px-4 py-2.5 text-sm font-semibold transition-colors
                                border-b-2 -mb-px
                                ${isActive
                                    ? 'text-[#1A4D2E] border-[#1A4D2E]'
                                    : 'text-[#6B6B6B] border-transparent hover:text-[#1A2E1F] hover:border-[#E0DED8]'}
                            `}
                        >
                            <span className="flex items-center gap-2">
                                {t.icon && <t.icon className="h-4 w-4" />}
                                {t.label}
                                {t.badge != null && t.badge > 0 && (
                                    <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-semibold ${
                                        isActive
                                            ? 'bg-[#1A4D2E] text-white'
                                            : 'bg-[#E0DED8] text-[#4A4A4A]'
                                    }`}>
                                        {t.badge}
                                    </span>
                                )}
                            </span>
                        </button>
                    );
                })}
            </div>
        </nav>
    );
};

export default TabBar;
