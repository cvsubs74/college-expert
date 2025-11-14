import { useState, useEffect } from 'react';
import {
  DocumentArrowUpIcon,
  DocumentTextIcon,
  TrashIcon,
  CheckCircleIcon,
  XCircleIcon,
  ArrowPathIcon
} from '@heroicons/react/24/outline';
import { uploadStudentProfile, listStudentProfiles, deleteStudentProfile } from '../services/api';
import { useAuth } from '../context/AuthContext';

function Profile() {
  const { currentUser } = useAuth();
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [loading, setLoading] = useState(false);
  const [profiles, setProfiles] = useState([]);
  const [uploadStatus, setUploadStatus] = useState(null);
  const [error, setError] = useState(null);

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

    if (!currentUser?.email) {
      setError('User not authenticated');
      return;
    }

    setUploading(true);
    setUploadStatus(null);
    setError(null);

    try {
      const response = await uploadStudentProfile(selectedFile, currentUser.email);
      
      if (response.success) {
        setUploadStatus({
          type: 'success',
          message: `Successfully uploaded ${selectedFile.name}`
        });
        setSelectedFile(null);
        // Reset file input
        document.getElementById('file-upload').value = '';
        // Reload profiles list
        await loadProfiles();
      } else {
        setUploadStatus({
          type: 'error',
          message: response.message || 'Upload failed'
        });
      }
    } catch (err) {
      console.error('Upload error:', err);
      setUploadStatus({
        type: 'error',
        message: err.response?.data?.message || 'Failed to upload file. Please try again.'
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
      const response = await deleteStudentProfile(documentName);
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
              Select File (PDF, DOCX, TXT)
            </label>
            <div className="flex items-center space-x-4">
              <label className="flex-1 flex items-center justify-center px-6 py-4 border-2 border-dashed border-gray-300 rounded-lg cursor-pointer hover:border-primary hover:bg-gray-50 transition-colors">
                <div className="text-center">
                  <DocumentArrowUpIcon className="mx-auto h-12 w-12 text-gray-400" />
                  <p className="mt-2 text-sm text-gray-600">
                    {selectedFile ? selectedFile.name : 'Click to select file'}
                  </p>
                  {selectedFile && (
                    <p className="mt-1 text-xs text-gray-500">
                      {formatFileSize(selectedFile.size)}
                    </p>
                  )}
                </div>
                <input
                  id="file-upload"
                  type="file"
                  className="hidden"
                  accept=".pdf,.docx,.txt,.doc"
                  onChange={handleFileSelect}
                />
              </label>
            </div>
          </div>

          {/* Upload Button */}
          <button
            onClick={handleUpload}
            disabled={!selectedFile || uploading}
            className={`w-full flex items-center justify-center px-6 py-3 border border-transparent text-base font-medium rounded-md text-white ${
              !selectedFile || uploading
                ? 'bg-gray-400 cursor-not-allowed'
                : 'bg-primary hover:bg-blue-700'
            } transition-colors`}
          >
            {uploading ? (
              <>
                <ArrowPathIcon className="h-5 w-5 mr-2 animate-spin" />
                Uploading...
              </>
            ) : (
              <>
                <DocumentArrowUpIcon className="h-5 w-5 mr-2" />
                Upload Profile
              </>
            )}
          </button>

          {/* Status Messages */}
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
          <h2 className="text-xl font-semibold text-gray-900">Your Profiles</h2>
          <button
            onClick={loadProfiles}
            disabled={loading}
            className="flex items-center px-3 py-2 text-sm text-gray-700 hover:text-primary transition-colors"
          >
            <ArrowPathIcon className={`h-4 w-4 mr-1 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
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
          <div className="space-y-3">
            {profiles.map((profile, index) => (
              <div
                key={index}
                className="flex items-center justify-between p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
              >
                <div className="flex items-center space-x-3 flex-1">
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
                <button
                  onClick={() => handleDelete(profile.name, profile.display_name)}
                  className="ml-4 p-2 text-red-600 hover:text-red-800 hover:bg-red-50 rounded-md transition-colors"
                  title="Delete profile"
                >
                  <TrashIcon className="h-5 w-5" />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default Profile;
