import React, { createContext, useContext, useState, useCallback } from 'react';
import { XMarkIcon, CheckCircleIcon, ExclamationCircleIcon, InformationCircleIcon, ArrowPathIcon } from '@heroicons/react/24/outline';

// Toast Context
const ToastContext = createContext(null);

export const useToast = () => {
    const context = useContext(ToastContext);
    if (!context) {
        throw new Error('useToast must be used within a ToastProvider');
    }
    return context;
};

// Toast types with styling
const toastStyles = {
    success: {
        bg: 'bg-emerald-50 border-emerald-200',
        icon: CheckCircleIcon,
        iconColor: 'text-emerald-500',
        textColor: 'text-emerald-800'
    },
    error: {
        bg: 'bg-red-50 border-red-200',
        icon: ExclamationCircleIcon,
        iconColor: 'text-red-500',
        textColor: 'text-red-800'
    },
    info: {
        bg: 'bg-blue-50 border-blue-200',
        icon: InformationCircleIcon,
        iconColor: 'text-blue-500',
        textColor: 'text-blue-800'
    },
    loading: {
        bg: 'bg-purple-50 border-purple-200',
        icon: ArrowPathIcon,
        iconColor: 'text-purple-500 animate-spin',
        textColor: 'text-purple-800'
    }
};

// Single Toast component
const Toast = ({ toast, onRemove }) => {
    const style = toastStyles[toast.type] || toastStyles.info;
    const Icon = style.icon;

    return (
        <div
            className={`flex items-center gap-3 px-4 py-3 rounded-xl border shadow-lg ${style.bg} animate-slide-in-right`}
            role="alert"
        >
            <Icon className={`h-5 w-5 flex-shrink-0 ${style.iconColor}`} />
            <div className="flex-1 min-w-0">
                <p className={`text-sm font-medium ${style.textColor}`}>{toast.title}</p>
                {toast.message && (
                    <p className={`text-xs ${style.textColor} opacity-80 mt-0.5`}>{toast.message}</p>
                )}
            </div>
            <button
                onClick={() => onRemove(toast.id)}
                className="p-1 hover:bg-white/50 rounded-full transition-colors"
            >
                <XMarkIcon className="h-4 w-4 text-gray-500" />
            </button>
        </div>
    );
};

// Toast Container
const ToastContainer = ({ toasts, removeToast }) => {
    if (toasts.length === 0) return null;

    return (
        <div className="fixed top-4 right-4 z-[100] flex flex-col gap-2 max-w-sm">
            {toasts.map((toast) => (
                <Toast key={toast.id} toast={toast} onRemove={removeToast} />
            ))}
        </div>
    );
};

// Toast Provider
export const ToastProvider = ({ children }) => {
    const [toasts, setToasts] = useState([]);

    const addToast = useCallback(({ type = 'info', title, message, duration = 5000 }) => {
        const id = Date.now() + Math.random();
        const newToast = { id, type, title, message };

        setToasts((prev) => [...prev, newToast]);

        // Auto-remove after duration (unless it's a loading toast)
        if (duration && type !== 'loading') {
            setTimeout(() => {
                removeToast(id);
            }, duration);
        }

        return id;
    }, []);

    const removeToast = useCallback((id) => {
        setToasts((prev) => prev.filter((t) => t.id !== id));
    }, []);

    const updateToast = useCallback((id, updates) => {
        setToasts((prev) =>
            prev.map((t) => (t.id === id ? { ...t, ...updates } : t))
        );
    }, []);

    // Convenience methods
    const toast = {
        success: (title, message, duration) => addToast({ type: 'success', title, message, duration }),
        error: (title, message, duration) => addToast({ type: 'error', title, message, duration }),
        info: (title, message, duration) => addToast({ type: 'info', title, message, duration }),
        loading: (title, message) => addToast({ type: 'loading', title, message, duration: 0 }),
        remove: removeToast,
        update: updateToast
    };

    return (
        <ToastContext.Provider value={toast}>
            {children}
            <ToastContainer toasts={toasts} removeToast={removeToast} />
        </ToastContext.Provider>
    );
};

export default ToastProvider;
