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
  uploadVertexAIProfile,
  listVertexAIProfiles,
  deleteVertexAIProfile,
  startSession,
  extractFullResponse,
  computeAllFits
} from '../services/api';

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

  // New state for tabs, profile view, and chat
  const [activeTab, setActiveTab] = useState('view'); // 'view' | 'chat' | 'files'
  const [profileMarkdown, setProfileMarkdown] = useState('');
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

  useEffect(() => {
    if (currentUser?.email) {
      loadProfiles();
    }
  }, [currentUser, knowledgeBaseApproach]); // Added knowledgeBaseApproach to dependencies

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
      // Fetch profile directly from Profile Manager ES
      const profileData = await fetchUserProfile(currentUser.email);

      if (profileData.success && profileData.content) {
        // Content IS the markdown - display directly
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
    // Reload profiles
    await loadProfiles();
    // If we're on the view tab, also reload markdown
    if (activeTab === 'view') {
      await loadProfileMarkdown();
    }
    console.log('[Profile] refreshAll completed');
  };




  // Format structured profile data as markdown
  const formatStructuredProfileAsMarkdown = (data) => {
    const pi = data.personal_info || {};
    const acad = data.academics || {};
    const gpa = acad.gpa || {};
    const ts = data.test_scores || {};
    const sat = ts.sat || {};
    const act = ts.act || {};

    let md = `# Student Profile: ${pi.name || 'Unknown'}\n\n`;

    // Personal Info
    md += `## 👤 Personal Information\n`;
    md += `- **School**: ${pi.school || 'Not specified'}\n`;
    md += `- **Location**: ${pi.location || 'Not specified'}\n`;
    if (pi.grade) md += `- **Grade**: ${pi.grade}\n`;
    if (pi.ethnicity) md += `- **Ethnicity**: ${pi.ethnicity}\n`;
    md += `\n`;

    // Intended Major
    if (data.intended_major) {
      md += `## 🎯 Intended Major\n${data.intended_major}\n\n`;
    }

    // Academics
    md += `## 📊 Academic Information\n`;
    md += `### GPA\n`;
    if (gpa.weighted) md += `- **Weighted GPA**: ${gpa.weighted}\n`;
    if (gpa.unweighted) md += `- **Unweighted GPA**: ${gpa.unweighted}\n`;
    if (gpa.uc_weighted) md += `- **UC Weighted GPA**: ${gpa.uc_weighted}\n`;
    if (gpa.uc_unweighted) md += `- **UC Unweighted GPA**: ${gpa.uc_unweighted}\n`;
    if (acad.total_semesters) md += `- **Total Semesters**: ${acad.total_semesters}\n`;
    md += `\n`;

    // Test Scores
    if (sat.total || act.composite || (ts.ap_exams && ts.ap_exams.length > 0)) {
      md += `### Test Scores\n`;
      if (sat.total) md += `- **SAT Total**: ${sat.total}${sat.math ? ` (Math: ${sat.math}, Reading: ${sat.reading})` : ''}\n`;
      if (act.composite) md += `- **ACT Composite**: ${act.composite}\n`;

      if (ts.ap_exams && ts.ap_exams.length > 0) {
        md += `\n**AP Exams:**\n`;
        ts.ap_exams.forEach(ap => {
          md += `- ${ap.subject}: **${ap.score}**${ap.subscore ? ` (${ap.subscore})` : ''}\n`;
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
      // Upload all files in parallel
      const uploadPromises = selectedFiles.map(async (file, index) => {
        try {
          setUploadProgress(prev => ({
            ...prev,
            [file.name]: { status: 'uploading', progress: 0 }
          }));

          // Use Vertex AI upload for vertexai approach
          let response;
          if (knowledgeBaseApproach === 'vertexai') {
            response = await uploadVertexAIProfile(file, currentUser.email);
          } else {
            response = await uploadStudentProfile(file, currentUser.email);
          }

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

      // Trigger fit computation in background if at least one upload succeeded
      if (successCount > 0 && currentUser?.email) {
        console.log('[Profile] Triggering fit computation for all universities...');
        // Don't await - let it run in background
        computeAllFits(currentUser.email).then(result => {
          if (result.success) {
            console.log(`[Profile] Fit computation complete: ${result.computed} universities`);
          } else {
            console.warn('[Profile] Fit computation failed:', result.error);
          }
        });
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

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Student Profile</h1>
        <p className="mt-2 text-gray-600">
          Upload your academic profile, transcript, and extracurricular information. This will be used for your admissions analysis.
        </p>

        {/* Approach Indicator */}
        <div className={`mt-4 inline-flex items-center px-4 py-2 rounded-lg border ${approachInfo.bgClass} ${approachInfo.borderClass}`}>
          <div className={`w-2 h-2 rounded-full mr-3 ${approachInfo.dotClass}`}></div>
          <div>
            <div className={`text-sm font-semibold ${approachInfo.textClass}`}>
              {approachInfo.name}
            </div>
            <div className={`text-xs font-medium ${approachInfo.subTextClass}`}>
              {approachInfo.description}
            </div>
          </div>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="bg-white shadow rounded-lg p-1 flex gap-1">
        <button
          onClick={() => setActiveTab('view')}
          className={`flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-lg font-medium transition-all ${activeTab === 'view'
            ? 'bg-gradient-to-r from-purple-600 to-blue-600 text-white shadow-lg'
            : 'text-gray-600 hover:bg-gray-100'
            }`}
        >
          <EyeIcon className="h-5 w-5" />
          View Profile
        </button>
        <button
          onClick={() => setActiveTab('chat')}
          className={`flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-lg font-medium transition-all ${activeTab === 'chat'
            ? 'bg-gradient-to-r from-purple-600 to-blue-600 text-white shadow-lg'
            : 'text-gray-600 hover:bg-gray-100'
            }`}
        >
          <ChatBubbleLeftRightIcon className="h-5 w-5" />
          Edit with AI
        </button>
        <button
          onClick={() => setActiveTab('files')}
          className={`flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-lg font-medium transition-all ${activeTab === 'files'
            ? 'bg-gradient-to-r from-purple-600 to-blue-600 text-white shadow-lg'
            : 'text-gray-600 hover:bg-gray-100'
            }`}
        >
          <DocumentArrowUpIcon className="h-5 w-5" />
          Upload Files
        </button>
      </div>

      {/* View Profile Tab */}
      {activeTab === 'view' && (
        <div className="bg-white shadow rounded-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold text-gray-900 flex items-center gap-2">
              <UserCircleIcon className="h-6 w-6 text-purple-600" />
              Your Profile
            </h2>
            <button
              onClick={loadProfileMarkdown}
              disabled={loadingProfile}
              className="flex items-center gap-2 px-3 py-2 text-sm text-gray-600 hover:text-purple-600 transition-colors"
            >
              <ArrowPathIcon className={`h-4 w-4 ${loadingProfile ? 'animate-spin' : ''}`} />
              Refresh
            </button>
          </div>

          {loadingProfile ? (
            <div className="flex items-center justify-center py-12">
              <ArrowPathIcon className="h-8 w-8 text-purple-600 animate-spin" />
              <span className="ml-3 text-gray-500">Loading your profile...</span>
            </div>
          ) : (
            <div className="prose prose-sm max-w-none prose-headings:text-gray-900 prose-p:text-gray-600 prose-li:text-gray-600 prose-strong:text-gray-800">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {profileMarkdown || '# No Profile Data\n\nUpload a profile document or click "Refresh" to load your profile.'}
              </ReactMarkdown>
            </div>
          )}
        </div>
      )}

      {/* Chat Tab */}
      {activeTab === 'chat' && (
        <div className="bg-white shadow rounded-lg flex flex-col h-[600px]">
          {/* Chat Header */}
          <div className="p-4 border-b border-gray-200">
            <h2 className="text-xl font-semibold text-gray-900 flex items-center gap-2">
              <SparklesIcon className="h-6 w-6 text-purple-600" />
              Edit Profile with AI
            </h2>
            <p className="text-sm text-gray-500 mt-1">
              Tell me what to update in your profile. Example: "Update my GPA to 3.9" or "Add robotics club to activities"
            </p>
          </div>

          {/* Chat Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {chatMessages.length === 0 ? (
              <div className="text-center py-8 text-gray-400">
                <ChatBubbleLeftRightIcon className="h-12 w-12 mx-auto mb-4 opacity-50" />
                <p>Start a conversation to edit your profile</p>
                <div className="mt-4 flex flex-wrap gap-2 justify-center">
                  {['Update my GPA to 3.85', 'Add SAT score: 1480', 'Add tennis to activities', 'Change intended major to Computer Science'].map(suggestion => (
                    <button
                      key={suggestion}
                      onClick={() => setChatInput(suggestion)}
                      className="px-3 py-1 bg-purple-50 text-purple-700 rounded-full text-sm hover:bg-purple-100 transition-colors"
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
                    className={`max-w-[80%] p-3 rounded-lg ${msg.role === 'user'
                      ? 'bg-purple-600 text-white rounded-br-sm'
                      : 'bg-gray-100 text-gray-800 rounded-bl-sm'
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
                <div className="bg-gray-100 p-3 rounded-lg rounded-bl-sm">
                  <div className="flex items-center gap-2 text-gray-500">
                    <ArrowPathIcon className="h-4 w-4 animate-spin" />
                    <span>Thinking...</span>
                  </div>
                </div>
              </div>
            )}
            <div ref={chatEndRef} />
          </div>

          {/* Chat Input */}
          <div className="p-4 border-t border-gray-200">
            <div className="flex gap-2">
              <input
                type="text"
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleSendMessage()}
                placeholder="Tell me what to update..."
                className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                disabled={isSending}
              />
              <button
                onClick={handleSendMessage}
                disabled={!chatInput.trim() || isSending}
                className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
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
                className={`w-full flex items-center justify-center px-6 py-3 border border-transparent text-base font-semibold rounded-lg text-white shadow-sm ${selectedFiles.length === 0 || uploading
                  ? 'bg-gray-400 cursor-not-allowed'
                  : 'bg-primary hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary'
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
                    {deleting ? 'Deleting...' : `Delete ${selectedProfiles.length} `}
                  </button>
                )}
                <button
                  onClick={loadProfiles}
                  disabled={loading}
                  className="flex items-center px-3 py-2 text-sm text-gray-700 hover:text-primary transition-colors"
                >
                  <ArrowPathIcon className={`h - 4 w - 4 mr - 1 ${loading ? 'animate-spin' : ''} `} />
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
                        className={`flex items - center justify - between p - 4 border rounded - lg transition - colors ${isSelected ? 'border-primary bg-blue-50' : 'border-gray-200 hover:bg-gray-50'
                          } `}
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
  );
}

export default Profile;
