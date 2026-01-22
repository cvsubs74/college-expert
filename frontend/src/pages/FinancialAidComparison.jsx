import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { getAidPackages, saveAidPackage, getCollegeList } from '../services/api';
import {
    CurrencyDollarIcon,
    PlusIcon,
    ArrowPathIcon,
    ChartBarIcon,
    ExclamationTriangleIcon,
    CheckCircleIcon,
    XMarkIcon
} from '@heroicons/react/24/outline';

const FinancialAidComparison = ({ embedded = false }) => {
    const { currentUser: user } = useAuth();
    const [packages, setPackages] = useState([]);
    const [collegeList, setCollegeList] = useState([]);
    const [isLoading, setIsLoading] = useState(true);
    const [showAddModal, setShowAddModal] = useState(false);
    const [selectedSchool, setSelectedSchool] = useState(null);
    const [editingPackage, setEditingPackage] = useState(null);

    useEffect(() => {
        loadData();
    }, [user]);

    const loadData = async () => {
        if (!user?.email) return;
        setIsLoading(true);
        try {
            const [aidResult, listResult] = await Promise.all([
                getAidPackages(user.email),
                getCollegeList(user.email)
            ]);

            if (aidResult.success) {
                setPackages(aidResult.packages || []);
            }
            if (listResult.success) {
                setCollegeList(listResult.colleges || []);
            }
        } catch (error) {
            console.error('Failed to load data:', error);
        } finally {
            setIsLoading(false);
        }
    };

    const handleSavePackage = async (packageData) => {
        if (!user?.email || !selectedSchool) return;

        const result = await saveAidPackage(user.email, selectedSchool.university_id, packageData);
        if (result.success) {
            loadData();
            setShowAddModal(false);
            setSelectedSchool(null);
            setEditingPackage(null);
        }
    };

    // Sort packages by net cost
    const sortedPackages = [...packages].sort((a, b) => (a.net_cost || 0) - (b.net_cost || 0));

    // Find best value
    const bestValue = sortedPackages.length > 0 ? sortedPackages[0] : null;

    // Format currency
    const formatCurrency = (amount) => {
        if (!amount && amount !== 0) return '—';
        return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(amount);
    };

    return (
        <div className={embedded ? '' : 'min-h-screen bg-gradient-to-b from-[#FDFCF7] to-stone-50'}>
            <div className={embedded ? '' : 'max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8'}>
                {/* Header - hidden when embedded */}
                {!embedded ? (
                    <div className="flex justify-between items-start mb-8">
                        <div>
                            <h1 className="text-3xl font-serif font-medium text-[#1A4D2E]">Financial Aid Comparison</h1>
                            <p className="text-stone-600 mt-2">Compare aid packages across your admitted schools.</p>
                        </div>
                        <button
                            onClick={() => setShowAddModal(true)}
                            className="flex items-center gap-2 px-4 py-2 bg-[#1A4D2E] text-white rounded-lg hover:bg-[#2D6A4F] transition-colors"
                        >
                            <PlusIcon className="h-5 w-5" />
                            Add Package
                        </button>
                    </div>
                ) : (
                    <div className="flex justify-end mb-4">
                        <button
                            onClick={() => setShowAddModal(true)}
                            className="flex items-center gap-2 px-4 py-2 bg-[#1A4D2E] text-white rounded-lg hover:bg-[#2D6A4F] transition-colors"
                        >
                            <PlusIcon className="h-5 w-5" />
                            Add Package
                        </button>
                    </div>
                )}

                {/* Summary Cards */}
                {packages.length > 0 && (
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
                        <div className="bg-emerald-50 rounded-xl p-5 border border-emerald-200">
                            <div className="flex items-center gap-3">
                                <div className="p-2 bg-emerald-100 rounded-lg">
                                    <CheckCircleIcon className="h-6 w-6 text-emerald-600" />
                                </div>
                                <div>
                                    <div className="text-sm text-emerald-600 font-medium">Best Value</div>
                                    <div className="text-lg font-bold text-emerald-800">{bestValue?.university_name || bestValue?.university_id}</div>
                                    <div className="text-2xl font-bold text-emerald-700">{formatCurrency(bestValue?.net_cost)}/yr</div>
                                </div>
                            </div>
                        </div>

                        <div className="bg-white rounded-xl p-5 border border-stone-200">
                            <div className="text-sm text-stone-500">Packages Entered</div>
                            <div className="text-3xl font-bold text-stone-800">{packages.length}</div>
                            <div className="text-sm text-stone-500 mt-1">of {collegeList.length} schools</div>
                        </div>

                        <div className="bg-white rounded-xl p-5 border border-stone-200">
                            <div className="text-sm text-stone-500">Average Net Cost</div>
                            <div className="text-3xl font-bold text-stone-800">
                                {formatCurrency(packages.length > 0
                                    ? packages.reduce((sum, p) => sum + (p.net_cost || 0), 0) / packages.length
                                    : 0)}
                            </div>
                            <div className="text-sm text-stone-500 mt-1">per year</div>
                        </div>
                    </div>
                )}

                {/* Comparison Table */}
                {isLoading ? (
                    <div className="text-center py-12">
                        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#1A4D2E] mx-auto"></div>
                        <p className="text-stone-500 mt-4">Loading aid packages...</p>
                    </div>
                ) : packages.length === 0 ? (
                    <div className="text-center py-12 bg-white rounded-xl border border-stone-200">
                        <CurrencyDollarIcon className="h-12 w-12 text-stone-300 mx-auto" />
                        <h3 className="mt-4 text-lg font-medium text-stone-700">No Aid Packages Yet</h3>
                        <p className="text-stone-500 mt-2 mb-4">Add your financial aid packages to compare costs.</p>
                        <button
                            onClick={() => setShowAddModal(true)}
                            className="inline-flex items-center gap-2 px-4 py-2 bg-[#1A4D2E] text-white rounded-lg hover:bg-[#2D6A4F]"
                        >
                            <PlusIcon className="h-5 w-5" />
                            Add Your First Package
                        </button>
                    </div>
                ) : (
                    <div className="bg-white rounded-xl border border-stone-200 overflow-hidden shadow-sm">
                        <div className="overflow-x-auto">
                            <table className="w-full">
                                <thead className="bg-stone-50 border-b border-stone-200">
                                    <tr>
                                        <th className="text-left px-6 py-4 text-sm font-semibold text-stone-600">School</th>
                                        <th className="text-right px-4 py-4 text-sm font-semibold text-stone-600">COA</th>
                                        <th className="text-right px-4 py-4 text-sm font-semibold text-emerald-600">Grants</th>
                                        <th className="text-right px-4 py-4 text-sm font-semibold text-amber-600">Loans</th>
                                        <th className="text-right px-4 py-4 text-sm font-semibold text-stone-600">Work Study</th>
                                        <th className="text-right px-4 py-4 text-sm font-semibold text-[#1A4D2E]">Net Cost</th>
                                        <th className="px-4 py-4"></th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-stone-100">
                                    {sortedPackages.map((pkg, index) => (
                                        <tr
                                            key={pkg.university_id}
                                            className={`hover:bg-stone-50 ${index === 0 ? 'bg-emerald-50/50' : ''}`}
                                        >
                                            <td className="px-6 py-4">
                                                <div className="flex items-center gap-2">
                                                    {index === 0 && (
                                                        <span className="px-2 py-0.5 bg-emerald-100 text-emerald-700 text-xs font-medium rounded-full">
                                                            Best Value
                                                        </span>
                                                    )}
                                                    <span className="font-medium text-stone-800">
                                                        {pkg.university_name || pkg.university_id}
                                                    </span>
                                                </div>
                                            </td>
                                            <td className="text-right px-4 py-4 text-stone-600">
                                                {formatCurrency(pkg.cost_of_attendance)}
                                            </td>
                                            <td className="text-right px-4 py-4 text-emerald-600 font-medium">
                                                -{formatCurrency(pkg.grants_scholarships)}
                                            </td>
                                            <td className="text-right px-4 py-4 text-amber-600">
                                                {formatCurrency(pkg.loans_offered)}
                                            </td>
                                            <td className="text-right px-4 py-4 text-stone-500">
                                                {formatCurrency(pkg.work_study)}
                                            </td>
                                            <td className="text-right px-4 py-4">
                                                <span className="font-bold text-[#1A4D2E] text-lg">
                                                    {formatCurrency(pkg.net_cost)}
                                                </span>
                                            </td>
                                            <td className="px-4 py-4">
                                                <button
                                                    onClick={() => {
                                                        setEditingPackage(pkg);
                                                        setSelectedSchool({ university_id: pkg.university_id, university_name: pkg.university_name });
                                                        setShowAddModal(true);
                                                    }}
                                                    className="text-stone-400 hover:text-[#1A4D2E]"
                                                >
                                                    Edit
                                                </button>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>
                )}

                {/* 4-Year Cost Comparison */}
                {packages.length > 1 && (
                    <div className="mt-8 bg-white rounded-xl p-6 border border-stone-200">
                        <h3 className="text-lg font-semibold text-stone-800 mb-4">4-Year Total Cost</h3>
                        <div className="space-y-3">
                            {sortedPackages.slice(0, 5).map((pkg, index) => {
                                const fourYearCost = (pkg.net_cost || 0) * 4;
                                const maxCost = Math.max(...sortedPackages.map(p => (p.net_cost || 0) * 4));
                                const widthPercent = maxCost > 0 ? (fourYearCost / maxCost) * 100 : 0;

                                return (
                                    <div key={pkg.university_id} className="flex items-center gap-4">
                                        <div className="w-40 text-sm font-medium text-stone-700 truncate">
                                            {pkg.university_name || pkg.university_id}
                                        </div>
                                        <div className="flex-1 h-8 bg-stone-100 rounded-lg overflow-hidden">
                                            <div
                                                className={`h-full flex items-center justify-end px-3 text-white text-sm font-medium
                                                    ${index === 0 ? 'bg-emerald-500' : 'bg-stone-400'}`}
                                                style={{ width: `${widthPercent}%` }}
                                            >
                                                {formatCurrency(fourYearCost)}
                                            </div>
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                )}
            </div>

            {/* Add/Edit Modal */}
            {showAddModal && (
                <AidPackageModal
                    colleges={collegeList.filter(c => !packages.find(p => p.university_id === c.university_id) || selectedSchool?.university_id === c.university_id)}
                    selectedSchool={selectedSchool}
                    editingPackage={editingPackage}
                    onSelectSchool={setSelectedSchool}
                    onSave={handleSavePackage}
                    onClose={() => {
                        setShowAddModal(false);
                        setSelectedSchool(null);
                        setEditingPackage(null);
                    }}
                />
            )}
        </div>
    );
};

// Modal Component
const AidPackageModal = ({ colleges, selectedSchool, editingPackage, onSelectSchool, onSave, onClose }) => {
    const [formData, setFormData] = useState({
        cost_of_attendance: editingPackage?.cost_of_attendance || '',
        grants_scholarships: editingPackage?.grants_scholarships || '',
        loans_offered: editingPackage?.loans_offered || '',
        work_study: editingPackage?.work_study || '',
        notes: editingPackage?.notes || ''
    });

    const handleChange = (field, value) => {
        setFormData(prev => ({ ...prev, [field]: value }));
    };

    const netCost = (parseFloat(formData.cost_of_attendance) || 0) - (parseFloat(formData.grants_scholarships) || 0);

    const handleSubmit = () => {
        onSave({
            university_name: selectedSchool?.university_name || selectedSchool?.university_id,
            cost_of_attendance: parseFloat(formData.cost_of_attendance) || 0,
            grants_scholarships: parseFloat(formData.grants_scholarships) || 0,
            loans_offered: parseFloat(formData.loans_offered) || 0,
            work_study: parseFloat(formData.work_study) || 0,
            net_cost: netCost,
            notes: formData.notes
        });
    };

    return (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-2xl w-full max-w-lg shadow-xl">
                <div className="flex justify-between items-center p-6 border-b border-stone-200">
                    <h2 className="text-xl font-semibold text-stone-800">
                        {editingPackage ? 'Edit Aid Package' : 'Add Aid Package'}
                    </h2>
                    <button onClick={onClose} className="text-stone-400 hover:text-stone-600">
                        <XMarkIcon className="h-6 w-6" />
                    </button>
                </div>

                <div className="p-6 space-y-4">
                    {/* School Selector */}
                    {!editingPackage && (
                        <div>
                            <label className="block text-sm font-medium text-stone-700 mb-2">School</label>
                            <select
                                value={selectedSchool?.university_id || ''}
                                onChange={(e) => {
                                    const school = colleges.find(c => c.university_id === e.target.value);
                                    onSelectSchool(school);
                                }}
                                className="w-full px-4 py-2 border border-stone-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#1A4D2E]/20"
                            >
                                <option value="">Select a school...</option>
                                {colleges.map(c => (
                                    <option key={c.university_id} value={c.university_id}>
                                        {c.university_name || c.university_id}
                                    </option>
                                ))}
                            </select>
                        </div>
                    )}

                    {/* Cost of Attendance */}
                    <div>
                        <label className="block text-sm font-medium text-stone-700 mb-2">Cost of Attendance (per year)</label>
                        <div className="relative">
                            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-stone-400">$</span>
                            <input
                                type="number"
                                value={formData.cost_of_attendance}
                                onChange={(e) => handleChange('cost_of_attendance', e.target.value)}
                                className="w-full pl-8 pr-4 py-2 border border-stone-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#1A4D2E]/20"
                                placeholder="82000"
                            />
                        </div>
                    </div>

                    {/* Grants & Scholarships */}
                    <div>
                        <label className="block text-sm font-medium text-emerald-700 mb-2">Grants & Scholarships (free money)</label>
                        <div className="relative">
                            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-stone-400">$</span>
                            <input
                                type="number"
                                value={formData.grants_scholarships}
                                onChange={(e) => handleChange('grants_scholarships', e.target.value)}
                                className="w-full pl-8 pr-4 py-2 border border-emerald-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500/20 bg-emerald-50/50"
                                placeholder="45000"
                            />
                        </div>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                        {/* Loans */}
                        <div>
                            <label className="block text-sm font-medium text-amber-700 mb-2">Loans Offered</label>
                            <div className="relative">
                                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-stone-400">$</span>
                                <input
                                    type="number"
                                    value={formData.loans_offered}
                                    onChange={(e) => handleChange('loans_offered', e.target.value)}
                                    className="w-full pl-8 pr-4 py-2 border border-stone-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#1A4D2E]/20"
                                    placeholder="5500"
                                />
                            </div>
                        </div>

                        {/* Work Study */}
                        <div>
                            <label className="block text-sm font-medium text-stone-700 mb-2">Work Study</label>
                            <div className="relative">
                                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-stone-400">$</span>
                                <input
                                    type="number"
                                    value={formData.work_study}
                                    onChange={(e) => handleChange('work_study', e.target.value)}
                                    className="w-full pl-8 pr-4 py-2 border border-stone-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#1A4D2E]/20"
                                    placeholder="3000"
                                />
                            </div>
                        </div>
                    </div>

                    {/* Net Cost Preview */}
                    <div className="bg-stone-50 rounded-lg p-4 border border-stone-200">
                        <div className="flex justify-between items-center">
                            <span className="text-stone-600">Net Cost (COA - Grants)</span>
                            <span className="text-2xl font-bold text-[#1A4D2E]">
                                ${netCost.toLocaleString()}/yr
                            </span>
                        </div>
                        <div className="text-sm text-stone-500 mt-1">
                            ~${(netCost * 4).toLocaleString()} over 4 years
                        </div>
                    </div>

                    {/* Notes */}
                    <div>
                        <label className="block text-sm font-medium text-stone-700 mb-2">Notes</label>
                        <textarea
                            value={formData.notes}
                            onChange={(e) => handleChange('notes', e.target.value)}
                            className="w-full px-4 py-2 border border-stone-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#1A4D2E]/20"
                            rows={2}
                            placeholder="e.g., Merit scholarship, renewable if GPA > 3.0"
                        />
                    </div>
                </div>

                <div className="flex justify-end gap-3 p-6 border-t border-stone-200">
                    <button
                        onClick={onClose}
                        className="px-4 py-2 text-stone-600 hover:text-stone-800"
                    >
                        Cancel
                    </button>
                    <button
                        onClick={handleSubmit}
                        disabled={!selectedSchool}
                        className="px-6 py-2 bg-[#1A4D2E] text-white rounded-lg hover:bg-[#2D6A4F] disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        Save Package
                    </button>
                </div>
            </div>
        </div>
    );
};

export default FinancialAidComparison;
