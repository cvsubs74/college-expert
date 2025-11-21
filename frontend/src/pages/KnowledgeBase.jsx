import { useState, useEffect } from 'react';
import {
  DocumentArrowUpIcon,
  DocumentTextIcon,
  TrashIcon,
  CheckCircleIcon,
  XCircleIcon,
  ArrowPathIcon,
  BookOpenIcon,
  EyeIcon,
  XMarkIcon
} from '@heroicons/react/24/outline';
import { uploadKnowledgeBaseDocument, listKnowledgeBaseDocuments, deleteKnowledgeBaseDocument, getKnowledgeBaseDocumentContent } from '../services/api';
import { auth } from '../firebase';
import { useApproach } from '../context/ApproachContext';

function KnowledgeBase() {
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [loading, setLoading] = useState(false);
  const [documents, setDocuments] = useState([]);
  const [uploadStatus, setUploadStatus] = useState(null);
  const [uploadProgress, setUploadProgress] = useState({});
  const [error, setError] = useState(null);
  const [previewDocument, setPreviewDocument] = useState(null);
  const [previewContent, setPreviewContent] = useState(null);
  const [loadingContent, setLoadingContent] = useState(false);
  const [pdfUrl, setPdfUrl] = useState(null);
  const [pdfError, setPdfError] = useState(null);
  const [selectedDocuments, setSelectedDocuments] = useState([]);
  const [deleting, setDeleting] = useState(false);
  
  // Get knowledge base approach from context (reads from localStorage)
  const { selectedApproach: knowledgeBaseApproach } = useApproach();
  
  // Get approach display info
  const getApproachInfo = (approach) => {
    switch (approach) {
      case 'rag':
        return {
          name: 'RAG (Gemini File Search)',
          description: 'Using Gemini File Search API for semantic document retrieval',
          bgClass: 'bg-blue-50',
          borderClass: 'border-blue-200',
          dotClass: 'bg-blue-500',
          textClass: 'text-blue-900',
          subTextClass: 'text-blue-700'
        };
      case 'firestore':
        return {
          name: 'Firestore Database',
          description: 'Using Cloud Firestore for structured document storage',
          bgClass: 'bg-green-50',
          borderClass: 'border-green-200',
          dotClass: 'bg-green-500',
          textClass: 'text-green-900',
          subTextClass: 'text-green-700'
        };
      case 'elasticsearch':
        return {
          name: 'Elasticsearch',
          description: 'Using Elasticsearch for advanced search capabilities',
          bgClass: 'bg-purple-50',
          borderClass: 'border-purple-200',
          dotClass: 'bg-purple-500',
          textClass: 'text-purple-900',
          subTextClass: 'text-purple-700'
        };
      default:
        return {
          name: 'Unknown',
          description: 'Unknown knowledge base approach',
          bgClass: 'bg-gray-50',
          borderClass: 'border-gray-200',
          dotClass: 'bg-gray-500',
          textClass: 'text-gray-900',
          subTextClass: 'text-gray-700'
        };
    }
  };
  
  const approachInfo = getApproachInfo(knowledgeBaseApproach);

  useEffect(() => {
    loadDocuments();
  }, []);

  const loadDocuments = async () => {
    setLoading(true);
    setError(null);
    try {
      const currentUser = auth.currentUser;
      const userId = currentUser?.email || 'anonymous';
      const response = await listKnowledgeBaseDocuments(userId);
      if (response.success && response.documents) {
        setDocuments(response.documents);
      } else {
        setDocuments([]);
      }
    } catch (err) {
      console.error('Error loading documents:', err);
      setError('Failed to load documents. Make sure the backend is running.');
      setDocuments([]);
    } finally {
      setLoading(false);
    }
  };

  const handleFileSelect = (event) => {
    const files = Array.from(event.target.files);
    if (files.length > 0) {
      setSelectedFiles(files);
      setUploadStatus(null);
      setError(null);
      setUploadProgress({});
    }
  };

  const handleUpload = async () => {
    if (selectedFiles.length === 0) {
      setError('Please select at least one file');
      return;
    }

    setUploading(true);
    setUploadStatus(null);
    setError(null);
    setUploadProgress({});

    try {
      // Upload all files in parallel
      const uploadPromises = selectedFiles.map(async (file) => {
        try {
          setUploadProgress(prev => ({
            ...prev,
            [file.name]: { status: 'uploading', progress: 0 }
          }));

          const currentUser = auth.currentUser;
          const userId = currentUser?.email || 'anonymous';
          const response = await uploadKnowledgeBaseDocument(file, userId);
          
          if (response.success) {
            setUploadProgress(prev => ({
              ...prev,
              [file.name]: { status: 'success', progress: 100 }
            }));
            return { success: true, filename: file.name };
          } else {
            setUploadProgress(prev => ({
              ...prev,
              [file.name]: { status: 'error', progress: 0, error: response.error }
            }));
            return { success: false, filename: file.name, error: response.error };
          }
        } catch (err) {
          console.error(`Upload error for ${file.name}:`, err);
          setUploadProgress(prev => ({
            ...prev,
            [file.name]: { status: 'error', progress: 0, error: err.message }
          }));
          return { success: false, filename: file.name, error: err.message };
        }
      });

      const results = await Promise.all(uploadPromises);
      
      const successCount = results.filter(r => r.success).length;
      const failCount = results.filter(r => !r.success).length;

      if (successCount > 0) {
        setUploadStatus({
          type: successCount === selectedFiles.length ? 'success' : 'warning',
          message: `Successfully uploaded ${successCount} file(s)${failCount > 0 ? `, ${failCount} failed` : ''}`
        });
      } else {
        setUploadStatus({
          type: 'error',
          message: 'All uploads failed'
        });
      }

      // Reset file input
      setSelectedFiles([]);
      document.getElementById('file-upload').value = '';
      
      // Reload documents list
      await loadDocuments();
    } catch (err) {
      console.error('Upload error:', err);
      setUploadStatus({
        type: 'error',
        message: 'Failed to upload documents. Please try again.'
      });
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (documentName, displayName) => {
    if (!confirm(`Are you sure you want to delete "${displayName}" from the knowledge base?`)) {
      return;
    }

    try {
      const currentUser = auth.currentUser;
      const userId = currentUser?.email || 'anonymous';
      const response = await deleteKnowledgeBaseDocument(documentName, displayName, userId);
      
      if (response.success) {
        setUploadStatus({
          type: 'success',
          message: `Successfully deleted ${displayName}`
        });
        await loadDocuments();
      } else {
        setError(response.error || 'Delete failed');
      }
    } catch (err) {
      console.error('Delete error:', err);
      setError(err.response?.data?.error || 'Failed to delete document');
    }
  };

  const handleBulkDelete = async () => {
    if (selectedDocuments.length === 0) {
      setError('Please select documents to delete');
      return;
    }

    if (!confirm(`Are you sure you want to delete ${selectedDocuments.length} document(s)?`)) {
      return;
    }

    setDeleting(true);
    setError(null);

    try {
      const deletePromises = selectedDocuments.map(doc =>
        deleteKnowledgeBaseDocument(doc.name, doc.display_name || doc.name)
      );

      const results = await Promise.all(deletePromises);
      const successCount = results.filter(r => r.success).length;
      const failCount = results.filter(r => !r.success).length;

      if (successCount > 0) {
        setUploadStatus({
          type: successCount === selectedDocuments.length ? 'success' : 'warning',
          message: `Successfully deleted ${successCount} document(s)${failCount > 0 ? `, ${failCount} failed` : ''}`
        });
      } else {
        setError('All deletions failed');
      }

      setSelectedDocuments([]);
      await loadDocuments();
    } catch (err) {
      console.error('Bulk delete error:', err);
      setError('Failed to delete documents');
    } finally {
      setDeleting(false);
    }
  };

  const toggleDocumentSelection = (doc) => {
    console.log('[DEBUG] Toggle document:', doc.display_name, 'name:', doc.name);
    console.log('[DEBUG] Full doc object:', doc);
    setSelectedDocuments(prev => {
      console.log('[DEBUG] Current selected count:', prev.length);
      console.log('[DEBUG] Current selected names:', prev.map(d => d.name));
      console.log('[DEBUG] Documents array length:', documents.length);
      
      const isSelected = prev.some(d => d.name === doc.name);
      console.log('[DEBUG] Is selected:', isSelected);
      
      if (isSelected) {
        const newSelection = prev.filter(d => d.name !== doc.name);
        console.log('[DEBUG] After deselect - count:', newSelection.length);
        console.log('[DEBUG] After deselect - names:', newSelection.map(d => d.name));
        return newSelection;
      } else {
        const newSelection = [...prev, doc];
        console.log('[DEBUG] After select - count:', newSelection.length);
        console.log('[DEBUG] After select - names:', newSelection.map(d => d.name));
        return newSelection;
      }
    });
  };

  const toggleSelectAll = () => {
    console.log('[DEBUG] toggleSelectAll called!');
    console.log('[DEBUG] Current selected:', selectedDocuments.length, 'Total docs:', documents.length);
    if (selectedDocuments.length === documents.length) {
      console.log('[DEBUG] Deselecting all');
      setSelectedDocuments([]);
    } else {
      console.log('[DEBUG] Selecting all');
      setSelectedDocuments([...documents]);
    }
  };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  const handlePreview = async (doc) => {
    setPreviewDocument(doc);
    setPreviewContent(null);
    setPdfUrl(null);
    setPdfError(null);
    setLoadingContent(true);
    
    try {
      const response = await getKnowledgeBaseDocumentContent(doc.name);
      if (response.success) {
        if (response.is_pdf && response.download_url) {
          // For PDFs, set the URL for the PDF viewer
          console.log('Setting PDF URL:', response.download_url);
          setPdfUrl(response.download_url);
        } else {
          // For text files, set the content
          setPreviewContent(response.content);
        }
      } else {
        setPreviewContent('Failed to load document content.');
      }
    } catch (err) {
      console.error('Error loading content:', err);
      setPreviewContent('Error loading document content.');
    } finally {
      setLoadingContent(false);
    }
  };

  const closePreview = () => {
    setPreviewDocument(null);
    setPreviewContent(null);
    setPdfUrl(null);
    setPdfError(null);
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Knowledge Base Management</h1>
        <p className="mt-2 text-gray-600">
          Upload university research documents to the shared knowledge base. These documents will be available to all users for college information queries.
        </p>
        
        {/* Knowledge Base Approach Indicator */}
        <div className={`mt-4 inline-flex items-center px-4 py-2 rounded-lg ${approachInfo.bgClass} border ${approachInfo.borderClass}`}>
          <div className="flex items-center space-x-2">
            <div className={`w-3 h-3 rounded-full ${approachInfo.dotClass}`}></div>
            <div>
              <p className={`text-sm font-medium ${approachInfo.textClass}`}>
                {approachInfo.name}
              </p>
              <p className={`text-xs ${approachInfo.subTextClass}`}>
                {approachInfo.description}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Upload Section */}
      <div className="bg-white shadow rounded-lg p-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Upload University Research</h2>
        
        <div className="space-y-4">
          {/* File Input */}
          <div>
            <label htmlFor="file-upload" className="block text-sm font-medium text-gray-700 mb-2">
              Select Documents (PDF, DOCX, TXT) - Multiple files supported
            </label>
            <div className="flex items-center space-x-4">
              <label 
                htmlFor="file-upload-input" 
                className={`inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-primary hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary cursor-pointer ${uploading ? 'opacity-50 cursor-not-allowed' : ''}`}
              >
                <DocumentArrowUpIcon className="h-5 w-5 mr-2" />
                Choose Files
              </label>
              <input
                id="file-upload-input"
                type="file"
                accept=".pdf,.docx,.txt"
                onChange={handleFileSelect}
                disabled={uploading}
                multiple
                className="hidden"
              />
              {selectedFiles.length === 0 && (
                <span className="text-sm text-gray-500">No files selected</span>
              )}
            </div>
          </div>

          {/* Selected Files List */}
          {selectedFiles.length > 0 && (
            <div className="bg-gray-50 rounded-lg p-4">
              <h3 className="text-sm font-medium text-gray-700 mb-2">
                Selected Files ({selectedFiles.length}):
              </h3>
              <ul className="space-y-2">
                {selectedFiles.map((file, index) => (
                  <li key={index} className="flex items-center justify-between text-sm">
                    <span className="text-gray-900">{file.name}</span>
                    <span className="text-gray-500">{formatFileSize(file.size)}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Upload Progress */}
          {Object.keys(uploadProgress).length > 0 && (
            <div className="bg-gray-50 rounded-lg p-4">
              <h3 className="text-sm font-medium text-gray-700 mb-2">Upload Progress:</h3>
              <ul className="space-y-2">
                {Object.entries(uploadProgress).map(([filename, progress]) => (
                  <li key={filename} className="flex items-center justify-between text-sm">
                    <span className="text-gray-900">{filename}</span>
                    {progress.status === 'uploading' && (
                      <span className="flex items-center text-blue-600">
                        <ArrowPathIcon className="h-4 w-4 mr-1 animate-spin" />
                        Uploading...
                      </span>
                    )}
                    {progress.status === 'success' && (
                      <span className="flex items-center text-green-600">
                        <CheckCircleIcon className="h-4 w-4 mr-1" />
                        Success
                      </span>
                    )}
                    {progress.status === 'error' && (
                      <span className="flex items-center text-red-600">
                        <XCircleIcon className="h-4 w-4 mr-1" />
                        Failed
                      </span>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Upload Button */}
          <button
            onClick={handleUpload}
            disabled={selectedFiles.length === 0 || uploading}
            className={`w-full flex items-center justify-center px-4 py-3 border border-transparent text-base font-medium rounded-md text-white ${
              selectedFiles.length === 0 || uploading
                ? 'bg-gray-400 cursor-not-allowed'
                : 'bg-primary hover:bg-blue-700'
            } transition-colors`}
          >
            {uploading ? (
              <>
                <ArrowPathIcon className="animate-spin h-5 w-5 mr-2" />
                Uploading {selectedFiles.length} file(s)...
              </>
            ) : (
              <>
                <DocumentArrowUpIcon className="h-5 w-5 mr-2" />
                Upload {selectedFiles.length > 0 ? `${selectedFiles.length} ` : ''}Document(s)
              </>
            )}
          </button>

          {/* Upload Status */}
          {uploadStatus && (
            <div className={`p-4 rounded-md ${
              uploadStatus.type === 'success' ? 'bg-green-50' : 
              uploadStatus.type === 'warning' ? 'bg-yellow-50' : 'bg-red-50'
            }`}>
              <div className="flex">
                {uploadStatus.type === 'success' ? (
                  <CheckCircleIcon className="h-5 w-5 text-green-400" />
                ) : uploadStatus.type === 'warning' ? (
                  <CheckCircleIcon className="h-5 w-5 text-yellow-400" />
                ) : (
                  <XCircleIcon className="h-5 w-5 text-red-400" />
                )}
                <p className={`ml-3 text-sm ${
                  uploadStatus.type === 'success' ? 'text-green-800' : 
                  uploadStatus.type === 'warning' ? 'text-yellow-800' : 'text-red-800'
                }`}>
                  {uploadStatus.message}
                </p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Documents List */}
      <div className="bg-white shadow rounded-lg p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-4">
            <h2 className="text-xl font-semibold text-gray-900">
              Documents ({documents.length})
            </h2>
            {selectedDocuments.length > 0 && (
              <span className="text-sm text-gray-600">
                {selectedDocuments.length} selected
              </span>
            )}
          </div>
          <div className="flex items-center space-x-2">
            {selectedDocuments.length > 0 && (
              <button
                onClick={handleBulkDelete}
                disabled={deleting}
                className="inline-flex items-center px-3 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-red-600 hover:bg-red-700 disabled:opacity-50"
              >
                <TrashIcon className="h-4 w-4 mr-2" />
                {deleting ? 'Deleting...' : `Delete ${selectedDocuments.length}`}
              </button>
            )}
            <button
              onClick={loadDocuments}
              disabled={loading}
              className="inline-flex items-center px-3 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50"
            >
              <ArrowPathIcon className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </button>
          </div>
        </div>

        {error && (
          <div className="mb-4 p-4 rounded-md bg-red-50">
            <div className="flex">
              <XCircleIcon className="h-5 w-5 text-red-400" />
              <p className="ml-3 text-sm text-red-800">{error}</p>
            </div>
          </div>
        )}

        {loading ? (
          <div className="flex items-center justify-center py-8">
            <ArrowPathIcon className="h-8 w-8 animate-spin text-gray-400" />
          </div>
        ) : documents.length === 0 ? (
          <div className="text-center py-8">
            <BookOpenIcon className="mx-auto h-12 w-12 text-gray-400" />
            <p className="mt-2 text-sm text-gray-500">No documents in knowledge base yet</p>
            <p className="text-xs text-gray-400">Upload university research documents to get started</p>
          </div>
        ) : (
          <>
            {documents.length > 0 && (
              <div className="mb-3 pb-3 border-b border-gray-200">
                <div className="flex items-center space-x-2">
                  <input
                    type="checkbox"
                    id="select-all-checkbox"
                    checked={selectedDocuments.length === documents.length && documents.length > 0}
                    ref={(el) => {
                      if (el) {
                        el.indeterminate = selectedDocuments.length > 0 && selectedDocuments.length < documents.length;
                      }
                    }}
                    onChange={(e) => {
                      e.stopPropagation();
                      toggleSelectAll();
                    }}
                    onClick={(e) => e.stopPropagation()}
                    className="h-4 w-4 text-primary border-gray-300 rounded focus:ring-primary cursor-pointer"
                  />
                  <label htmlFor="select-all-checkbox" className="text-sm font-medium text-gray-700 cursor-pointer">
                    Select All
                  </label>
                </div>
              </div>
            )}
            <div className="space-y-3">
              {documents.map((doc, index) => {
                const isSelected = selectedDocuments.some(d => d.name === doc.name);
                return (
                  <div
                    key={doc.name || index}
                    className={`flex items-center justify-between p-4 border rounded-lg transition-colors ${
                      isSelected ? 'border-primary bg-blue-50' : 'border-gray-200 hover:bg-gray-50'
                    }`}
                  >
                    <div className="flex items-center space-x-3 flex-1">
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={(e) => {
                          e.stopPropagation();
                          toggleDocumentSelection(doc);
                        }}
                        onClick={(e) => e.stopPropagation()}
                        className="h-4 w-4 text-primary border-gray-300 rounded focus:ring-primary"
                      />
                      <DocumentTextIcon className="h-6 w-6 text-gray-400" />
                      <div className="flex-1">
                        <p className="text-sm font-medium text-gray-900">{doc.display_name || doc.name}</p>
                    <p className="text-xs text-gray-500">
                      {formatFileSize(doc.size_bytes || doc.size)} • {doc.mime_type}
                    </p>
                  </div>
                </div>
                <div className="flex items-center space-x-2">
                  <button
                    onClick={() => handlePreview(doc)}
                    className="p-2 text-blue-600 hover:text-blue-800 hover:bg-blue-50 rounded-md transition-colors"
                    title="Preview document"
                  >
                    <EyeIcon className="h-5 w-5" />
                  </button>
                  <button
                    onClick={() => handleDelete(doc.name, doc.display_name || doc.name)}
                    className="p-2 text-red-600 hover:bg-red-50 rounded-md transition-colors"
                    title="Delete document"
                  >
                    <TrashIcon className="h-5 w-5" />
                  </button>
                </div>
              </div>
                );
              })}
            </div>
          </>
        )}

        <div className="mt-4 p-4 bg-blue-50 rounded-md">
          <p className="text-sm text-blue-800">
            <strong>Note:</strong> Documents uploaded here are shared across all users and will be used by the AI agent to answer college-related questions in the "College Info Chat" section.
          </p>
        </div>
      </div>

      {/* Preview Modal */}
      {previewDocument && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-hidden flex flex-col">
            {/* Modal Header */}
            <div className="flex items-center justify-between p-6 border-b border-gray-200">
              <h3 className="text-xl font-semibold text-gray-900">Document Preview</h3>
              <button
                onClick={closePreview}
                className="text-gray-400 hover:text-gray-600 transition-colors"
              >
                <XMarkIcon className="h-6 w-6" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="flex-1 overflow-y-auto p-6">
              <div className="space-y-4">
                {/* Document Info */}
                <div className="bg-gray-50 rounded-lg p-4">
                  <h4 className="text-sm font-semibold text-gray-700 mb-3">Document Information</h4>
                  <dl className="space-y-2">
                    <div className="flex justify-between">
                      <dt className="text-sm text-gray-600">Name:</dt>
                      <dd className="text-sm font-medium text-gray-900">{previewDocument.name}</dd>
                    </div>
                    <div className="flex justify-between">
                      <dt className="text-sm text-gray-600">Size:</dt>
                      <dd className="text-sm font-medium text-gray-900">{formatFileSize(previewDocument.size)}</dd>
                    </div>
                    <div className="flex justify-between">
                      <dt className="text-sm text-gray-600">Type:</dt>
                      <dd className="text-sm font-medium text-gray-900">{previewDocument.mime_type}</dd>
                    </div>
                  </dl>
                </div>

                {/* Document Content */}
                <div className="bg-white border border-gray-200 rounded-lg p-4">
                  <h4 className="text-sm font-semibold text-gray-700 mb-3">Document Content</h4>
                  {loadingContent ? (
                    <div className="flex items-center justify-center py-8">
                      <ArrowPathIcon className="h-6 w-6 animate-spin text-gray-400" />
                      <span className="ml-2 text-sm text-gray-500">Loading content...</span>
                    </div>
                  ) : pdfUrl && !pdfError ? (
                    <div className="space-y-4">
                      <div className="bg-gray-50 rounded p-4">
                        <iframe
                          src={pdfUrl}
                          className="w-full h-[600px] border-0 rounded"
                          title="PDF Preview"
                          onError={() => setPdfError('Failed to load PDF')}
                        />
                      </div>
                      <div className="flex justify-center">
                        <a
                          href={pdfUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-sm text-blue-600 hover:text-blue-800 underline"
                        >
                          Open in new tab
                        </a>
                      </div>
                    </div>
                  ) : pdfError ? (
                    <div className="bg-red-50 border border-red-200 rounded p-4">
                      <p className="text-sm text-red-800">{pdfError}</p>
                    </div>
                  ) : previewContent ? (
                    <div className="bg-gray-50 rounded p-4 max-h-96 overflow-y-auto">
                      <pre className="text-xs text-gray-800 whitespace-pre-wrap font-mono">{previewContent}</pre>
                    </div>
                  ) : (
                    <p className="text-sm text-gray-500">Content not available</p>
                  )}
                </div>
              </div>
            </div>

            {/* Modal Footer */}
            <div className="flex items-center justify-end space-x-3 p-6 border-t border-gray-200">
              <button
                onClick={closePreview}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default KnowledgeBase;
