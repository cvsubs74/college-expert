
import React, { useState, useEffect } from 'react';
import { CheckCircleIcon, CalendarIcon, ExclamationCircleIcon, SparklesIcon, ArrowPathIcon } from '@heroicons/react/24/outline';
import { CheckCircleIcon as CheckCircleSolidIcon } from '@heroicons/react/24/solid';
import { useAuth } from '../../context/AuthContext';
import { markRoadmapTask, getRoadmapTasks, generateRoadmapTasks, updateTaskStatus } from '../../services/api';

// Helper to calculate days until due and urgency color
const getDaysUntil = (dateStr) => {
    if (!dateStr) return null;
    const dueDate = new Date(dateStr);
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    dueDate.setHours(0, 0, 0, 0);
    return Math.ceil((dueDate - today) / (1000 * 60 * 60 * 24));
};

const getUrgencyColor = (daysUntil) => {
    if (daysUntil === null) return 'stone';
    if (daysUntil < 0) return 'red'; // Overdue
    if (daysUntil <= 3) return 'red';
    if (daysUntil <= 7) return 'amber';
    return 'emerald';
};

const RoadmapView = ({ roadmap, isLoading, error, initialProgress = {} }) => {
    const { currentUser: user } = useAuth();
    const [completedTasks, setCompletedTasks] = useState(initialProgress);
    const [savingTask, setSavingTask] = useState(null);
    const [personalizedTasks, setPersonalizedTasks] = useState([]);
    const [isLoadingTasks, setIsLoadingTasks] = useState(false);
    const [isGenerating, setIsGenerating] = useState(false);

    // Update state when initialProgress changes (e.g., fetched from server)
    useEffect(() => {
        if (initialProgress && Object.keys(initialProgress).length > 0) {
            setCompletedTasks(initialProgress);
        }
    }, [initialProgress]);

    const handleToggleTask = async (taskId) => {
        if (!user?.email) return;

        const isCurrentlyCompleted = completedTasks[taskId]?.completed || false;
        const newCompleted = !isCurrentlyCompleted;

        // Optimistic update
        setCompletedTasks(prev => ({
            ...prev,
            [taskId]: { completed: newCompleted }
        }));
        setSavingTask(taskId);

        try {
            const result = await markRoadmapTask(user.email, taskId, newCompleted);
            if (!result.success) {
                // Revert on failure
                setCompletedTasks(prev => ({
                    ...prev,
                    [taskId]: { completed: isCurrentlyCompleted }
                }));
            }
        } catch (err) {
            // Revert on error
            setCompletedTasks(prev => ({
                ...prev,
                [taskId]: { completed: isCurrentlyCompleted }
            }));
        } finally {
            setSavingTask(null);
        }
    };

    // Load personalized tasks on mount
    useEffect(() => {
        const loadPersonalizedTasks = async () => {
            if (!user?.email) return;
            setIsLoadingTasks(true);
            try {
                const result = await getRoadmapTasks(user.email, 'pending');
                if (result.success && result.tasks) {
                    setPersonalizedTasks(result.tasks);
                }
            } catch (err) {
                console.error('Failed to load personalized tasks:', err);
            } finally {
                setIsLoadingTasks(false);
            }
        };
        loadPersonalizedTasks();
    }, [user]);

    // Generate personalized tasks
    const handleGenerateTasks = async () => {
        if (!user?.email) return;
        setIsGenerating(true);
        try {
            const result = await generateRoadmapTasks(user.email);
            if (result.success && result.tasks) {
                setPersonalizedTasks(result.tasks.filter(t => t.status === 'pending'));
            }
        } catch (err) {
            console.error('Failed to generate tasks:', err);
        } finally {
            setIsGenerating(false);
        }
    };

    // Mark personalized task complete
    const handleCompleteTask = async (taskId) => {
        if (!user?.email) return;
        setSavingTask(taskId);
        try {
            const result = await updateTaskStatus(user.email, taskId, 'completed');
            if (result.success) {
                setPersonalizedTasks(prev => prev.filter(t => t.task_id !== taskId));
            }
        } catch (err) {
            console.error('Failed to complete task:', err);
        } finally {
            setSavingTask(null);
        }
    };

    // Calculate progress
    const totalTasks = roadmap?.phases?.reduce((sum, phase) => sum + (phase.tasks?.length || 0), 0) || 0;
    const completedCount = Object.values(completedTasks).filter(t => t?.completed).length;
    const progressPercent = totalTasks > 0 ? Math.round((completedCount / totalTasks) * 100) : 0;

    if (isLoading) {
        return (
            <div className="flex items-center justify-center h-full">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#1A4D2E]"></div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="p-6 bg-red-50 text-red-700 rounded-lg">
                <p>Error loading roadmap: {error}</p>
            </div>
        );
    }

    if (!roadmap) {
        return <div className="p-6 text-gray-500">No roadmap available.</div>;
    }

    return (
        <div className="bg-white/80 backdrop-blur-sm rounded-2xl border border-stone-200 shadow-sm overflow-hidden h-full flex flex-col">
            {/* Header with Progress */}
            <div className="p-6 border-b border-stone-100 bg-[#FDFCF7]">
                <h2 className="text-xl font-serif text-[#1A4D2E] font-medium">{roadmap.title}</h2>
                <p className="text-sm text-stone-500 mt-1">Your personalized guide to admissions success.</p>

                {/* Progress Bar */}
                <div className="mt-4">
                    <div className="flex justify-between text-xs text-stone-500 mb-1">
                        <span>{completedCount} of {totalTasks} tasks complete</span>
                        <span className="font-medium text-[#1A4D2E]">{progressPercent}%</span>
                    </div>
                    <div className="h-2 bg-stone-200 rounded-full overflow-hidden">
                        <div
                            className="h-full bg-gradient-to-r from-[#1A4D2E] to-[#2D6A4F] transition-all duration-500 ease-out rounded-full"
                            style={{ width: `${progressPercent}%` }}
                        />
                    </div>
                </div>
            </div>

            {/* Personalized University Tasks Section */}
            {(personalizedTasks.length > 0 || !isLoadingTasks) && (
                <div className="p-4 border-b border-stone-100 bg-gradient-to-r from-amber-50/50 to-orange-50/50">
                    <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center gap-2">
                            <SparklesIcon className="h-5 w-5 text-amber-600" />
                            <h3 className="font-medium text-stone-800">Your Upcoming Deadlines</h3>
                        </div>
                        <button
                            onClick={handleGenerateTasks}
                            disabled={isGenerating}
                            className="flex items-center gap-1 text-xs text-amber-700 hover:text-amber-900 transition-colors"
                        >
                            <ArrowPathIcon className={`h-4 w-4 ${isGenerating ? 'animate-spin' : ''}`} />
                            {isGenerating ? 'Generating...' : 'Refresh Tasks'}
                        </button>
                    </div>

                    {isLoadingTasks ? (
                        <div className="text-center py-4 text-stone-400 text-sm">Loading tasks...</div>
                    ) : personalizedTasks.length === 0 ? (
                        <div className="text-center py-4">
                            <p className="text-stone-500 text-sm">No upcoming tasks. Click "Refresh Tasks" to generate from your college list.</p>
                        </div>
                    ) : (
                        <div className="space-y-2 max-h-64 overflow-y-auto">
                            {personalizedTasks.slice(0, 8).map((task) => {
                                const daysUntil = getDaysUntil(task.due_date);
                                const urgency = getUrgencyColor(daysUntil);
                                const isSaving = savingTask === task.task_id;

                                return (
                                    <div
                                        key={task.task_id}
                                        className={`p-3 rounded-lg border flex items-start gap-3 transition-all
                                            ${urgency === 'red' ? 'bg-red-50 border-red-200' :
                                                urgency === 'amber' ? 'bg-amber-50 border-amber-200' :
                                                    'bg-emerald-50 border-emerald-200'}`}
                                    >
                                        <button
                                            onClick={() => handleCompleteTask(task.task_id)}
                                            disabled={isSaving}
                                            className={`mt-0.5 text-stone-300 hover:text-emerald-600 transition-colors ${isSaving ? 'opacity-50' : ''}`}
                                        >
                                            <CheckCircleIcon className="h-5 w-5" />
                                        </button>
                                        <div className="flex-1 min-w-0">
                                            <p className="text-sm font-medium text-stone-800 truncate">{task.title}</p>
                                            <div className="flex items-center gap-2 mt-1">
                                                <span className={`text-xs font-medium px-2 py-0.5 rounded-full
                                                    ${urgency === 'red' ? 'bg-red-100 text-red-700' :
                                                        urgency === 'amber' ? 'bg-amber-100 text-amber-700' :
                                                            'bg-emerald-100 text-emerald-700'}`}>
                                                    {daysUntil < 0 ? `${Math.abs(daysUntil)}d overdue` :
                                                        daysUntil === 0 ? 'Due today' :
                                                            daysUntil === 1 ? 'Due tomorrow' :
                                                                `${daysUntil} days left`}
                                                </span>
                                                {task.university_name && (
                                                    <span className="text-xs text-stone-500 truncate">{task.university_name}</span>
                                                )}
                                            </div>
                                        </div>
                                        {urgency === 'red' && (
                                            <ExclamationCircleIcon className="h-5 w-5 text-red-500 flex-shrink-0" />
                                        )}
                                    </div>
                                );
                            })}
                        </div>
                    )}
                </div>
            )}

            {/* Phases */}
            <div className="flex-1 overflow-y-auto p-6 space-y-8">
                {roadmap.phases.map((phase, index) => (
                    <div key={phase.id} className="relative pl-8 border-l-2 border-stone-200 last:border-0">
                        {/* Timeline Dot */}
                        <div className="absolute -left-[9px] top-0 h-4 w-4 rounded-full bg-[#1A4D2E] ring-4 ring-white"></div>

                        <div className="mb-2">
                            <h3 className="text-lg font-medium text-stone-800">{phase.name}</h3>
                            <div className="flex items-center text-xs text-stone-500 mt-0.5">
                                <CalendarIcon className="h-3 w-3 mr-1" />
                                <span>{phase.date_range}</span>
                            </div>
                        </div>

                        {/* Tasks */}
                        <div className="space-y-3 mt-4">
                            {phase.tasks.map((task) => {
                                const isCompleted = completedTasks[task.id]?.completed || false;
                                const isSaving = savingTask === task.id;

                                return (
                                    <div
                                        key={task.id}
                                        className={`
                                            group p-3 rounded-lg border transition-all duration-200 
                                            ${isCompleted ? 'bg-green-50/50 border-green-200' :
                                                task.type === 'deadline'
                                                    ? 'bg-amber-50/50 border-amber-200 hover:border-amber-300'
                                                    : 'bg-white border-stone-100 hover:border-[#1A4D2E]/20 hover:shadow-sm'}
                                        `}
                                    >
                                        <div className="flex items-start gap-3">
                                            <button
                                                className={`mt-0.5 transition-colors ${isSaving ? 'opacity-50' : ''} ${isCompleted ? 'text-green-600' : 'text-stone-300 hover:text-[#1A4D2E]'}`}
                                                onClick={() => handleToggleTask(task.id)}
                                                disabled={isSaving}
                                            >
                                                {isCompleted ? (
                                                    <CheckCircleSolidIcon className="h-5 w-5" />
                                                ) : (
                                                    <CheckCircleIcon className="h-5 w-5" />
                                                )}
                                            </button>
                                            <div className="flex-1">
                                                <p className={`text-sm font-medium ${isCompleted ? 'text-green-700 line-through' : task.type === 'deadline' ? 'text-amber-900' : 'text-stone-700'}`}>
                                                    {task.title}
                                                </p>
                                                {task.due_date && (
                                                    <p className="text-xs text-amber-600/80 mt-1 font-medium">Due: {task.due_date}</p>
                                                )}
                                            </div>
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
};

export default RoadmapView;
