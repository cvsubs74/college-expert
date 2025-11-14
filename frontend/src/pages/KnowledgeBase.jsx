import { useState, useEffect } from 'react';
import {
  DocumentArrowUpIcon,
  DocumentTextIcon,
  TrashIcon,
  CheckCircleIcon,
  XCircleIcon,
  ArrowPathIcon,
  BookOpenIcon
} from '@heroicons/react/24/outline';
import { uploadKnowledgeBaseDocument, listKnowledgeBaseDocuments, deleteKnowledgeBaseDocument } from '../services/api';

function KnowledgeBase() {
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [loading, setLoading] = useState(false);
  const [documents, setDocuments] = useState([]);
  const [uploadStatus, setUploadStatus] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadDocuments();
  }, []);

  const loadDocuments = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await listKnowledgeBaseDocuments();
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
    const file = event.target.files[0];
    if (file) {
      setSelectedFile(file);
      setUploadStatus(null);
      setError(null);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      setError('Please select a file first');
      return;
    }

    setUploading(true);
    setUploadStatus(null);
    setError(null);

    try {
      const response = await uploadKnowledgeBaseDocument(selectedFile);
      
      if (response.success) {
        setUploadStatus({
          type: 'success',
          message: `Successfully uploaded ${selectedFile.name} to knowledge base`
        });
        setSelectedFile(null);
        // Reset file input
        document.getElementById('file-upload').value = '';
        // Reload documents list
        await loadDocuments();
      } else {
        setUploadStatus({
          type: 'error',
          message: response.error || 'Upload failed'
        });
      }
    } catch (err) {
      console.error('Upload error:', err);
      setUploadStatus({
        type: 'error',
        message: err.response?.data?.error || 'Failed to upload document'
      });
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (documentName) => {
    if (!confirm(`Are you sure you want to delete "${documentName}" from the knowledge base?`)) {
      return;
    }

    try {
      const response = await deleteKnowledgeBaseDocument(documentName);
      
      if (response.success) {
        setUploadStatus({
          type: 'success',
          message: `Successfully deleted ${documentName}`
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

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Knowledge Base Management</h1>
        <p className="mt-2 text-gray-600">
          Upload university research documents to the shared knowledge base. These documents will be available to all users for college information queries.
        </p>
      </div>

      {/* Upload Section */}
      <div className="bg-white shadow rounded-lg p-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Upload University Research</h2>
        
        <div className="space-y-4">
          {/* File Input */}
          <div>
            <label htmlFor="file-upload" className="block text-sm font-medium text-gray-700 mb-2">
              Select Document (PDF, DOCX, TXT)
            </label>
            <div className="flex items-center space-x-4">
              <input
                id="file-upload"
                type="file"
                accept=".pdf,.docx,.txt"
                onChange={handleFileSelect}
                disabled={uploading}
                className="block w-full text-sm text-gray-500
                  file:mr-4 file:py-2 file:px-4
                  file:rounded-md file:border-0
                  file:text-sm file:font-semibold
                  file:bg-primary file:text-white
                  hover:file:bg-blue-700
                  disabled:opacity-50 disabled:cursor-not-allowed"
              />
            </div>
            {selectedFile && (
              <p className="mt-2 text-sm text-gray-600">
                Selected: {selectedFile.name} ({formatFileSize(selectedFile.size)})
              </p>
            )}
          </div>

          {/* Upload Button */}
          <button
            onClick={handleUpload}
            disabled={!selectedFile || uploading}
            className={`w-full flex items-center justify-center px-4 py-3 border border-transparent text-base font-medium rounded-md text-white ${
              !selectedFile || uploading
                ? 'bg-gray-400 cursor-not-allowed'
                : 'bg-primary hover:bg-blue-700'
            } transition-colors`}
          >
            {uploading ? (
              <>
                <ArrowPathIcon className="animate-spin h-5 w-5 mr-2" />
                Uploading...
              </>
            ) : (
              <>
                <DocumentArrowUpIcon className="h-5 w-5 mr-2" />
                Upload to Knowledge Base
              </>
            )}
          </button>

          {/* Upload Status */}
          {uploadStatus && (
            <div className={`p-4 rounded-md ${
              uploadStatus.type === 'success' ? 'bg-green-50' : 'bg-red-50'
            }`}>
              <div className="flex">
                {uploadStatus.type === 'success' ? (
                  <CheckCircleIcon className="h-5 w-5 text-green-400" />
                ) : (
                  <XCircleIcon className="h-5 w-5 text-red-400" />
                )}
                <p className={`ml-3 text-sm ${
                  uploadStatus.type === 'success' ? 'text-green-800' : 'text-red-800'
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
          <h2 className="text-xl font-semibold text-gray-900">Knowledge Base Documents</h2>
          <button
            onClick={loadDocuments}
            disabled={loading}
            className="inline-flex items-center px-3 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50"
          >
            <ArrowPathIcon className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
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
          <div className="space-y-3">
            {documents.map((doc, index) => (
              <div
                key={index}
                className="flex items-center justify-between p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
              >
                <div className="flex items-center space-x-3 flex-1">
                  <DocumentTextIcon className="h-6 w-6 text-gray-400" />
                  <div className="flex-1">
                    <p className="text-sm font-medium text-gray-900">{doc.name}</p>
                    <p className="text-xs text-gray-500">
                      {formatFileSize(doc.size)} • {doc.mime_type}
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => handleDelete(doc.name)}
                  className="ml-4 p-2 text-red-600 hover:bg-red-50 rounded-md transition-colors"
                  title="Delete document"
                >
                  <TrashIcon className="h-5 w-5" />
                </button>
              </div>
            ))}
          </div>
        )}

        <div className="mt-4 p-4 bg-blue-50 rounded-md">
          <p className="text-sm text-blue-800">
            <strong>Note:</strong> Documents uploaded here are shared across all users and will be used by the AI agent to answer college-related questions in the "College Info Chat" section.
          </p>
        </div>
      </div>
    </div>
  );
}

export default KnowledgeBase;
