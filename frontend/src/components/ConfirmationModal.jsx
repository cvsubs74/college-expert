import React from 'react';
import { ExclamationTriangleIcon, TrashIcon, XMarkIcon } from '@heroicons/react/24/outline';

/**
 * ConfirmationModal - A themed confirmation dialog to replace browser's native confirm()
 * 
 * @param {boolean} isOpen - Whether the modal is visible
 * @param {function} onClose - Called when modal is closed without confirming
 * @param {function} onConfirm - Called when user confirms the action
 * @param {string} title - Modal title (default: "Confirm Action")
 * @param {string} message - The confirmation message to display
 * @param {string} confirmText - Text for confirm button (default: "Confirm")
 * @param {string} cancelText - Text for cancel button (default: "Cancel")
 * @param {string} variant - "danger" for destructive actions, "warning" for caution (default: "danger")
 */
const ConfirmationModal = ({
    isOpen,
    onClose,
    onConfirm,
    title = "Confirm Action",
    message = "Are you sure you want to proceed?",
    confirmText = "Confirm",
    cancelText = "Cancel",
    variant = "danger"
}) => {
    if (!isOpen) return null;

    const variantStyles = {
        danger: {
            iconBg: "bg-red-100",
            iconColor: "text-red-600",
            confirmBg: "bg-red-600 hover:bg-red-700",
            Icon: TrashIcon
        },
        warning: {
            iconBg: "bg-amber-100",
            iconColor: "text-amber-600",
            confirmBg: "bg-amber-600 hover:bg-amber-700",
            Icon: ExclamationTriangleIcon
        }
    };

    const styles = variantStyles[variant] || variantStyles.danger;
    const { Icon } = styles;

    const handleConfirm = () => {
        onConfirm();
        onClose();
    };

    return (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm animate-in fade-in duration-200">
            <div className="w-full max-w-sm bg-white rounded-2xl shadow-2xl overflow-hidden animate-in zoom-in-95 duration-200">
                {/* Header */}
                <div className="px-6 pt-6 pb-0">
                    <div className="flex items-start gap-4">
                        <div className={`p-3 rounded-full ${styles.iconBg}`}>
                            <Icon className={`h-6 w-6 ${styles.iconColor}`} />
                        </div>
                        <div className="flex-1 pt-1">
                            <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
                            <p className="mt-2 text-sm text-gray-600">{message}</p>
                        </div>
                        <button
                            onClick={onClose}
                            className="p-1 -mr-1 -mt-1 hover:bg-gray-100 rounded-lg transition-colors"
                        >
                            <XMarkIcon className="h-5 w-5 text-gray-400" />
                        </button>
                    </div>
                </div>

                {/* Actions */}
                <div className="flex gap-3 px-6 py-4 mt-4 bg-gray-50 border-t border-gray-100">
                    <button
                        onClick={onClose}
                        className="flex-1 px-4 py-2.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
                    >
                        {cancelText}
                    </button>
                    <button
                        onClick={handleConfirm}
                        className={`flex-1 px-4 py-2.5 text-sm font-medium text-white rounded-lg transition-colors ${styles.confirmBg}`}
                    >
                        {confirmText}
                    </button>
                </div>
            </div>
        </div>
    );
};

export default ConfirmationModal;
