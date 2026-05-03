import React, { useState } from 'react';
import { ChevronDownIcon, ChevronUpIcon, CheckCircleIcon, XCircleIcon } from '@heroicons/react/24/outline';

// Single step inside a scenario detail. Collapsed shows status, name,
// elapsed; expanded shows assertions + request + response excerpt.

const fmtMs = (ms) => (ms == null ? '—' : ms < 1000 ? `${ms}ms` : `${(ms / 1000).toFixed(1)}s`);

const StepRow = ({ step }) => {
    const [open, setOpen] = useState(!step.passed);
    const Icon = step.passed ? CheckCircleIcon : XCircleIcon;
    const iconCls = step.passed ? 'text-emerald-600' : 'text-rose-600';

    return (
        <div className={`border rounded-lg ${step.passed ? 'border-[#E0DED8]' : 'border-rose-200 bg-rose-50/40'}`}>
            <button
                type="button"
                className="w-full flex items-center gap-3 px-4 py-3 text-left"
                onClick={() => setOpen(!open)}
            >
                <Icon className={`h-5 w-5 flex-shrink-0 ${iconCls}`} />
                <div className="flex-1 min-w-0">
                    <div className="flex items-baseline gap-2">
                        <span className="font-mono text-sm font-semibold text-[#2A2A2A] truncate">
                            {step.name}
                        </span>
                        <span className="text-xs text-[#8A8A8A]">
                            {step.status_code ?? '—'} · {fmtMs(step.elapsed_ms)}
                        </span>
                    </div>
                    <div className="text-xs text-[#6B6B6B] truncate">{step.endpoint || ''}</div>
                </div>
                {open ? (
                    <ChevronUpIcon className="h-4 w-4 text-[#8A8A8A]" />
                ) : (
                    <ChevronDownIcon className="h-4 w-4 text-[#8A8A8A]" />
                )}
            </button>

            {open && (
                <div className="px-4 pb-4 pt-1 space-y-3 text-xs">
                    {/* Assertions */}
                    {step.assertions?.length > 0 && (
                        <div>
                            <div className="text-[10px] uppercase tracking-wider font-semibold text-[#8A8A8A] mb-1">
                                Assertions
                            </div>
                            <ul className="space-y-1">
                                {step.assertions.map((a, i) => (
                                    <li key={i} className="flex items-start gap-2">
                                        <span
                                            className={`inline-block w-1.5 h-1.5 rounded-full mt-1.5 flex-shrink-0 ${a.passed ? 'bg-emerald-500' : 'bg-rose-500'}`}
                                        />
                                        <span className="font-mono text-[11px]">
                                            <span className={a.passed ? 'text-[#4A4A4A]' : 'text-rose-700'}>
                                                {a.name}
                                            </span>
                                            {a.message && (
                                                <span className="text-[#8A8A8A] ml-2">— {a.message}</span>
                                            )}
                                        </span>
                                    </li>
                                ))}
                            </ul>
                        </div>
                    )}

                    {/* Request */}
                    {step.request != null && (
                        <details>
                            <summary className="text-[10px] uppercase tracking-wider font-semibold text-[#8A8A8A] cursor-pointer hover:text-[#1A4D2E]">
                                Request
                            </summary>
                            <pre className="mt-1 bg-[#F8F6F0] border border-[#E0DED8] rounded-lg p-3 overflow-x-auto text-[11px] font-mono">
                                {JSON.stringify(step.request, null, 2)}
                            </pre>
                        </details>
                    )}

                    {/* Response excerpt */}
                    {step.response_excerpt && (
                        <details>
                            <summary className="text-[10px] uppercase tracking-wider font-semibold text-[#8A8A8A] cursor-pointer hover:text-[#1A4D2E]">
                                Response excerpt
                            </summary>
                            <pre className="mt-1 bg-[#F8F6F0] border border-[#E0DED8] rounded-lg p-3 overflow-x-auto text-[11px] font-mono whitespace-pre-wrap break-words">
                                {step.response_excerpt}
                            </pre>
                        </details>
                    )}
                </div>
            )}
        </div>
    );
};

export default StepRow;
