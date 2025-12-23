import React, { useState, useEffect } from 'react';
import { motion, useInView } from 'framer-motion';
import { useRef } from 'react';
import { demoDocuments } from '../../data/demoData';

const DocumentUploadDemo = () => {
    const ref = useRef(null);
    const isInView = useInView(ref, { once: true, amount: 0.5 });

    const [uploadComplete, setUploadComplete] = useState(false);
    const [documents, setDocuments] = useState([]);

    useEffect(() => {
        if (!isInView) return;

        // Start upload animation after 1s
        setTimeout(() => {
            setDocuments(demoDocuments.map(doc => ({ ...doc, progress: 0 })));

            // Animate progress for each document
            const interval = setInterval(() => {
                setDocuments(prev => {
                    const updated = prev.map(doc => {
                        if (doc.progress < 100) {
                            return { ...doc, progress: Math.min(doc.progress + 10, 100) };
                        }
                        return { ...doc, status: 'complete' };
                    });

                    // Check if all complete
                    if (updated.every(doc => doc.progress === 100)) {
                        clearInterval(interval);
                        setTimeout(() => setUploadComplete(true), 500);
                    }

                    return updated;
                });
            }, 200);

            return () => clearInterval(interval);
        }, 1000);
    }, [isInView]);

    return (
        <div ref={ref} className="w-full max-w-2xl mx-auto">
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={isInView ? { opacity: 1, y: 0 } : {}}
                transition={{ duration: 0.5 }}
                className="bg-white rounded-2xl shadow-2xl overflow-hidden border border-[#E0DED8]"
            >
                {/* Header */}
                <div className="bg-gradient-to-r from-[#1A4D2E] to-[#2D6B45] px-6 py-4">
                    <div className="flex items-center gap-3">
                        <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                        </svg>
                        <div>
                            <h3 className="text-white font-semibold">Upload Your Documents</h3>
                            <p className="text-white/80 text-sm">AI will extract your academic profile</p>
                        </div>
                    </div>
                </div>

                {/* Upload area */}
                <div className="p-6">
                    <div className="border-2 border-dashed border-[#E0DED8] rounded-xl p-8 mb-6 bg-[#FDFCF7]">
                        <div className="text-center">
                            <motion.div
                                className="w-16 h-16 rounded-full bg-[#D6E8D5] flex items-center justify-center mx-auto mb-4"
                                animate={documents.length > 0 ? { scale: [1, 1.1, 1] } : {}}
                                transition={{ duration: 0.5 }}
                            >
                                <svg className="w-8 h-8 text-[#1A4D2E]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                                </svg>
                            </motion.div>
                            <p className="text-[#4A4A4A] font-medium mb-1">
                                {documents.length === 0 ? 'Click to select files' : `${documents.length} file(s) selected`}
                            </p>
                            <p className="text-sm text-[#6B6B6B]">
                                PDF, DOCX, TXT • Multiple files supported
                            </p>
                        </div>
                    </div>

                    {/* Document list */}
                    {documents.length > 0 && (
                        <div className="space-y-3">
                            <h4 className="text-sm font-semibold text-[#4A4A4A] mb-3">
                                Processing Documents:
                            </h4>

                            {documents.map((doc, index) => (
                                <motion.div
                                    key={doc.name}
                                    initial={{ opacity: 0, x: -20 }}
                                    animate={{ opacity: 1, x: 0 }}
                                    transition={{ delay: index * 0.2 }}
                                    className="bg-[#F8F6F0] rounded-lg p-4 border border-[#E0DED8]"
                                >
                                    <div className="flex items-center gap-3 mb-3">
                                        <div className="w-10 h-10 rounded-lg bg-white flex items-center justify-center border border-[#E0DED8]">
                                            <svg className="w-5 h-5 text-[#C05838]" fill="currentColor" viewBox="0 0 20 20">
                                                <path fillRule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clipRule="evenodd" />
                                            </svg>
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <p className="text-sm font-medium text-[#1A4D2E] truncate">{doc.name}</p>
                                            <p className="text-xs text-[#6B6B6B]">{doc.size}</p>
                                        </div>
                                        {doc.progress === 100 ? (
                                            <motion.div
                                                initial={{ scale: 0 }}
                                                animate={{ scale: 1 }}
                                                className="w-6 h-6 rounded-full bg-[#2E7D32] flex items-center justify-center"
                                            >
                                                <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                                                </svg>
                                            </motion.div>
                                        ) : (
                                            <div className="text-xs font-medium text-[#FF8C42]">{doc.progress}%</div>
                                        )}
                                    </div>

                                    {/* Progress bar */}
                                    <div className="w-full h-2 bg-white rounded-full overflow-hidden">
                                        <motion.div
                                            className="h-full bg-gradient-to-r from-[#FF8C42] to-[#E67A2E]"
                                            initial={{ width: '0%' }}
                                            animate={{ width: `${doc.progress}%` }}
                                            transition={{ duration: 0.3 }}
                                        />
                                    </div>

                                    {/* Extracted data (appears when complete) */}
                                    {doc.progress === 100 && doc.extractedData && (
                                        <motion.div
                                            initial={{ opacity: 0, height: 0 }}
                                            animate={{ opacity: 1, height: 'auto' }}
                                            transition={{ delay: 0.3 }}
                                            className="mt-3 pt-3 border-t border-[#E0DED8]"
                                        >
                                            <p className="text-xs text-[#2E7D32] font-medium mb-2 flex items-center gap-1">
                                                <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                                                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                                                </svg>
                                                Extracted:
                                            </p>
                                            <div className="flex flex-wrap gap-2">
                                                {Object.entries(doc.extractedData).map(([key, value]) => (
                                                    <span
                                                        key={key}
                                                        className="px-2 py-1 bg-white rounded text-xs font-medium text-[#1A4D2E] border border-[#D6E8D5]"
                                                    >
                                                        {key}: {value}
                                                    </span>
                                                ))}
                                            </div>
                                        </motion.div>
                                    )}
                                </motion.div>
                            ))}
                        </div>
                    )}

                    {/* Success message */}
                    {uploadComplete && (
                        <motion.div
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            className="mt-6 bg-[#E8F5E9] border border-[#2E7D32] rounded-lg p-4"
                        >
                            <div className="flex items-start gap-3">
                                <svg className="w-5 h-5 text-[#2E7D32] mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                                </svg>
                                <div>
                                    <p className="text-sm font-semibold text-[#2E7D32]">
                                        Successfully uploaded 3 file(s)
                                    </p>
                                    <p className="text-xs text-[#1A4D2E] mt-1">
                                        Your profile has been built. Click "View Profile" to see your academic summary.
                                    </p>
                                </div>
                            </div>
                        </motion.div>
                    )}
                </div>
            </motion.div>
        </div>
    );
};

export default DocumentUploadDemo;
