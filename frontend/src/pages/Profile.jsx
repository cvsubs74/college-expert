import { useState, useEffect, useRef } from 'react';
import { useAuth } from '../context/AuthContext';
import { useApproach } from '../context/ApproachContext';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  uploadStudentProfile,
  listStudentProfiles,
  deleteStudentProfile,
  getStudentProfileContent,
  fetchUserProfile,
  fetchStructuredProfile,
  uploadVertexAIProfile,
  listVertexAIProfiles,
  deleteVertexAIProfile,
  startSession,
  extractFullResponse,
  recomputeLaunchpadFits,
  resetAllProfile
} from '../services/api';
import ProfileViewCard from '../components/ProfileViewCard';
import ProfileBuilder from '../components/ProfileBuilder';
import GuidedInterview from '../components/GuidedInterview';

import {
  DocumentArrowUpIcon,
  DocumentTextIcon,
  TrashIcon,
  CheckCircleIcon,
  XCircleIcon,
  ArrowPathIcon,
  EyeIcon,
  XMarkIcon,
  ChatBubbleLeftRightIcon,
  PaperAirplaneIcon,
  SparklesIcon,
  UserCircleIcon,
  PencilSquareIcon
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

  // Reset profile modal state
  const [showResetModal, setShowResetModal] = useState(false);
  const [resetting, setResetting] = useState(false);
  const [resetOptions, setResetOptions] = useState({ deleteCollegeList: false });

  // New state for tabs, profile view, and chat
  const [activeTab, setActiveTab] = useState('view'); // 'view' | 'files' | 'form' | 'guided' | 'chat'
  const [profileMarkdown, setProfileMarkdown] = useState('');
  const [structuredProfile, setStructuredProfile] = useState(null);
  const [loadingProfile, setLoadingProfile] = useState(false);
  const [chatMessages, setChatMessages] = useState([]);
  const [chatInput, setChatInput] = useState('');
  const [isSending, setIsSending] = useState(false);
  const chatEndRef = useRef(null);

  // Get knowledge base approach from context (profile manager follows same approach)
  const { selectedApproach: knowledgeBaseApproach } = useApproach();

  // Get approach display info (same as KnowledgeBase)
  const getApproachInfo = (approach) => {
    switch (approach) {
      case 'hybrid':
        return {
          name: 'Hybrid Search',
          description: 'Using structured university profiles with BM25 + Vector search',
          bgClass: 'bg-teal-50',
          borderClass: 'border-teal-200',
          dotClass: 'bg-teal-500',
          textClass: 'text-teal-900',
          subTextClass: 'text-teal-700'
        };
      case 'rag':
        return {
          name: 'RAG (Gemini File Search)',
          description: 'Using Gemini File Search API for profile storage and retrieval',
          bgClass: 'bg-blue-50',
          borderClass: 'border-blue-200',
          dotClass: 'bg-blue-500',
          textClass: 'text-blue-900',
          subTextClass: 'text-blue-700'
        };
      case 'firestore':
        return {
          name: 'Firestore Database',
          description: 'Using Cloud Firestore for structured profile storage',
          bgClass: 'bg-green-50',
          borderClass: 'border-green-200',
          dotClass: 'bg-green-500',
          textClass: 'text-green-900',
          subTextClass: 'text-green-700'
        };
      case 'elasticsearch':
        return {
          name: 'Elasticsearch',
          description: 'Using Elasticsearch for advanced profile search and analysis',
          bgClass: 'bg-purple-50',
          borderClass: 'border-purple-200',
          dotClass: 'bg-purple-500',
          textClass: 'text-purple-900',
          subTextClass: 'text-purple-700'
        };
      default:
        return {
          name: 'Unknown',
          description: 'Unknown profile storage approach',
          bgClass: 'bg-gray-50',
          borderClass: 'border-gray-200',
          dotClass: 'bg-gray-500',
          textClass: 'text-gray-900',
          subTextClass: 'text-gray-700'
        };
    }
  };

  const approachInfo = getApproachInfo(knowledgeBaseApproach);

  // Handle gateway selection
  const handleGatewaySelect = (method) => {
    if (method === 'upload' || method === 'form') {
      // Both upload and form now go to the unified ProfileBuilder
      setActiveTab('edit');
    } else if (method === 'chat') {
      setActiveTab('chat');
      // Add initial message for help mode
      setChatMessages(prev => [...prev, {
        role: 'model',
        text: `Hi ${currentUser?.displayName || 'there'}! I'm here to help you with your profile. What would you like help with today?`
      }]);
    }
  };

  // Check if profile is empty (no structured data AND no uploaded files)
  const isProfileEmpty = !loadingProfile && !structuredProfile && profiles.length === 0;

  useEffect(() => {
    if (currentUser?.email) {
      loadProfiles();
      loadProfileMarkdown();
    }
  }, [currentUser, knowledgeBaseApproach]);

  // Auto-switch to Upload Documents tab when no profile exists
  useEffect(() => {
    if (!loadingProfile && !loading && isProfileEmpty && activeTab === 'view') {
      setActiveTab('files');
    }
  }, [loadingProfile, loading, isProfileEmpty, activeTab]);

  const loadProfiles = async () => {
    if (!currentUser?.email) {
      setError('User not authenticated');
      return;
    }

    setLoading(true);
    setError(null);
    try {
      // Use Vertex AI list for vertexai approach
      let response;
      if (knowledgeBaseApproach === 'vertexai') {
        response = await listVertexAIProfiles(currentUser.email);
      } else {
        response = await listStudentProfiles(currentUser.email);
      }

      if (response.success && response.documents) {
        // Transform documents to match frontend expectations
        const transformedProfiles = response.documents.map(doc => ({
          id: doc.name,
          name: doc.name,
          display_name: doc.display_name,
          size_bytes: doc.size_bytes,
          create_time: doc.create_time,
          state: doc.state,
          document: doc
        }));
        setProfiles(transformedProfiles);
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

  // Load profile directly from Profile Manager ES (no agent needed)
  const loadProfileMarkdown = async () => {
    if (!currentUser?.email) return;

    setLoadingProfile(true);
    try {
      // Fetch structured profile first (for visual display)
      const structuredData = await fetchStructuredProfile(currentUser.email);
      if (structuredData.success && structuredData.profile) {
        setStructuredProfile(structuredData.profile);
      }

      // Also fetch markdown for chat/AI editing
      const profileData = await fetchUserProfile(currentUser.email);
      if (profileData.success && profileData.content) {
        setProfileMarkdown(profileData.content);
      } else {
        setProfileMarkdown('# No Profile Found\n\nPlease upload a profile document to get started.');
      }
    } catch (err) {
      console.error('Error loading profile:', err);
      setProfileMarkdown('# Unable to Load Profile\n\nPlease make sure you have uploaded a profile document.');
    } finally {
      setLoadingProfile(false);
    }
  };

  // Refresh all profile data (called after CRUD operations)
  const refreshAll = async () => {
    console.log('[Profile] refreshAll called');
    // Clear existing data to force visible refresh
    setProfiles([]);
    setProfileMarkdown('');
    // Reload all data
    await loadProfiles();
    // Always reload profile data for all tabs to sync
    await loadProfileMarkdown();
    console.log('[Profile] refreshAll completed');

    // Trigger recomputation of fits for Launchpad universities (runs in background)
    if (currentUser?.email) {
      console.log('[Profile] Triggering Launchpad fit recomputation...');
      recomputeLaunchpadFits(currentUser.email).then(result => {
        if (result.success) {
          console.log(`[Profile] Recomputed ${result.recomputed} Launchpad fits`);
        }
      });
    }
  };




  // Format structured profile data as markdown - Uses FLAT profile fields
  const formatStructuredProfileAsMarkdown = (data) => {
    // Flat fields - direct access
    const name = data.name || 'Unknown';
    const school = data.school;
    const location = data.location;
    const grade = data.grade;
    const gpaWeighted = data.gpa_weighted;
    const gpaUnweighted = data.gpa_unweighted;
    const satTotal = data.sat_total;
    const satMath = data.sat_math;
    const satReading = data.sat_reading;
    const actComposite = data.act_composite;

    let md = `# Student Profile: ${name}\n\n`;

    // Personal Info
    md += `## 👤 Personal Information\n`;
    md += `- **School**: ${school || 'Not specified'}\n`;
    md += `- **Location**: ${location || 'Not specified'}\n`;
    if (grade) md += `- **Grade**: ${grade}\n`;
    md += `\n`;

    // Intended Major
    if (data.intended_major) {
      md += `## 🎯 Intended Major\n${data.intended_major}\n\n`;
    }

    // Academics - Using flat field names
    md += `## 📊 Academic Information\n`;
    md += `### GPA\n`;
    if (gpaWeighted) md += `- **Weighted GPA**: ${gpaWeighted}\n`;
    if (gpaUnweighted) md += `- **Unweighted GPA**: ${gpaUnweighted}\n`;
    if (data.gpa_uc) md += `- **UC GPA**: ${data.gpa_uc}\n`;
    md += `\n`;

    // Test Scores - Using flat field names
    const apExams = data.ap_exams || [];
    if (satTotal || actComposite || apExams.length > 0) {
      md += `### Test Scores\n`;
      if (satTotal) md += `- **SAT Total**: ${satTotal}${satMath ? ` (Math: ${satMath}, Reading: ${satReading})` : ''}\n`;
      if (actComposite) md += `- **ACT Composite**: ${actComposite}\n`;

      if (apExams.length > 0) {
        md += `\n**AP Exams:**\n`;
        apExams.forEach(ap => {
          md += `- ${ap.subject}: **${ap.score}**\n`;
        });
      }
      md += `\n`;
    }

    // Courses
    if (data.courses && data.courses.length > 0) {
      md += `## 📚 Courses\n`;
      const coursesByGrade = {};
      data.courses.forEach(c => {
        const grade = c.grade_level || 'Other';
        if (!coursesByGrade[grade]) coursesByGrade[grade] = [];
        coursesByGrade[grade].push(c);
      });

      Object.keys(coursesByGrade).sort().forEach(grade => {
        md += `### ${grade}th Grade\n`;
        coursesByGrade[grade].forEach(c => {
          const type = c.type && c.type !== 'Regular' ? ` (${c.type})` : '';
          const grades = c.semester1_grade && c.semester2_grade
            ? `: ${c.semester1_grade}/${c.semester2_grade}`
            : '';
          md += `- ${c.name}${type}${grades}\n`;
        });
        md += `\n`;
      });
    }

    // Extracurriculars
    if (data.extracurriculars && data.extracurriculars.length > 0) {
      md += `## 🏆 Extracurricular Activities\n`;
      data.extracurriculars.forEach(ec => {
        md += `### ${ec.name}\n`;
        if (ec.role) md += `**Role**: ${ec.role}`;
        if (ec.grades) md += ` | **Grades**: ${ec.grades}`;
        if (ec.hours_per_week) md += ` | **Hours/week**: ${ec.hours_per_week}`;
        md += `\n`;
        if (ec.description) md += `${ec.description}\n`;
        if (ec.achievements && ec.achievements.length > 0) {
          md += `**Achievements**: ${ec.achievements.join(', ')}\n`;
        }
        md += `\n`;
      });
    }

    // Awards
    if (data.awards && data.awards.length > 0) {
      md += `## 🏅 Awards & Honors\n`;
      data.awards.forEach(a => {
        md += `- **${a.name}**${a.grade ? ` (Grade ${a.grade})` : ''}\n`;
      });
      md += `\n`;
    }

    // Work Experience
    if (data.work_experience && data.work_experience.length > 0) {
      md += `## 💼 Work Experience\n`;
      data.work_experience.forEach(w => {
        md += `- **${w.employer}** - ${w.role}`;
        if (w.grades) md += ` (${w.grades})`;
        if (w.hours_per_week) md += ` - ${w.hours_per_week} hrs/week`;
        md += `\n`;
      });
      md += `\n`;
    }

    // Special Programs
    if (data.special_programs && data.special_programs.length > 0) {
      md += `## 🌟 Special Programs\n`;
      data.special_programs.forEach(sp => {
        md += `- **${sp.name}**${sp.grade ? ` (Grade ${sp.grade})` : ''}\n`;
        if (sp.description) md += `  ${sp.description}\n`;
      });
      md += `\n`;
    }

    // Leadership
    if (data.leadership_roles && data.leadership_roles.length > 0) {
      md += `## 👑 Leadership Roles\n`;
      data.leadership_roles.forEach(role => {
        md += `- ${role}\n`;
      });
    }

    return md;
  };


  // Handle sending chat message
  const handleSendMessage = async () => {
    if (!chatInput.trim() || isSending) return;

    const userMessage = chatInput.trim();
    setChatInput('');
    setChatMessages(prev => [...prev, { role: 'user', content: userMessage }]);
    setIsSending(true);

    try {
      const prompt = `[USER_EMAIL: ${currentUser.email}]
${userMessage}

If this is a request to update or modify my profile, make the changes and confirm what was updated.
If this is a question about my profile, answer based on my profile data.`;

      const response = await startSession(prompt);
      const fullResponse = extractFullResponse(response);
      const aiMessage = fullResponse.result || fullResponse;

      setChatMessages(prev => [...prev, { role: 'assistant', content: aiMessage }]);

      // Refresh profile markdown after updates
      if (userMessage.toLowerCase().includes('update') || userMessage.toLowerCase().includes('change') ||
        userMessage.toLowerCase().includes('add') || userMessage.toLowerCase().includes('remove')) {
        await loadProfileMarkdown();
      }
    } catch (err) {
      console.error('Error sending message:', err);
      setChatMessages(prev => [...prev, { role: 'assistant', content: 'Sorry, I encountered an error. Please try again.' }]);
    } finally {
      setIsSending(false);
    }
  };

  // Scroll chat to bottom
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages]);

  // Load profile when switching to view tab
  useEffect(() => {
    if (activeTab === 'view' && !profileMarkdown && !loadingProfile) {
      loadProfileMarkdown();
    }
  }, [activeTab]);

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
      // Upload all files in parallel with progressive status updates
      const uploadPromises = selectedFiles.map(async (file, index) => {
        try {
          // Phase 1: Uploading (0-30%)
          setUploadProgress(prev => ({
            ...prev,
            [file.name]: { status: 'uploading', progress: 10 }
          }));

          // Simulate upload progress
          await new Promise(r => setTimeout(r, 200));
          setUploadProgress(prev => ({
            ...prev,
            [file.name]: { status: 'uploading', progress: 30 }
          }));

          // Phase 2: Processing (30-60%)
          setUploadProgress(prev => ({
            ...prev,
            [file.name]: { status: 'processing', progress: 40 }
          }));

          // Use Vertex AI upload for vertexai approach
          let response;
          if (knowledgeBaseApproach === 'vertexai') {
            response = await uploadVertexAIProfile(file, currentUser.email);
          } else {
            response = await uploadStudentProfile(file, currentUser.email);
          }

          // Phase 3: Extracting profile data (60-90%)
          setUploadProgress(prev => ({
            ...prev,
            [file.name]: { status: 'extracting', progress: 70 }
          }));

          await new Promise(r => setTimeout(r, 300));
          setUploadProgress(prev => ({
            ...prev,
            [file.name]: { status: 'extracting', progress: 85 }
          }));

          if (response.success) {
            // Phase 4: Complete (100%)
            const extractedFields = response.extracted_fields || response.extractedFields || [];
            setUploadProgress(prev => ({
              ...prev,
              [file.name]: {
                status: 'success',
                progress: 100,
                extractedFields: extractedFields
              }
            }));
            return { success: true, filename: file.name, extractedFields };
          } else {
            setUploadProgress(prev => ({
              ...prev,
              [file.name]: { status: 'error', progress: 0, error: response.message }
            }));
            return { success: false, filename: file.name, error: response.message };
          }
        } catch (err) {
          console.error(`Upload error for ${file.name}: `, err);
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
          message: `Successfully uploaded ${successCount} file(s)${failCount > 0 ? `, ${failCount} failed` : ''} `
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

      // Refresh all profile data
      await refreshAll();

      // NOTE: Fits are now computed lazily when universities are added to Launchpad
      // This saves significant LLM costs by only computing fits for universities
      // the student is actually interested in
      if (successCount > 0) {
        console.log('[Profile] Upload complete - fits will be computed when universities are added to Launchpad');
      }
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

  const handleDelete = async (documentId, displayName) => {
    if (!confirm(`Are you sure you want to delete "${displayName}" ? `)) {
      return;
    }

    try {
      // Use Vertex AI delete for vertexai approach
      let response;
      if (knowledgeBaseApproach === 'vertexai') {
        response = await deleteVertexAIProfile(documentId, currentUser.email);
      } else {
        response = await deleteStudentProfile(documentId, currentUser.email, displayName);
      }
      if (response.success) {
        setUploadStatus({
          type: 'success',
          message: `Successfully deleted ${displayName} `
        });
        // Small delay to ensure ES has indexed the deletion
        await new Promise(resolve => setTimeout(resolve, 500));
        await refreshAll();
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

    if (!confirm(`Are you sure you want to delete ${selectedProfiles.length} profile(s) ? `)) {
      return;
    }

    setDeleting(true);
    setError(null);

    try {
      const deletePromises = selectedProfiles.map(profile =>
        deleteStudentProfile(profile.id, currentUser.email, profile.display_name)
      );

      const results = await Promise.all(deletePromises);
      const successCount = results.filter(r => r.success).length;
      const failCount = results.filter(r => !r.success).length;

      if (successCount > 0) {
        setUploadStatus({
          type: successCount === selectedProfiles.length ? 'success' : 'warning',
          message: `Successfully deleted ${successCount} profile(s)${failCount > 0 ? `, ${failCount} failed` : ''} `
        });
      } else {
        setError('All deletions failed');
      }

      setSelectedProfiles([]);
      // Small delay to ensure ES has indexed all deletions
      await new Promise(resolve => setTimeout(resolve, 500));
      await refreshAll();
    } catch (err) {
      console.error('Bulk delete error:', err);
      setError('Failed to delete profiles');
    } finally {
      setDeleting(false);
    }
  };

  const toggleProfileSelection = (profile) => {
    setSelectedProfiles(prev => {
      const isSelected = prev.some(p => p.id === profile.id);
      if (isSelected) {
        return prev.filter(p => p.id !== profile.id);
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

  // Handle complete profile reset
  const handleResetProfile = async () => {
    if (!currentUser?.email) return;

    setResetting(true);
    try {
      const result = await resetAllProfile(currentUser.email, resetOptions.deleteCollegeList);
      if (result.success) {
        setUploadStatus({
          type: 'success',
          message: result.message || 'Profile reset complete'
        });
        setShowResetModal(false);
        setResetOptions({ deleteCollegeList: false });
        // Small delay for ES consistency
        await new Promise(resolve => setTimeout(resolve, 500));
        await refreshAll();
        // Clear local state
        setProfiles([]);
        setProfileMarkdown('');
        setStructuredProfile(null);
      } else {
        setError(result.error || 'Failed to reset profile');
      }
    } catch (err) {
      console.error('Reset profile error:', err);
      setError('Failed to reset profile. Please try again.');
    } finally {
      setResetting(false);
    }
  };

  // Reset Profile Modal
  const ResetProfileModal = () => (
    showResetModal && (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
        <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full overflow-hidden">
          <div className="p-6 border-b border-gray-100">
            <h3 className="text-xl font-bold text-red-600 flex items-center gap-2">
              <TrashIcon className="h-6 w-6" />
              Reset All Profile Data
            </h3>
          </div>

          <div className="p-6 space-y-4">
            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
              <p className="text-red-800 text-sm font-medium">
                This action will permanently delete:
              </p>
              <ul className="mt-2 text-red-700 text-sm list-disc list-inside space-y-1">
                <li>All uploaded profile documents</li>
                <li>Your onboarding profile data</li>
                <li>All computed fit analyses</li>
              </ul>
            </div>

            <label className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg cursor-pointer hover:bg-gray-100">
              <input
                type="checkbox"
                checked={resetOptions.deleteCollegeList}
                onChange={(e) => setResetOptions(prev => ({ ...prev, deleteCollegeList: e.target.checked }))}
                className="h-4 w-4 text-red-600 rounded border-gray-300 focus:ring-red-500"
              />
              <span className="text-sm text-gray-700">
                Also delete my college list (Launchpad)
              </span>
            </label>

            <p className="text-gray-500 text-sm">
              You will need to re-complete onboarding after resetting.
            </p>
          </div>

          <div className="p-6 bg-gray-50 flex gap-3 justify-end">
            <button
              onClick={() => {
                setShowResetModal(false);
                setResetOptions({ deleteCollegeList: false });
              }}
              className="px-4 py-2 text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              onClick={handleResetProfile}
              disabled={resetting}
              className="px-4 py-2 text-white bg-red-600 rounded-lg hover:bg-red-700 disabled:opacity-50 flex items-center gap-2"
            >
              {resetting ? (
                <>
                  <ArrowPathIcon className="h-4 w-4 animate-spin" />
                  Resetting...
                </>
              ) : (
                <>
                  <TrashIcon className="h-4 w-4" />
                  Reset Everything
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    )
  );

  return (
    <div className="space-y-8">
      {/* Hero Header - Subtle light background with accent */}
      <div className="bg-white rounded-2xl p-6 border border-gray-200 shadow-sm">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 bg-gradient-to-br from-amber-400 to-orange-500 rounded-xl flex items-center justify-center shadow-md">
              <UserCircleIcon className="h-6 w-6 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-gray-900">Student Profile</h1>
              <p className="mt-0.5 text-sm text-gray-500 max-w-lg">
                Upload your academic profile, transcript, and activities for personalized analysis.
              </p>
            </div>
          </div>

          {/* Approach badge removed - keeping UI clean */}
        </div>
      </div>

      {/* Tab Navigation - Always visible */}
      <div className="flex border-b border-gray-200 mb-6 overflow-x-auto">
        {/* Upload Documents - Always first */}
        <button
          onClick={() => setActiveTab('files')}
          className={`px-4 py-3 font-medium text-sm border-b-2 transition-colors duration-200 flex items-center gap-2 whitespace-nowrap ${activeTab === 'files'
            ? 'border-indigo-600 text-indigo-600'
            : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
        >
          <DocumentTextIcon className="h-5 w-5" />
          Upload Documents
        </button>

        {/* View Profile - Only show if there's data */}
        {!isProfileEmpty && (
          <button
            onClick={() => setActiveTab('view')}
            className={`px-4 py-3 font-medium text-sm border-b-2 transition-colors duration-200 flex items-center gap-2 whitespace-nowrap ${activeTab === 'view'
              ? 'border-indigo-600 text-indigo-600'
              : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
          >
            <UserCircleIcon className="h-5 w-5" />
            View Profile
          </button>
        )}

        <button
          onClick={() => setActiveTab('form')}
          className={`px-4 py-3 font-medium text-sm border-b-2 transition-colors duration-200 flex items-center gap-2 whitespace-nowrap ${activeTab === 'form'
            ? 'border-indigo-600 text-indigo-600'
            : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
        >
          <PencilSquareIcon className="h-5 w-5" />
          Profile Editor
        </button>

        <button
          onClick={() => setActiveTab('guided')}
          className={`px-4 py-3 font-medium text-sm border-b-2 transition-colors duration-200 flex items-center gap-2 whitespace-nowrap ${activeTab === 'guided'
            ? 'border-purple-600 text-purple-600'
            : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
        >
          <SparklesIcon className="h-5 w-5" />
          Take Assessment
        </button>

        <button
          onClick={() => setActiveTab('chat')}
          className={`px-4 py-3 font-medium text-sm border-b-2 transition-colors duration-200 flex items-center gap-2 whitespace-nowrap ${activeTab === 'chat'
            ? 'border-indigo-600 text-indigo-600'
            : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
        >
          <ChatBubbleLeftRightIcon className="h-5 w-5" />
          Ask & Update
        </button>
      </div>

      {/* Content Area */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 min-h-[600px]">

        {/* VIEW TAB */}
        {activeTab === 'view' && (
          <div className="p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-semibold text-gray-900 flex items-center gap-3">
                <div className="p-2 bg-gray-100 rounded-xl">
                  <UserCircleIcon className="h-5 w-5 text-gray-600" />
                </div>
                Your Profile
              </h2>
              <div className="flex gap-2">
                <button
                  onClick={loadProfileMarkdown}
                  disabled={loadingProfile}
                  className="flex items-center gap-2 px-3 py-2 text-sm text-gray-600 hover:text-gray-900 rounded-lg border border-gray-200 hover:border-gray-300 transition-colors"
                >
                  <ArrowPathIcon className={`h-4 w-4 ${loadingProfile ? 'animate-spin' : ''}`} />
                  Refresh
                </button>
                {!isProfileEmpty && (
                  <button
                    onClick={() => setShowResetModal(true)}
                    className="flex items-center gap-2 px-3 py-2 text-sm text-red-600 hover:text-red-700 rounded-lg border border-red-200 hover:border-red-300 hover:bg-red-50 transition-colors"
                  >
                    <TrashIcon className="h-4 w-4" />
                    Reset Profile
                  </button>
                )}
              </div>
            </div>

            {loadingProfile ? (
              <div className="flex flex-col items-center justify-center py-16">
                <div className="p-4 bg-gray-100 rounded-full mb-4">
                  <ArrowPathIcon className="h-8 w-8 text-gray-500 animate-spin" />
                </div>
                <span className="text-gray-600 font-medium">Loading your profile...</span>
              </div>
            ) : structuredProfile ? (
              <ProfileViewCard profileData={structuredProfile} />
            ) : (
              <div className="prose prose-sm max-w-none prose-headings:text-gray-900 prose-p:text-gray-600 prose-li:text-gray-600 prose-strong:text-gray-800 bg-white rounded-xl p-6 shadow-sm">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {profileMarkdown || '# No Profile Data\n\nUpload a profile document or click "Refresh" to load your profile.'}
                </ReactMarkdown>
              </div>
            )}
          </div>
        )}

        {/* FORM TAB (Questionnaire only) */}
        {activeTab === 'form' && (
          <div className="p-4">
            <ProfileBuilder profile={structuredProfile} onProfileUpdate={loadProfileMarkdown} />
          </div>
        )}

        {/* GUIDED TAB (AI asks questions based on missing fields) */}
        {activeTab === 'guided' && (
          <GuidedInterview profile={structuredProfile} onProfileUpdate={loadProfileMarkdown} />
        )}

        {/* Chat Tab */}
        {activeTab === 'chat' && (
          <div className="bg-white shadow-sm rounded-2xl flex flex-col h-[600px] border border-gray-200">
            {/* Chat Header */}
            <div className="p-4 border-b border-gray-100">
              <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-3">
                <div className="p-2 bg-gray-100 rounded-xl">
                  <SparklesIcon className="h-5 w-5 text-gray-600" />
                </div>
                Edit Profile with AI
              </h2>
              <p className="text-sm text-gray-500 mt-1 ml-12">
                Tell me what to update in your profile. Example: "Update my GPA to 3.9" or "Add robotics club to activities"
              </p>
            </div>

            {/* Chat Messages */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {chatMessages.length === 0 ? (
                <div className="text-center py-8 text-gray-400">
                  <div className="p-4 bg-gray-100 rounded-2xl inline-block mb-4">
                    <ChatBubbleLeftRightIcon className="h-10 w-10 text-gray-500" />
                  </div>
                  <p className="text-gray-600">Start a conversation to edit your profile</p>
                  <div className="mt-4 flex flex-wrap gap-2 justify-center">
                    {['Update my GPA to 3.85', 'Add SAT score: 1480', 'Add tennis to activities', 'Change intended major to Computer Science'].map(suggestion => (
                      <button
                        key={suggestion}
                        onClick={() => setChatInput(suggestion)}
                        className="px-3 py-1.5 bg-gray-100 text-gray-700 rounded-full text-sm hover:bg-gray-200 border border-gray-200 transition-colors"
                      >
                        {suggestion}
                      </button>
                    ))}
                  </div>
                </div>
              ) : (
                chatMessages.map((msg, idx) => (
                  <div
                    key={idx}
                    className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                  >
                    <div
                      className={`max-w-[80%] p-3 rounded-2xl ${msg.role === 'user'
                        ? 'bg-gray-900 text-white'
                        : 'bg-gray-50 text-gray-800 border border-gray-200'
                        }`}
                    >
                      {msg.role === 'assistant' ? (
                        <div className="prose prose-sm max-w-none prose-p:text-gray-800 prose-p:my-1">
                          <ReactMarkdown remarkPlugins={[remarkGfm]}>
                            {msg.content}
                          </ReactMarkdown>
                        </div>
                      ) : (
                        <p>{msg.content}</p>
                      )}
                    </div>
                  </div>
                ))
              )}
              {isSending && (
                <div className="flex justify-start">
                  <div className="bg-gray-100 p-3 rounded-2xl border border-gray-200">
                    <div className="flex items-center gap-2 text-gray-600">
                      <ArrowPathIcon className="h-4 w-4 animate-spin" />
                      <span>Thinking...</span>
                    </div>
                  </div>
                </div>
              )}
              <div ref={chatEndRef} />
            </div>

            {/* Chat Input */}
            <div className="p-4 border-t border-gray-100 bg-gray-50">
              <div className="flex gap-2">
                <input
                  type="text"
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleSendMessage()}
                  placeholder="Tell me what to update..."
                  className="flex-1 px-4 py-2.5 border border-gray-200 rounded-xl focus:ring-2 focus:ring-gray-400 focus:border-transparent bg-white"
                  disabled={isSending}
                />
                <button
                  onClick={handleSendMessage}
                  disabled={!chatInput.trim() || isSending}
                  className="px-4 py-2 bg-gray-900 text-white rounded-xl hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                >
                  <PaperAirplaneIcon className="h-5 w-5" />
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Files Tab - Original Upload Section */}
        {activeTab === 'files' && (
          <>

            {/* Upload Section */}
            <div className="bg-white rounded-2xl p-6 border border-gray-200 shadow-sm">
              <h2 className="text-xl font-semibold text-gray-900 mb-2 flex items-center gap-2">
                <div className="p-1.5 bg-indigo-100 rounded-lg">
                  <DocumentArrowUpIcon className="h-5 w-5 text-indigo-600" />
                </div>
                Upload Your Documents
              </h2>
              <p className="text-gray-600 mb-4">
                Upload any documents that showcase your achievements. Our AI will automatically extract relevant information to build your profile.
              </p>

              {/* Document Types */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
                <div className="flex items-center gap-2 text-sm text-gray-600 bg-gray-50 px-3 py-2 rounded-lg">
                  <span>📄</span> Transcripts
                </div>
                <div className="flex items-center gap-2 text-sm text-gray-600 bg-gray-50 px-3 py-2 rounded-lg">
                  <span>🏆</span> Award Certificates
                </div>
                <div className="flex items-center gap-2 text-sm text-gray-600 bg-gray-50 px-3 py-2 rounded-lg">
                  <span>📝</span> Resumes
                </div>
                <div className="flex items-center gap-2 text-sm text-gray-600 bg-gray-50 px-3 py-2 rounded-lg">
                  <span>🤝</span> Volunteer Records
                </div>
              </div>

              <div className="space-y-4">
                {/* File Input */}
                <div>
                  <label className="block text-sm font-medium text-gray-600 mb-2">
                    Select Files (PDF, DOCX, TXT) - Multiple files supported
                  </label>
                  <div className="flex items-center space-x-4">
                    <label className="flex-1 flex items-center justify-center px-6 py-6 border-2 border-dashed border-gray-300 rounded-2xl cursor-pointer hover:border-gray-400 hover:bg-gray-50 transition-colors">
                      <div className="text-center">
                        <DocumentArrowUpIcon className="mx-auto h-10 w-10 text-gray-400" />
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
                        accept=".pdf,.docx,.txt,.doc,.md,.markdown"
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

                {/* Upload Progress with Visual Bars */}
                {Object.keys(uploadProgress).length > 0 && (
                  <div className="bg-gray-50 rounded-lg p-4">
                    <h3 className="text-sm font-medium text-gray-700 mb-3">Processing Documents:</h3>
                    <div className="space-y-3">
                      {Object.entries(uploadProgress).map(([filename, progress]) => (
                        <div key={filename} className="space-y-1">
                          <div className="flex items-center justify-between text-sm">
                            <span className="text-gray-900 font-medium truncate max-w-[200px]" title={filename}>
                              {filename}
                            </span>
                            <span className={`flex items-center text-xs font-medium ${progress.status === 'uploading' ? 'text-blue-600' :
                              progress.status === 'processing' ? 'text-amber-600' :
                                progress.status === 'extracting' ? 'text-purple-600' :
                                  progress.status === 'success' ? 'text-green-600' :
                                    'text-red-600'
                              }`}>
                              {progress.status === 'uploading' && (
                                <>
                                  <ArrowPathIcon className="h-3 w-3 mr-1 animate-spin" />
                                  Uploading... {progress.progress}%
                                </>
                              )}
                              {progress.status === 'processing' && (
                                <>
                                  <ArrowPathIcon className="h-3 w-3 mr-1 animate-spin" />
                                  Processing... {progress.progress}%
                                </>
                              )}
                              {progress.status === 'extracting' && (
                                <>
                                  <SparklesIcon className="h-3 w-3 mr-1 animate-pulse" />
                                  Extracting profile data... {progress.progress}%
                                </>
                              )}
                              {progress.status === 'success' && (
                                <>
                                  <CheckCircleIcon className="h-3 w-3 mr-1" />
                                  Complete
                                </>
                              )}
                              {progress.status === 'error' && (
                                <>
                                  <XCircleIcon className="h-3 w-3 mr-1" />
                                  Failed
                                </>
                              )}
                            </span>
                          </div>
                          {/* Progress Bar */}
                          <div className="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
                            <div
                              className={`h-full rounded-full transition-all duration-300 ${progress.status === 'uploading' ? 'bg-blue-500' :
                                progress.status === 'processing' ? 'bg-amber-500' :
                                  progress.status === 'extracting' ? 'bg-purple-500' :
                                    progress.status === 'success' ? 'bg-green-500' :
                                      'bg-red-500'
                                }`}
                              style={{ width: `${progress.progress || 0}%` }}
                            />
                          </div>
                          {/* Error message if present */}
                          {progress.error && (
                            <p className="text-xs text-red-500 mt-1">{progress.error}</p>
                          )}
                          {/* Extracted fields summary */}
                          {progress.extractedFields && progress.extractedFields.length > 0 && (
                            <p className="text-xs text-green-600 mt-1">
                              ✓ Extracted: {progress.extractedFields.join(', ')}
                            </p>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Upload Button */}
                <button
                  onClick={handleUpload}
                  disabled={selectedFiles.length === 0 || uploading}
                  className={`w-full flex items-center justify-center px-6 py-3 border border-transparent text-base font-medium rounded-xl text-white ${selectedFiles.length === 0 || uploading
                    ? 'bg-gray-300 cursor-not-allowed'
                    : 'bg-gray-900 hover:bg-gray-800'
                    } transition-all duration-200`}
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
                  <div className={`p-4 rounded-lg border ${uploadStatus.type === 'success' ? 'bg-green-50 border-green-200' :
                    uploadStatus.type === 'warning' ? 'bg-yellow-50 border-yellow-200' : 'bg-red-50 border-red-200'
                    }`}>
                    <div className="flex items-start">
                      {uploadStatus.type === 'success' ? (
                        <CheckCircleIcon className="h-5 w-5 text-green-500 mt-0.5" />
                      ) : uploadStatus.type === 'warning' ? (
                        <CheckCircleIcon className="h-5 w-5 text-yellow-500 mt-0.5" />
                      ) : (
                        <XCircleIcon className="h-5 w-5 text-red-500 mt-0.5" />
                      )}
                      <p className={`ml-3 text-sm font-medium ${uploadStatus.type === 'success' ? 'text-green-800' :
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
              <div className="mt-6 p-4 bg-gray-50 rounded-xl border border-gray-200">
                <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
                  <SparklesIcon className="h-4 w-4 text-gray-500" />
                  What to Include:
                </h3>
                <ul className="text-sm text-gray-600 space-y-1.5 list-disc list-inside">
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
            <div className="bg-white rounded-2xl p-6 border border-gray-200 shadow-sm">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-gray-100 rounded-xl">
                    <DocumentTextIcon className="h-5 w-5 text-gray-600" />
                  </div>
                  <h2 className="text-lg font-semibold text-gray-900">Your Documents</h2>
                  {selectedProfiles.length > 0 && (
                    <span className="text-sm text-gray-600 bg-gray-100 px-2 py-0.5 rounded-full">
                      {selectedProfiles.length} selected
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  {selectedProfiles.length > 0 && (
                    <button
                      onClick={handleBulkDelete}
                      disabled={deleting}
                      className="inline-flex items-center px-3 py-2 text-sm font-medium rounded-xl text-white bg-red-500 hover:bg-red-600 disabled:opacity-50"
                    >
                      <TrashIcon className="h-4 w-4 mr-2" />
                      {deleting ? 'Deleting...' : `Delete ${selectedProfiles.length} `}
                    </button>
                  )}
                  <button
                    onClick={loadProfiles}
                    disabled={loading}
                    className="flex items-center px-3 py-2 text-sm text-gray-600 hover:text-gray-900 transition-colors bg-white border border-gray-200 rounded-xl hover:border-gray-300"
                  >
                    <ArrowPathIcon className={`h-4 w-4 mr-1 ${loading ? 'animate-spin' : ''}`} />
                    Refresh
                  </button>
                </div>
              </div>

              {loading ? (
                <div className="text-center py-12">
                  <div className="p-4 bg-gray-100 rounded-full inline-block mb-3">
                    <ArrowPathIcon className="h-8 w-8 text-gray-500 animate-spin" />
                  </div>
                  <p className="text-sm text-gray-500">Loading profiles...</p>
                </div>
              ) : profiles.length === 0 ? (
                <div className="text-center py-12">
                  <div className="p-4 bg-gray-100 rounded-full inline-block mb-3">
                    <DocumentTextIcon className="h-10 w-10 text-gray-400" />
                  </div>
                  <p className="text-sm text-gray-500">No profiles uploaded yet</p>
                  <p className="text-xs text-gray-400 mt-1">Upload your first profile above</p>
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
                          className="h-4 w-4 text-gray-900 border-gray-300 rounded focus:ring-gray-500"
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
                          className={`flex items-center justify-between p-4 border rounded-xl transition-all ${isSelected ? 'border-gray-400 bg-gray-50' : 'border-gray-200 hover:bg-gray-50 hover:border-gray-300'
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
                                <span className={`inline - flex items - center px - 2 py - 0.5 rounded text - xs font - medium ${profile.state === 'ACTIVE' ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'
                                  } `}>
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
                              onClick={() => handleDelete(profile.id, profile.display_name)}
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
          </>
        )}
      </div>

      {/* Reset Profile Modal */}
      <ResetProfileModal />
    </div>
  );
}

export default Profile;
