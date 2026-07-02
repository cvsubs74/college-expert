import React, { useState, useEffect, useCallback } from 'react';
import { ScaleIcon } from '@heroicons/react/24/outline';
import { useAuth } from '../context/AuthContext';
import { getOutcomeCalibration, setApplicationDecision } from '../services/api';
import DecisionLedger from '../components/stratia/DecisionLedger';

// ============================================================================
// DECISION LEDGER PAGE (#312) — promotes the Decision Ledger (predicted fit vs
// actual admission outcome) from a buried block on the Launchpad to its own
// sidebar route. Loads outcome calibration and hands off to the unchanged
// DecisionLedger component; recording a decision re-syncs from the server
// (authoritative decided_count + ordering), same behavior as the Launchpad.
// ============================================================================

const DecisionLedgerPage = () => {
    const { currentUser } = useAuth();
    const [calibration, setCalibration] = useState({ outcomes: [], decided_count: 0, total: 0 });
    const [loading, setLoading] = useState(true);

    const reload = useCallback(async () => {
        if (!currentUser?.email) { setLoading(false); return; }
        const res = await getOutcomeCalibration(currentUser.email);
        if (res?.success) setCalibration(res);
        setLoading(false);
    }, [currentUser?.email]);

    useEffect(() => { reload(); }, [reload]);

    const handleSetDecision = async (universityId, decision) => {
        if (!currentUser?.email) return;
        // Optimistic, then re-sync (server recomputes decided_count + ordering).
        setCalibration((prev) => ({
            ...prev,
            outcomes: (prev.outcomes || []).map((o) =>
                o.university_id === universityId ? { ...o, decision: decision || null } : o),
        }));
        await setApplicationDecision(currentUser.email, universityId, decision);
        reload();
    };

    return (
        <div className="max-w-4xl mx-auto p-4 sm:p-6">
            <div className="flex items-center gap-3 mb-2">
                <div className="h-10 w-10 rounded-xl bg-[#D6E8D5] flex items-center justify-center">
                    <ScaleIcon className="h-6 w-6 text-[#1A4D2E]" />
                </div>
                <div>
                    <h1 className="font-serif text-2xl font-semibold text-[#2C2C2C]">Decision Ledger</h1>
                    <p className="text-sm text-[#6B6B6B]">
                        Record real admission outcomes and see how Stratia's fit calls held up — predicted vs actual.
                    </p>
                </div>
            </div>

            {loading ? (
                <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100 mt-6" data-testid="decision-ledger-loading">
                    <div className="animate-pulse space-y-3">
                        <div className="h-5 bg-gray-200 rounded w-1/3" />
                        <div className="h-20 bg-gray-100 rounded" />
                    </div>
                </div>
            ) : calibration.outcomes.length > 0 ? (
                <div className="mt-4">
                    <DecisionLedger outcomes={calibration.outcomes} onSetDecision={handleSetDecision} />
                </div>
            ) : (
                <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100 mt-6" data-testid="decision-ledger-empty">
                    <p className="text-sm text-gray-700">
                        Once you've added colleges and recorded admission decisions, this ledger
                        will show how Stratia's predicted fit compared to your real outcomes.
                    </p>
                </div>
            )}
        </div>
    );
};

export default DecisionLedgerPage;
