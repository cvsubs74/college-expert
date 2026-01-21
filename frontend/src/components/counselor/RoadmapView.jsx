
import React, { useState, useEffect } from 'react';
import { CheckCircleIcon, CalendarIcon, LockClosedIcon } from '@heroicons/react/24/outline';
import { CheckCircleIcon as CheckCircleSolidIcon } from '@heroicons/react/24/solid';
import { useAuth } from '../../context/AuthContext';
import { markRoadmapTask } from '../../services/api';

const RoadmapView = ({ roadmap, isLoading, error, initialProgress = {} }) => {
    const { currentUser: user } = useAuth();
    const [completedTasks, setCompletedTasks] = useState(initialProgress);
    const [savingTask, setSavingTask] = useState(null);

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
