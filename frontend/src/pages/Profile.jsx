import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { 
  uploadStudentProfile, 
  listStudentProfiles, 
  deleteStudentProfile,
  getStudentProfileContent
} from '../services/api';
import {
  DocumentArrowUpIcon,
  DocumentTextIcon,
  TrashIcon,
  CheckCircleIcon,
  XCircleIcon,
  ArrowPathIcon,
  EyeIcon,
  XMarkIcon
} from '@heroicons/react/24/outline';

function Profile() {
  const { currentUser } = useAuth();
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [loading, setLoading] = useState(false);
  const [profiles, setProfiles] = useState([]);
  const [uploadStatus, setUploadStatus] = useState(null);
  const [uploadProgress, setUploadProgress] = useState({});
  const [error, setError] = useState(null);
  const [previewDocument, setPreviewDocument] = useState(null);
  const [previewContent, setPreviewContent] = useState(null);
  const [loadingContent, setLoadingContent] = useState(false);
  const [pdfUrl, setPdfUrl] = useState(null);
  const [pdfError, setPdfError] = useState(null);
  const [selectedProfiles, setSelectedProfiles] = useState([]);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    if (currentUser?.email) {
      loadProfiles();
    }
  }, [currentUser]);

  const loadProfiles = async () => {
    if (!currentUser?.email) {
      setError('User not authenticated');
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const response = await listStudentProfiles(currentUser.email);
      if (response.success && response.documents) {
        setProfiles(response.documents);
      } else {
        setProfiles([]);
      }
    } catch (err) {
      console.error('Error loading profiles:', err);
      setError('Failed to load profiles. Make sure the backend is running.');
      setProfiles([]);
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

    if (!currentUser?.email) {
      setError('User not authenticated');
      return;
    }

    setUploading(true);
    setUploadStatus(null);
    setError(null);
    setUploadProgress({});

    try {
      // Upload all files in parallel
      const uploadPromises = selectedFiles.map(async (file, index) => {
        try {
          setUploadProgress(prev => ({
            ...prev,
            [file.name]: { status: 'uploading', progress: 0 }
          }));

          const response = await uploadStudentProfile(file, currentUser.email);
          
          if (response.success) {
            setUploadProgress(prev => ({
              ...prev,
              [file.name]: { status: 'success', progress: 100 }
            }));
            return { success: true, filename: file.name };
          } else {
            setUploadProgress(prev => ({
              ...prev,
              [file.name]: { status: 'error', progress: 0, error: response.message }
            }));
            return { success: false, filename: file.name, error: response.message };
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
      
      // Reload profiles list
      await loadProfiles();
    } catch (err) {
      console.error('Upload error:', err);
      setUploadStatus({
        type: 'error',
        message: 'Failed to upload files. Please try again.'
      });
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (documentName, displayName) => {
    if (!confirm(`Are you sure you want to delete "${displayName}"?`)) {
      return;
    }

    try {
      const response = await deleteStudentProfile(documentName, currentUser.email, displayName);
      if (response.success) {
        setUploadStatus({
          type: 'success',
          message: `Successfully deleted ${displayName}`
        });
        await loadProfiles();
      } else {
        setError(response.message || 'Failed to delete profile');
      }
    } catch (err) {
      console.error('Delete error:', err);
      setError('Failed to delete profile. Please try again.');
    }
  };

  const handleBulkDelete = async () => {
    if (selectedProfiles.length === 0) {
      setError('Please select profiles to delete');
      return;
    }

    if (!confirm(`Are you sure you want to delete ${selectedProfiles.length} profile(s)?`)) {
      return;
    }

    setDeleting(true);
    setError(null);

    try {
      const deletePromises = selectedProfiles.map(profile =>
        deleteStudentProfile(profile.name, currentUser.email, profile.display_name)
      );

      const results = await Promise.all(deletePromises);
      const successCount = results.filter(r => r.success).length;
      const failCount = results.filter(r => !r.success).length;

      if (successCount > 0) {
        setUploadStatus({
          type: successCount === selectedProfiles.length ? 'success' : 'warning',
          message: `Successfully deleted ${successCount} profile(s)${failCount > 0 ? `, ${failCount} failed` : ''}`
        });
      } else {
        setError('All deletions failed');
      }

      setSelectedProfiles([]);
      await loadProfiles();
    } catch (err) {
      console.error('Bulk delete error:', err);
      setError('Failed to delete profiles');
    } finally {
      setDeleting(false);
    }
  };

  const toggleProfileSelection = (profile) => {
    setSelectedProfiles(prev => {
      const isSelected = prev.some(p => p.name === profile.name);
      if (isSelected) {
        return prev.filter(p => p.name !== profile.name);
      } else {
        return [...prev, profile];
      }
    });
  };

  const toggleSelectAll = () => {
    if (selectedProfiles.length === profiles.length) {
      setSelectedProfiles([]);
    } else {
      setSelectedProfiles([...profiles]);
    }
  };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const handlePreview = async (profile) => {
    setPreviewDocument(profile);
    setPreviewContent(null);
    setPdfUrl(null);
    setPdfError(null);
    setLoadingContent(true);
    
    try {
      const filename = profile.display_name || profile.name.split('/').pop();
      const response = await getStudentProfileContent(currentUser.email, filename);
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
        <h1 className="text-3xl font-bold text-gray-900">Student Profile</h1>
        <p className="mt-2 text-gray-600">
          Upload your academic profile, transcript, and extracurricular information. This will be used for your admissions analysis.
        </p>
      </div>

      {/* Upload Section */}
      <div className="bg-white shadow rounded-lg p-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Upload Profile</h2>
        
        <div className="space-y-4">
          {/* File Input */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Select Files (PDF, DOCX, TXT) - Multiple files supported
            </label>
            <div className="flex items-center space-x-4">
              <label className="flex-1 flex items-center justify-center px-6 py-4 border-2 border-dashed border-gray-300 rounded-lg cursor-pointer hover:border-primary hover:bg-gray-50 transition-colors">
                <div className="text-center">
                  <DocumentArrowUpIcon className="mx-auto h-12 w-12 text-gray-400" />
                  <p className="mt-2 text-sm text-gray-600">
                    {selectedFiles.length > 0 
                      ? `${selectedFiles.length} file(s) selected` 
                      : 'Click to select files'}
                  </p>
                  {selectedFiles.length > 0 && (
                    <p className="mt-1 text-xs text-gray-500">
                      {selectedFiles.map(f => f.name).join(', ')}
                    </p>
                  )}
                </div>
                <input
                  id="file-upload"
                  type="file"
                  className="hidden"
                  accept=".pdf,.docx,.txt,.doc"
                  onChange={handleFileSelect}
                  multiple
                />
              </label>
            </div>
          </div>

          {/* Selected Files List */}
          {selectedFiles.length > 0 && (
            <div className="bg-gray-50 rounded-lg p-4">
              <h3 className="text-sm font-medium text-gray-700 mb-2">Selected Files:</h3>
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
            className={`w-full flex items-center justify-center px-6 py-3 border border-transparent text-base font-medium rounded-md text-white ${
              selectedFiles.length === 0 || uploading
                ? 'bg-gray-400 cursor-not-allowed'
                : 'bg-primary hover:bg-blue-700'
            } transition-colors`}
          >
            {uploading ? (
              <>
                <ArrowPathIcon className="h-5 w-5 mr-2 animate-spin" />
                Uploading {selectedFiles.length} file(s)...
              </>
            ) : (
              <>
                <DocumentArrowUpIcon className="h-5 w-5 mr-2" />
                Upload {selectedFiles.length > 0 ? `${selectedFiles.length} ` : ''}Profile(s)
              </>
            )}
          </button>

          {/* Status Messages */}
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

          {error && (
            <div className="p-4 rounded-md bg-red-50">
              <div className="flex">
                <XCircleIcon className="h-5 w-5 text-red-400" />
                <p className="ml-3 text-sm text-red-800">{error}</p>
              </div>
            </div>
          )}
        </div>

        {/* Guidelines */}
        <div className="mt-6 p-4 bg-blue-50 rounded-md">
          <h3 className="text-sm font-medium text-blue-900 mb-2">What to Include:</h3>
          <ul className="text-sm text-blue-800 space-y-1 list-disc list-inside">
            <li>Complete transcript with courses, grades, and course levels (Regular, Honors, AP, IB)</li>
            <li>Standardized test scores (SAT, ACT, AP tests)</li>
            <li>Extracurricular activities and leadership roles</li>
            <li>Awards and honors</li>
            <li>Personal statement or essay (optional)</li>
            <li>Any other relevant academic information</li>
          </ul>
        </div>
      </div>

      {/* Existing Profiles */}
      <div className="bg-white shadow rounded-lg p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-4">
            <h2 className="text-xl font-semibold text-gray-900">Your Profiles</h2>
            {selectedProfiles.length > 0 && (
              <span className="text-sm text-gray-600">
                {selectedProfiles.length} selected
              </span>
            )}
          </div>
          <div className="flex items-center space-x-2">
            {selectedProfiles.length > 0 && (
              <button
                onClick={handleBulkDelete}
                disabled={deleting}
                className="inline-flex items-center px-3 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-red-600 hover:bg-red-700 disabled:opacity-50"
              >
                <TrashIcon className="h-4 w-4 mr-2" />
                {deleting ? 'Deleting...' : `Delete ${selectedProfiles.length}`}
              </button>
            )}
            <button
              onClick={loadProfiles}
              disabled={loading}
              className="flex items-center px-3 py-2 text-sm text-gray-700 hover:text-primary transition-colors"
            >
              <ArrowPathIcon className={`h-4 w-4 mr-1 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </button>
          </div>
        </div>

        {loading ? (
          <div className="text-center py-8">
            <ArrowPathIcon className="h-8 w-8 text-gray-400 animate-spin mx-auto" />
            <p className="mt-2 text-sm text-gray-500">Loading profiles...</p>
          </div>
        ) : profiles.length === 0 ? (
          <div className="text-center py-8">
            <DocumentTextIcon className="h-12 w-12 text-gray-400 mx-auto" />
            <p className="mt-2 text-sm text-gray-500">No profiles uploaded yet</p>
          </div>
        ) : (
          <>
            {profiles.length > 0 && (
              <div className="mb-3 pb-3 border-b border-gray-200">
                <label className="flex items-center space-x-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={selectedProfiles.length === profiles.length}
                    onChange={toggleSelectAll}
                    className="h-4 w-4 text-primary border-gray-300 rounded focus:ring-primary"
                  />
                  <span className="text-sm font-medium text-gray-700">
                    Select All
                  </span>
                </label>
              </div>
            )}
            <div className="space-y-3">
              {profiles.map((profile, index) => {
                const isSelected = selectedProfiles.some(p => p.name === profile.name);
                return (
                  <div
                    key={index}
                    className={`flex items-center justify-between p-4 border rounded-lg transition-colors ${
                      isSelected ? 'border-primary bg-blue-50' : 'border-gray-200 hover:bg-gray-50'
                    }`}
                  >
                    <div className="flex items-center space-x-3 flex-1">
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => toggleProfileSelection(profile)}
                        className="h-4 w-4 text-primary border-gray-300 rounded focus:ring-primary"
                      />
                      <DocumentTextIcon className="h-8 w-8 text-primary flex-shrink-0" />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-900 truncate">
                          {profile.display_name || profile.name}
                        </p>
                    <p className="text-xs text-gray-500">
                      {formatFileSize(profile.size_bytes)} • {formatDate(profile.create_time)}
                    </p>
                    {profile.state && (
                      <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                        profile.state === 'ACTIVE' ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'
                      }`}>
                        {profile.state}
                      </span>
                    )}
                  </div>
                </div>
                <div className="flex items-center space-x-2">
                  <button
                    onClick={() => handlePreview(profile)}
                    className="p-2 text-blue-600 hover:text-blue-800 hover:bg-blue-50 rounded-md transition-colors"
                    title="Preview document"
                  >
                    <EyeIcon className="h-5 w-5" />
                  </button>
                  <button
                    onClick={() => handleDelete(profile.name, profile.display_name)}
                    className="p-2 text-red-600 hover:text-red-800 hover:bg-red-50 rounded-md transition-colors"
                    title="Delete profile"
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
                      <dd className="text-sm font-medium text-gray-900">{previewDocument.display_name || previewDocument.name}</dd>
                    </div>
                    <div className="flex justify-between">
                      <dt className="text-sm text-gray-600">Size:</dt>
                      <dd className="text-sm font-medium text-gray-900">{formatFileSize(previewDocument.size_bytes)}</dd>
                    </div>
                    <div className="flex justify-between">
                      <dt className="text-sm text-gray-600">Uploaded:</dt>
                      <dd className="text-sm font-medium text-gray-900">{formatDate(previewDocument.create_time)}</dd>
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

export default Profile;
