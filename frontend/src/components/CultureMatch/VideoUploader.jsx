import React, { useState } from 'react';
import { VideoCameraIcon } from '@heroicons/react/24/outline';

const VideoUploader = ({ onUpload, processing }) => {
    const [dragActive, setDragActive] = useState(false);

    const handleDrag = (e) => {
        e.preventDefault();
        e.stopPropagation();
        if (e.type === "dragenter" || e.type === "dragover") {
            setDragActive(true);
        } else if (e.type === "dragleave") {
            setDragActive(false);
        }
    };

    const handleDrop = (e) => {
        e.preventDefault();
        e.stopPropagation();
        setDragActive(false);
        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
            onUpload(e.dataTransfer.files[0]);
        }
    };

    return (
        <div
            className={`relative border-2 border-dashed rounded-xl p-12 text-center transition-colors ${dragActive ? 'border-blue-500 bg-blue-50' : 'border-gray-300 hover:border-blue-400'
                } ${processing ? 'opacity-50 pointer-events-none' : ''}`}
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
        >
            <div className="flex flex-col items-center gap-4">
                <div className="p-4 rounded-full bg-blue-100 text-blue-600">
                    <VideoCameraIcon className="w-10 h-10" />
                </div>
                <div>
                    <h3 className="text-xl font-semibold text-gray-900">Record or Upload Your Vibe</h3>
                    <p className="text-gray-500 mt-2 max-w-sm mx-auto">
                        Upload a 30s video introducing yourself. Our multimodal AI analyzes your personality to find your campus culture match.
                    </p>
                </div>
                <button
                    className="mt-2 px-6 py-3 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition-colors shadow-sm flex items-center gap-2"
                    onClick={() => document.getElementById('video-input').click()}
                    disabled={processing}
                >
                    Select Video File
                </button>
                <p className="text-xs text-gray-400 mt-2">Supports MP4, MOV, WebM (Max 50MB)</p>
                <input
                    type="file"
                    id="video-input"
                    className="hidden"
                    accept="video/*"
                    onChange={(e) => e.target.files[0] && onUpload(e.target.files[0])}
                />
            </div>
        </div>
    );
};
export default VideoUploader;
