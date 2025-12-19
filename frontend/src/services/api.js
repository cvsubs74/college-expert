import axios from 'axios';

// Get API base URLs from environment or use defaults
const RAG_AGENT_URL = import.meta.env.VITE_RAG_AGENT_URL;
const ES_AGENT_URL = import.meta.env.VITE_ES_AGENT_URL;
const HYBRID_AGENT_URL = import.meta.env.VITE_HYBRID_AGENT_URL;
const VERTEXAI_AGENT_URL = import.meta.env.VITE_VERTEXAI_AGENT_URL;
const VERTEXAI_KNOWLEDGE_BASE_URL = import.meta.env.VITE_KNOWLEDGE_BASE_VERTEXAI_URL;
const VERTEXAI_PROFILE_MANAGER_URL = import.meta.env.VITE_PROFILE_MANAGER_VERTEXAI_URL;
const KNOWLEDGE_BASE_URL = import.meta.env.VITE_KNOWLEDGE_BASE_URL;
const KNOWLEDGE_BASE_ES_URL = import.meta.env.VITE_KNOWLEDGE_BASE_ES_URL;
const KNOWLEDGE_BASE_UNIVERSITIES_URL = import.meta.env.VITE_KNOWLEDGE_BASE_UNIVERSITIES_URL;
const PROFILE_MANAGER_URL = import.meta.env.VITE_PROFILE_MANAGER_URL;
const PROFILE_MANAGER_ES_URL = import.meta.env.VITE_PROFILE_MANAGER_ES_URL;

// Get knowledge base approach from environment
const KNOWLEDGE_BASE_APPROACH = import.meta.env.VITE_KNOWLEDGE_BASE_APPROACH || 'rag';

// Get the appropriate agent URL based on approach
const getAgentUrl = () => {
  const approach = localStorage.getItem('knowledgeBaseApproach') || KNOWLEDGE_BASE_APPROACH;
  if (approach === 'hybrid') return HYBRID_AGENT_URL;
  if (approach === 'elasticsearch') return ES_AGENT_URL;
  if (approach === 'vertexai') return VERTEXAI_AGENT_URL;
  return RAG_AGENT_URL;
};

// Get the app name based on approach
const getAppName = () => {
  const approach = localStorage.getItem('knowledgeBaseApproach') || KNOWLEDGE_BASE_APPROACH;
  if (approach === 'hybrid') return 'college_expert_hybrid';
  if (approach === 'elasticsearch') return 'college_expert_es';
  if (approach === 'vertexai') return 'college_expert_adk';
  return 'college_expert_rag';
};

// Determine profile manager URL based on approach
// Note: Hybrid approach uses profile_manager_es for student profiles
const getProfileManagerUrl = () => {
  const approach = localStorage.getItem('knowledgeBaseApproach') || KNOWLEDGE_BASE_APPROACH;
  if (approach === 'hybrid') {
    return import.meta.env.VITE_PROFILE_MANAGER_ES_URL || 'https://profile-manager-es-pfnwjfp26a-ue.a.run.app';
  }
  if (approach === 'elasticsearch') {
    return import.meta.env.VITE_PROFILE_MANAGER_ES_URL || 'https://profile-manager-es-pfnwjfp26a-ue.a.run.app';
  }
  if (approach === 'vertexai') {
    return import.meta.env.VITE_PROFILE_MANAGER_VERTEXAI_URL || 'https://profile-manager-vertexai-pfnwjfp26a-ue.a.run.app';
  }
  return import.meta.env.VITE_PROFILE_MANAGER_URL || 'https://profile-manager-pfnwjfp26a-ue.a.run.app';
};

// Create axios instance for agent API
const api = axios.create({
  timeout: 300000, // 5 minutes for agent processing (complex analysis with multiple sub-agents)
  headers: {
    'Content-Type': 'application/json',
  },
});

// Note: We don't create static axios instances for profile/KB managers
// because the baseURL needs to change dynamically when user switches approaches.
// Instead, we'll use axios directly with the dynamic URL in each function.

console.log(`[FRONTEND] Using knowledge base approach: ${KNOWLEDGE_BASE_APPROACH}`);
console.log(`[FRONTEND] Profile manager URL: ${getProfileManagerUrl()}`);

// Session management - use localStorage to persist across page changes
const SESSION_STORAGE_KEY = 'college_counselor_session_id';
const APPROACH_STORAGE_KEY = 'knowledgeBaseApproach';

const getSessionId = () => {
  return localStorage.getItem(SESSION_STORAGE_KEY);
};

const setSessionId = (sessionId) => {
  localStorage.setItem(SESSION_STORAGE_KEY, sessionId);
};

const clearSessionId = () => {
  localStorage.removeItem(SESSION_STORAGE_KEY);
};

const getApproach = () => {
  return localStorage.getItem(APPROACH_STORAGE_KEY) || 'rag';
};


/**
 * Start a new session and send first message
 * Uses ADK deployment pattern: 
 * 1. POST /apps/{app_name}/users/user/sessions to create session
 * 2. POST /run to send the actual message
 * Matches integration test pattern
 */
export const startSession = async (message, userEmail = null) => {
  try {
    const agentUrl = getAgentUrl();
    const appName = getAppName();
    const approach = getApproach();

    console.log(`[API] Using approach: ${approach}`);
    console.log(`[API] Agent URL: ${agentUrl}`);
    console.log(`[API] App name: ${appName}`);

    console.log('[API] Creating new session...');

    // Step 1: Create session with simple message - use plain string to avoid contamination
    const sessionResponse = await axios.post(
      `${agentUrl}/apps/${appName}/users/user/sessions`,
      '{"user_input":"Hello"}',
      {
        timeout: 300000,
        headers: { 'Content-Type': 'application/json' },
        transformRequest: [(data) => data]
      }
    );


    console.log('[API] Session created:', sessionResponse.data);

    // Extract session ID from response
    const sessionId = sessionResponse.data.id;
    setSessionId(sessionId);

    console.log('[API] Session ID:', sessionId);
    console.log('[API] Now sending actual message via /run...');

    // Step 2: Send the actual message using /run endpoint
    return await sendMessage(sessionId, message, userEmail);
  } catch (error) {
    console.error('[API] Error starting session:', error);
    throw error;
  }
};

/**
 * Send a message to an existing session
 * Uses ADK deployment pattern: POST /run
 * Matches integration test pattern
 */
export const sendMessage = async (sessionId, message, userEmail = null, history = []) => {
  try {
    console.log('[API] Sending message to session:', sessionId);

    // Update stored session ID
    setSessionId(sessionId);

    const agentUrl = getAgentUrl();
    const appName = getAppName();
    const approach = getApproach();

    console.log(`[API] Using approach: ${approach}`);
    console.log(`[API] Agent URL: ${agentUrl}`);

    // Construct the full message with explicit context
    let fullMessage = message;

    // Add user email context
    if (userEmail) {
      fullMessage = `[USER_EMAIL: ${userEmail}]\n\n${fullMessage}`;
    }

    // Add conversation history context if provided
    if (history && history.length > 0) {
      const historyText = history.map(msg => `${msg.role === 'user' ? 'User' : 'Assistant'}: ${msg.content}`).join('\n\n');
      fullMessage = `CONVERSATION HISTORY:\n${historyText}\n\nCURRENT REQUEST:\n${fullMessage}`;
    }


    // Helper function to safely escape a string for JSON
    // Note: Only escape common characters. \b and \f are regex special chars that would corrupt text.
    const escapeForJson = (str) => {
      return str
        .replace(/\\/g, '\\\\')
        .replace(/"/g, '\\"')
        .replace(/\n/g, '\\n')
        .replace(/\r/g, '\\r')
        .replace(/\t/g, '\\t');
    };


    // Build the request manually with proper escaping
    const escapedAppName = escapeForJson(String(appName || ''));
    const escapedSessionId = escapeForJson(String(sessionId || ''));
    const escapedMessage = escapeForJson(String(fullMessage || ''));

    const requestBody = `{"app_name":"${escapedAppName}","user_id":"user","session_id":"${escapedSessionId}","new_message":{"parts":[{"text":"${escapedMessage}"}]}}`;

    console.log('[API] Session ID being used:', sessionId);
    console.log('[API] Sending sanitized request to:', `${agentUrl}/run`);
    console.log('[API] Message length:', fullMessage.length);
    console.log('[API] Request body first 200 chars:', requestBody.substring(0, 200));

    const response = await axios.post(
      `${agentUrl}/run`,
      requestBody,
      {
        timeout: 300000,
        headers: { 'Content-Type': 'application/json' },
        transformRequest: [(data) => data]
      }
    );



    console.log('[API] Response received:', response.data);

    // The /run endpoint returns an array of events directly, not wrapped in {events: [...]}
    const events = Array.isArray(response.data) ? response.data : (response.data.events || []);

    return {
      id: sessionId,
      events: events,
      approach: approach
    };
  } catch (error) {
    console.error('Error sending message:', error);
    // If session not found, clear it
    if (error.response?.status === 404) {
      console.log('[API] Session not found, clearing stored session...');
      clearSessionId();
    }
    throw error;
  }
};

/**
 * Get session history
 */
export const getSession = async (sessionId) => {
  try {
    const response = await api.get(`/apps/agents/users/user/sessions/${sessionId}`);
    return response.data;
  } catch (error) {
    console.error('Error getting session:', error);
    throw error;
  }
};

/**
 * Upload student profile document to the user-specific student_profile store
 * Uses the profile manager cloud function
 */
export const uploadStudentProfile = async (file, userEmail) => {
  try {
    if (!userEmail) {
      throw new Error('User email is required for profile upload');
    }

    const formData = new FormData();
    formData.append('file', file);
    formData.append('user_email', userEmail);  // Use user_email as backend expects

    // Call the profile manager cloud function with dynamic URL
    const baseUrl = getProfileManagerUrl();
    const response = await axios.post(`${baseUrl}/upload-profile`, formData, {
      timeout: 180000,
      headers: {
        'Content-Type': 'multipart/form-data',
        'X-User-Email': userEmail
      },
    });
    return response.data;
  } catch (error) {
    console.error('Error uploading profile:', error);
    throw error;
  }
};

/**
 * List documents in user-specific student_profile store
 * Uses the profile manager cloud function
 */
export const listStudentProfiles = async (userEmail) => {
  try {
    if (!userEmail) {
      throw new Error('User email is required to list profiles');
    }

    const baseUrl = getProfileManagerUrl();
    const response = await axios.get(`${baseUrl}/list-profiles`, {
      timeout: 180000,
      params: { user_email: userEmail },  // Use user_email and /list-profiles endpoint
      headers: { 'X-User-Email': userEmail }
    });
    return response.data;
  } catch (error) {
    console.error('Error listing profiles:', error);
    throw error;
  }
};

/**
 * Delete a student profile document
 * Uses the profile manager cloud function
 */
export const deleteStudentProfile = async (documentId, userEmail, filename) => {
  try {
    const baseUrl = getProfileManagerUrl();
    const response = await axios.delete(`${baseUrl}/delete-profile`, {
      timeout: 180000,
      data: {
        document_name: documentId,
        user_email: userEmail,
        filename: filename
      },
      headers: { 'X-User-Email': userEmail }
    });
    return response.data;
  } catch (error) {
    console.error('Error deleting profile:', error);
    throw error;
  }
};

/**
 * Reset all profile data - clears profile, fit analyses, and optionally college list
 * Use for complete profile reset / fresh start
 */
export const resetAllProfile = async (userEmail, deleteCollegeList = false) => {
  try {
    const baseUrl = getProfileManagerUrl();
    const response = await axios.post(`${baseUrl}/reset-all-profile`, {
      user_email: userEmail,
      delete_college_list: deleteCollegeList
    }, {
      timeout: 180000,
      headers: { 'X-User-Email': userEmail }
    });
    return response.data;
  } catch (error) {
    console.error('Error resetting profile:', error);
    throw error;
  }
};

/**
 * Get student profile document content for preview
 * Uses the profile manager cloud function
 */
export const getStudentProfileContent = async (userEmail, filename) => {
  try {
    const baseUrl = getProfileManagerUrl();
    const response = await axios.post(`${baseUrl}/get-profile-content`, {
      user_email: userEmail,
      filename: filename
    }, {
      timeout: 180000,
      headers: { 'X-User-Email': userEmail }
    });
    return response.data;
  } catch (error) {
    console.error('Error getting profile content:', error);
    throw error;
  }
};

/**
 * Fetch the complete user profile directly from Profile Manager ES
 * Returns both raw content and structured data (JSON) for display
 * @param {string} userEmail - User's email address
 * @returns {object} Profile data with content and structuredData fields
 */
export const fetchUserProfile = async (userEmail) => {
  try {
    const baseUrl = getProfileManagerUrl();
    console.log(`[API] Fetching profile for ${userEmail} from ${baseUrl}`);

    const response = await axios.post(`${baseUrl}/search`, {
      user_email: userEmail,
      query: 'student profile',
      size: 1
    }, {
      timeout: 60000,
      headers: {
        'Content-Type': 'application/json',
        'X-User-Email': userEmail
      }
    });

    if (response.data?.success && response.data?.documents?.length > 0) {
      const doc = response.data.documents[0];
      // Content is nested inside doc.document
      const innerDoc = doc.document || doc;
      const content = innerDoc.content || doc.content || '';
      const metadata = innerDoc.metadata || doc.metadata || {};

      console.log(`[API] Profile found, content length: ${content.length}`);

      return {
        success: true,
        content: content,  // Clean markdown (for both search and display)
        metadata: metadata,
        filename: metadata?.filename || doc.display_name || 'profile'
      };
    }

    return {
      success: false,
      error: 'No profile found',
      content: ''
    };
  } catch (error) {
    console.error('Error fetching user profile:', error);
    throw error;
  }
};

/**
 * Fetch structured profile data (JSON) for visual display
 * Uses the /get-profile endpoint which returns parsed JSON structure
 * @param {string} userEmail - User's email address
 * @returns {object} Structured profile data with fields like personal_info, academics, etc.
 */
export const fetchStructuredProfile = async (userEmail) => {
  try {
    const baseUrl = getProfileManagerUrl();
    console.log(`[API] Fetching structured profile for ${userEmail}`);

    const response = await axios.get(`${baseUrl}/get-profile`, {
      params: { user_email: userEmail },
      timeout: 60000,
      headers: {
        'Content-Type': 'application/json',
        'X-User-Email': userEmail
      }
    });

    if (response.data?.success && response.data?.profile) {
      console.log(`[API] Structured profile found`);
      return {
        success: true,
        profile: response.data.profile
      };
    }

    return {
      success: false,
      error: 'No profile found',
      profile: null
    };
  } catch (error) {
    console.error('Error fetching structured profile:', error);
    // Don't throw - return error state for graceful handling
    return {
      success: false,
      error: error.message,
      profile: null
    };
  }
};

/**
 * Update a specific field in the structured profile
 * Uses the /update-structured-field endpoint for safe field-level updates
 * @param {string} userEmail - User's email address
 * @param {string} fieldPath - The field to update (e.g., 'gpa_weighted', 'courses')
 * @param {any} value - The new value
 * @param {string} operation - 'set', 'append', or 'remove' (default: 'set')
 * @returns {object} Result with success status
 */
export const updateProfileField = async (userEmail, fieldPath, value, operation = 'set') => {
  try {
    const url = `${PROFILE_MANAGER_ES_URL}/update-structured-field`;
    console.log(`[API] Updating profile field: ${fieldPath} with operation: ${operation}`);

    const response = await axios.post(url, {
      user_email: userEmail,
      field_path: fieldPath,
      value: value,
      operation: operation
    });

    if (response.data.success) {
      console.log(`[API] Successfully updated ${fieldPath}`);
      return {
        success: true,
        message: response.data.message || 'Field updated successfully'
      };
    } else {
      console.error(`[API] Failed to update ${fieldPath}:`, response.data.error);
      return {
        success: false,
        error: response.data.error || 'Update failed'
      };
    }
  } catch (error) {
    console.error(`[API] Error updating profile field ${fieldPath}:`, error);
    return {
      success: false,
      error: error.message
    };
  }
};

/**
 * Save onboarding profile data
 * Saves the collected onboarding data directly to the structured profile
 * @param {string} userEmail - User's email address
 * @param {object} onboardingData - Onboarding form data
 * @returns {object} Result with success status
 */
export const saveOnboardingProfile = async (userEmail, onboardingData) => {
  try {
    const baseUrl = getProfileManagerUrl();
    console.log(`[API] Saving onboarding profile for ${userEmail}`);

    // Save onboarding data as initial profile
    const response = await axios.post(`${baseUrl}/save-onboarding-profile`, {
      user_email: userEmail,
      profile_data: onboardingData
    }, {
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
        'X-User-Email': userEmail
      }
    });

    console.log(`[API] Onboarding profile saved:`, response.data);
    return response.data;
  } catch (error) {
    console.error('[API] Error saving onboarding profile:', error);
    return {
      success: false,
      error: error.message
    };
  }
};

/**
 * Check onboarding status for a user
 * Returns whether user has completed or skipped onboarding
 * @param {string} userEmail - User's email address
 * @returns {object} { hasProfile: boolean, onboardingStatus: string }
 */
export const checkOnboardingStatus = async (userEmail) => {
  try {
    const baseUrl = getProfileManagerUrl();
    console.log(`[API] Checking onboarding status for ${userEmail}`);

    // Fetch the structured profile to check onboarding_status
    const response = await axios.get(`${baseUrl}/get-profile`, {
      params: { user_email: userEmail },
      timeout: 15000,
      headers: {
        'Content-Type': 'application/json',
        'X-User-Email': userEmail
      }
    });

    if (response.data?.success && response.data?.profile) {
      const profile = response.data.profile;
      const onboardingStatus = profile.onboarding_status || null;

      return {
        hasProfile: true,
        onboardingStatus: onboardingStatus,
        needsOnboarding: !onboardingStatus || onboardingStatus === 'in_progress'
      };
    }

    // No profile found - definitely needs onboarding
    return {
      hasProfile: false,
      onboardingStatus: null,
      needsOnboarding: true
    };
  } catch (error) {
    console.error('[API] Error checking onboarding status:', error);
    // On error, assume needs onboarding (safer default)
    return {
      hasProfile: false,
      onboardingStatus: null,
      needsOnboarding: true
    };
  }
};


/**
 * Extract text content and suggested questions from the agent's response
 * Returns an object with { text, suggested_questions }
 */
export const extractResponseText = (sessionData) => {
  if (!sessionData || !sessionData.events) {
    return '';
  }

  // Get the last event
  const lastEvent = sessionData.events[sessionData.events.length - 1];

  if (!lastEvent || !lastEvent.content || !lastEvent.content.parts) {
    return '';
  }

  // Extract text from all parts
  const rawText = lastEvent.content.parts
    .filter(part => part.text)
    .map(part => part.text)
    .join('\n\n');

  // Try to parse as JSON (OrchestratorOutput format)
  try {
    const parsed = JSON.parse(rawText);
    if (parsed.result !== undefined) {
      // Return the result text (for backward compatibility)
      return parsed.result;
    }
  } catch (e) {
    // Not JSON, return as-is
  }

  return rawText;
};

/**
 * Extract the full response object including suggested questions
 * Returns { result: string, suggested_questions: string[] }
 */
export const extractFullResponse = (sessionData) => {
  if (!sessionData || !sessionData.events) {
    return { result: '', suggested_questions: [] };
  }

  // Get the last event
  const lastEvent = sessionData.events[sessionData.events.length - 1];

  if (!lastEvent || !lastEvent.content || !lastEvent.content.parts) {
    return { result: '', suggested_questions: [] };
  }

  // Extract text from all parts
  const rawText = lastEvent.content.parts
    .filter(part => part.text)
    .map(part => part.text)
    .join('\n\n');

  // Try to parse as JSON (OrchestratorOutput format)
  try {
    const parsed = JSON.parse(rawText);
    if (parsed.result !== undefined) {
      return {
        result: parsed.result,
        suggested_questions: parsed.suggested_questions || []
      };
    }
  } catch (e) {
    // Not JSON, return raw text with no suggestions
  }

  return { result: rawText, suggested_questions: [] };
};

// ============================================
// Knowledge Base Management API
// ============================================

// Determine knowledge base URL based on approach
const getKnowledgeBaseUrl = () => {
  const approach = localStorage.getItem('knowledgeBaseApproach') || KNOWLEDGE_BASE_APPROACH;
  if (approach === 'hybrid') {
    // Hybrid uses the universities knowledge base
    return import.meta.env.VITE_KNOWLEDGE_BASE_UNIVERSITIES_URL || 'https://knowledge-base-manager-universities-pfnwjfp26a-ue.a.run.app';
  }
  if (approach === 'elasticsearch') {
    return import.meta.env.VITE_KNOWLEDGE_BASE_ES_URL || 'https://knowledge-base-manager-es-pfnwjfp26a-ue.a.run.app';
  }
  if (approach === 'vertexai') {
    return import.meta.env.VITE_KNOWLEDGE_BASE_VERTEXAI_URL || 'https://knowledge-base-manager-vertexai-pfnwjfp26a-ue.a.run.app';
  }
  return import.meta.env.VITE_KNOWLEDGE_BASE_URL || 'https://knowledge-base-manager-pfnwjfp26a-ue.a.run.app';
};

// Note: knowledgeBaseApi removed - we use dynamic URLs in each function call

console.log(`[FRONTEND] Knowledge base URL: ${getKnowledgeBaseUrl()}`);

/**
 * Upload university research document to the college_admissions_kb store
 * Uses the knowledge base manager cloud function
 * Works with all approaches (RAG, Firestore, Elasticsearch) using the same endpoint
 */
export const uploadKnowledgeBaseDocument = async (file, userId) => {
  try {
    const formData = new FormData();
    formData.append('file', file);
    if (userId) {
      formData.append('user_id', userId);
    }

    const baseUrl = getKnowledgeBaseUrl();
    const response = await axios.post(`${baseUrl}/upload-document`, formData, {
      timeout: 180000,
      headers: {
        'Content-Type': 'multipart/form-data',
        ...(userId && { 'X-User-Email': userId })
      },
    });
    return response.data;
  } catch (error) {
    console.error('Error uploading knowledge base document:', error);
    console.error('Error details:', {
      message: error.message,
      status: error.response?.status,
      statusText: error.response?.statusText,
      data: error.response?.data,
      url: getKnowledgeBaseUrl() + '/upload-document'
    });
    throw error;
  }
};

/**
 * List all documents in the knowledge base
 * Uses the knowledge base manager cloud function
 * Works with all approaches (RAG, Firestore, Elasticsearch) using the same endpoint
 * Note: Hybrid approach uses universities KB with different response format
 */
export const listKnowledgeBaseDocuments = async (userId) => {
  try {
    const approach = localStorage.getItem('knowledgeBaseApproach') || KNOWLEDGE_BASE_APPROACH;
    const baseUrl = getKnowledgeBaseUrl();

    // Hybrid approach uses universities knowledge base with different endpoint
    if (approach === 'hybrid') {
      // Universities KB uses root endpoint and returns 'universities' array
      const response = await axios.get(baseUrl, {
        timeout: 60000
      });

      // Transform universities response to document format for UI compatibility
      if (response.data.success && response.data.universities) {
        const documents = response.data.universities.map(uni => ({
          name: uni.university_id,
          display_name: uni.official_name,
          mime_type: 'university/profile',
          size_bytes: 0,
          size: 0,
          create_time: uni.indexed_at,
          state: 'ACTIVE',
          location: uni.location,
          acceptance_rate: uni.acceptance_rate,
          market_position: uni.market_position
        }));

        return {
          success: true,
          documents: documents,
          total: response.data.total
        };
      }
      return response.data;
    }

    // Other approaches use /documents endpoint
    const response = await axios.get(`${baseUrl}/documents`, {
      timeout: 180000,
      params: userId ? { user_id: userId } : {},
      headers: userId ? { 'X-User-Email': userId } : {}
    });
    return response.data;
  } catch (error) {
    console.error('Error listing knowledge base documents:', error);
    throw error;
  }
};

/**
 * Delete a document from the knowledge base
 * Uses the knowledge base manager cloud function
 * Works with all approaches (RAG, Firestore, Elasticsearch) using the same endpoint
 * Note: Hybrid approach uses universities KB with DELETE method
 */
export const deleteKnowledgeBaseDocument = async (documentName, filename, userId) => {
  try {
    const approach = localStorage.getItem('knowledgeBaseApproach') || KNOWLEDGE_BASE_APPROACH;
    const baseUrl = getKnowledgeBaseUrl();

    // Hybrid approach uses DELETE method with university_id
    if (approach === 'hybrid') {
      const response = await axios.delete(baseUrl, {
        timeout: 180000,
        data: { university_id: documentName }
      });
      return response.data;
    }

    // Other approaches use POST to /delete endpoint
    const response = await axios.post(`${baseUrl}/delete`, {
      file_name: documentName,
      ...(userId && { user_id: userId })
    }, {
      timeout: 180000,
      headers: userId ? { 'X-User-Email': userId } : {}
    });
    return response.data;
  } catch (error) {
    console.error('Error deleting document:', error);
    throw error;
  }
};

/**
 * Get knowledge base document content for preview
 * Uses the knowledge base manager cloud function
 */
export const getKnowledgeBaseDocumentContent = async (fileName) => {
  try {
    const baseUrl = getKnowledgeBaseUrl();
    const response = await axios.post(`${baseUrl}/get-document-content`, {
      file_name: fileName
    }, {
      timeout: 60000
    });
    return response.data;
  } catch (error) {
    console.error('Error getting document content:', error);
    throw error;
  }
};

/**
 * Upload document to Vertex AI (via cloud function)
 * Uploads to GCS then indexes in Vertex AI RAG
 */
export const uploadVertexAIDocument = async (file, userId) => {
  try {
    const formData = new FormData();
    formData.append('file', file);
    if (userId) {
      formData.append('user_id', userId);
    }

    const baseUrl = VERTEXAI_KNOWLEDGE_BASE_URL;
    const response = await axios.post(`${baseUrl}/upload-document`, formData, {
      timeout: 120000,
      headers: {
        'Content-Type': 'multipart/form-data',
        ...(userId && { 'X-User-Email': userId })
      },
    });
    return response.data;
  } catch (error) {
    console.error('Error uploading Vertex AI document:', error);
    throw error;
  }
};

/**
 * Upload profile to Vertex AI (via cloud function)
 * Uploads to user-specific GCS folder then indexes in Vertex AI RAG
 */
export const uploadVertexAIProfile = async (file, userId) => {
  try {
    const formData = new FormData();
    formData.append('file', file);
    if (userId) {
      formData.append('user_id', userId);
    }

    const baseUrl = VERTEXAI_PROFILE_MANAGER_URL;
    const response = await axios.post(`${baseUrl}/upload-profile`, formData, {
      timeout: 120000,
      headers: {
        'Content-Type': 'multipart/form-data',
        ...(userId && { 'X-User-Email': userId })
      },
    });
    return response.data;
  } catch (error) {
    console.error('Error uploading Vertex AI profile:', error);
    throw error;
  }
};

/**
 * List documents from Vertex AI (via cloud function)
 * Lists from GCS
 */
export const listVertexAIDocuments = async (userId) => {
  try {
    const baseUrl = VERTEXAI_KNOWLEDGE_BASE_URL;
    const response = await axios.get(`${baseUrl}/documents`, {
      timeout: 180000,
      params: userId ? { user_id: userId } : {},
      headers: userId ? { 'X-User-Email': userId } : {}
    });
    return response.data;
  } catch (error) {
    console.error('Error listing Vertex AI documents:', error);
    throw error;
  }
};

/**
 * List profiles from Vertex AI (via cloud function)
 * Lists from user-specific GCS folder
 */
export const listVertexAIProfiles = async (userId) => {
  try {
    const baseUrl = VERTEXAI_PROFILE_MANAGER_URL;
    const response = await axios.get(`${baseUrl}/profiles`, {
      timeout: 180000,
      params: { user_email: userId },
      headers: { 'X-User-Email': userId }
    });
    return response.data;
  } catch (error) {
    console.error('Error listing Vertex AI profiles:', error);
    throw error;
  }
};

/**
 * Delete document from Vertex AI (via cloud function)
 * Deletes from both GCS and Vertex AI RAG
 */
export const deleteVertexAIDocument = async (documentName, displayName, userId) => {
  try {
    const baseUrl = VERTEXAI_KNOWLEDGE_BASE_URL;
    const response = await axios.post(`${baseUrl}/delete`, {
      file_name: documentName
    }, {
      timeout: 180000,
      headers: userId ? { 'X-User-Email': userId } : {}
    });
    return response.data;
  } catch (error) {
    console.error('Error deleting Vertex AI document:', error);
    throw error;
  }
};

/**
 * Delete profile from Vertex AI (via cloud function)
 * Deletes from both GCS and Vertex AI RAG
 */
export const deleteVertexAIProfile = async (documentId, userId, displayName) => {
  try {
    const baseUrl = VERTEXAI_PROFILE_MANAGER_URL;
    const response = await axios.post(`${baseUrl}/delete`, {
      file_name: documentId
    }, {
      timeout: 180000,
      headers: { 'X-User-Email': userId }
    });
    return response.data;
  } catch (error) {
    console.error('Error deleting Vertex AI profile:', error);
    throw error;
  }
};

// ============================================
// College List Management API
// ============================================

/**
 * Get user's college list
 * @param {string} userEmail - User's email
 * @returns {Promise<{success: boolean, college_list: Array, count: number}>}
 */
export const getCollegeList = async (userEmail) => {
  try {
    const baseUrl = getProfileManagerUrl();
    const response = await axios.get(`${baseUrl}/get-college-list`, {
      params: { user_email: userEmail },
      timeout: 180000,
      headers: { 'X-User-Email': userEmail }
    });
    return response.data;
  } catch (error) {
    console.error('Error getting college list:', error);
    throw error;
  }
};

/**
 * Add or remove a college from user's list
 * @param {string} userEmail - User's email
 * @param {string} action - 'add' or 'remove'
 * @param {{id: string, name: string}} university - University object
 * @param {string} intendedMajor - Student's intended major (optional)
 * @returns {Promise<{success: boolean, college_list: Array}>}
 */
export const updateCollegeList = async (userEmail, action, university, intendedMajor = '') => {
  try {
    const baseUrl = getProfileManagerUrl();
    const response = await axios.post(`${baseUrl}/update-college-list`, {
      user_email: userEmail,
      action: action,
      university: university,
      intended_major: intendedMajor
    }, {
      timeout: 180000,
      headers: { 'X-User-Email': userEmail }
    });
    return response.data;
  } catch (error) {
    console.error('Error updating college list:', error);
    throw error;
  }
};

/**
 * Update fit analysis for a college in user's list
 * @param {string} userEmail - User's email
 * @param {string} universityId - University ID
 * @param {Object} fitAnalysis - Fit analysis data
 * @returns {Promise<{success: boolean}>}
 */
export const updateFitAnalysis = async (userEmail, universityId, fitAnalysis) => {
  try {
    const baseUrl = getProfileManagerUrl();
    const response = await axios.post(`${baseUrl}/update-fit-analysis`, {
      user_email: userEmail,
      university_id: universityId,
      fit_analysis: fitAnalysis
    }, {
      timeout: 180000,
      headers: { 'X-User-Email': userEmail }
    });
    return response.data;
  } catch (error) {
    console.error('Error updating fit analysis:', error);
    throw error;
  }
};

// ============================================
// Pre-computed Fit Matrix API
// ============================================

/**
 * Compute fit analysis for ALL universities and store in profile
 * This should be called after profile upload (runs in background)
 * @param {string} userEmail - User's email
 * @returns {Promise<{success: boolean, computed: number, fits_computed_at: string}>}
 */
export const computeAllFits = async (userEmail) => {
  try {
    console.log(`[API] Computing all fits for ${userEmail}...`);
    const baseUrl = getProfileManagerUrl();
    const response = await axios.post(`${baseUrl}/compute-all-fits`, {
      user_email: userEmail
    }, {
      timeout: 300000,  // 5 min timeout - this takes a while (100 universities)
      headers: { 'X-User-Email': userEmail }
    });
    console.log(`[API] Computed fits:`, response.data);
    return response.data;
  } catch (error) {
    console.error('Error computing all fits:', error);
    // Don't throw - this is a background operation
    return { success: false, error: error.message };
  }
};

/**
 * Compute fit analysis for a SINGLE university (lazy fit computation with caching)
 * Called when a university is added to the Launchpad
 * @param {string} userEmail - User's email
 * @param {string} universityId - University ID to compute fit for
 * @param {boolean} forceRecompute - If true, bypass cache and force LLM recomputation
 * @returns {Promise<{success: boolean, fit_analysis: object, from_cache: boolean}>}
 */
export const computeSingleFit = async (userEmail, universityId, forceRecompute = false) => {
  try {
    console.log(`[API] Computing single fit for ${userEmail} - ${universityId} (force=${forceRecompute})...`);
    const baseUrl = getProfileManagerUrl();
    const response = await axios.post(`${baseUrl}/compute-single-fit`, {
      user_email: userEmail,
      university_id: universityId,
      force_recompute: forceRecompute
    }, {
      timeout: 60000,  // 1 min timeout for single university
      headers: { 'X-User-Email': userEmail }
    });
    console.log(`[API] Computed single fit (from_cache=${response.data.from_cache}):`, response.data);
    return response.data;
  } catch (error) {
    // Check for 402 Payment Required (insufficient credits)
    if (error.response?.status === 402) {
      console.warn('[API] Insufficient credits for fit analysis');
      return {
        success: false,
        error: 'insufficient_credits',
        insufficientCredits: true,
        creditsRemaining: error.response?.data?.credits_remaining ?? 0,
        message: error.response?.data?.message || 'You need more credits to run fit analysis'
      };
    }
    console.error('Error computing single fit:', error);
    return { success: false, error: error.message };
  }
};

/**
 * Generate fit infographic image using Gemini AI
 * Creates a personalized visual infographic for the student's fit analysis
 * @param {string} userEmail - User's email
 * @param {string} universityId - University ID to generate infographic for
 * @param {boolean} forceRegenerate - If true, bypass cache and regenerate image
 * @returns {Promise<{success: boolean, infographic_url: string, from_cache: boolean}>}
 */
export const generateFitInfographic = async (userEmail, universityId, forceRegenerate = false) => {
  try {
    console.log(`[API] Generating fit infographic for ${userEmail} - ${universityId} (force=${forceRegenerate})...`);
    const baseUrl = getProfileManagerUrl();
    const response = await axios.post(`${baseUrl}/generate-fit-image`, {
      user_email: userEmail,
      university_id: universityId,
      force_regenerate: forceRegenerate
    }, {
      timeout: 120000,  // 2 min timeout for image generation
      headers: { 'X-User-Email': userEmail }
    });
    console.log(`[API] Generated infographic (from_cache=${response.data.from_cache}):`, response.data);
    return response.data;
  } catch (error) {
    console.error('Error generating fit infographic:', error);
    return { success: false, error: error.message };
  }
};


/**
 * Get structured infographic data for frontend rendering
 * Returns JSON that can be rendered as a beautiful native component (no image generation)
 * @param {string} userEmail - User's email
 * @param {string} universityId - University ID to get infographic data for
 * @returns {Promise<{success: boolean, infographic_data: Object}>}
 */
export const getFitInfographicData = async (userEmail, universityId) => {
  try {
    console.log(`[API] Getting fit infographic data for ${userEmail} - ${universityId}...`);
    const baseUrl = getProfileManagerUrl();
    const response = await axios.get(`${baseUrl}/generate-fit-infographic-data`, {
      params: {
        user_email: userEmail,
        university_id: universityId
      },
      timeout: 30000,
      headers: { 'X-User-Email': userEmail }
    });
    console.log(`[API] Got infographic data:`, response.data);
    return response.data;
  } catch (error) {
    console.error('Error getting fit infographic data:', error);
    return { success: false, error: error.message };
  }
};


/**
 * Get pre-computed fits with optional filtering
 * @param {string} userEmail - User's email
 * @param {Object} filters - Optional filters: { category, state, exclude_ids }
 * @param {number} limit - Max results to return
 * @param {string} sortBy - Sort order: "rank" or "match_score"
 * @returns {Promise<{success: boolean, results: Array, total: number, fits_ready: boolean}>}
 */
export const getPrecomputedFits = async (userEmail, filters = {}, limit = 20, sortBy = 'rank') => {
  try {
    const baseUrl = getProfileManagerUrl();
    const response = await axios.post(`${baseUrl}/get-fits`, {
      user_email: userEmail,
      filters: filters,
      limit: limit,
      sort_by: sortBy
    }, {
      timeout: 30000,
      headers: { 'X-User-Email': userEmail }
    });
    return response.data;
  } catch (error) {
    console.error('Error getting pre-computed fits:', error);
    throw error;
  }
};

/**
 * Recompute fits for all universities in user's Launchpad
 * Called when profile is updated to refresh fit analyses
 * @param {string} userEmail - User's email
 * @returns {Promise<{success: boolean, recomputed: number}>}
 */
export const recomputeLaunchpadFits = async (userEmail) => {
  try {
    console.log(`[API] Recomputing Launchpad fits for ${userEmail}...`);

    // First, get the user's college list
    const listResult = await getCollegeList(userEmail);
    if (!listResult.success || !listResult.colleges || listResult.colleges.length === 0) {
      console.log('[API] No universities in Launchpad, skipping recomputation');
      return { success: true, recomputed: 0 };
    }

    // Recompute fits for each university in the Launchpad (in parallel, limited)
    const universities = listResult.colleges;
    console.log(`[API] Recomputing fits for ${universities.length} Launchpad universities`);

    let recomputed = 0;
    // Process in batches of 3 to avoid overwhelming the backend
    // forceRecompute=true because profile changed and we need fresh analysis
    for (let i = 0; i < universities.length; i += 3) {
      const batch = universities.slice(i, i + 3);
      const promises = batch.map(uni =>
        computeSingleFit(userEmail, uni.university_id, true).catch(err => {  // force=true for profile update
          console.warn(`[API] Failed to recompute fit for ${uni.university_id}:`, err);
          return { success: false };
        })
      );
      const results = await Promise.all(promises);
      recomputed += results.filter(r => r.success).length;
    }

    console.log(`[API] Recomputed ${recomputed}/${universities.length} Launchpad fits`);
    return { success: true, recomputed };
  } catch (error) {
    console.error('Error recomputing Launchpad fits:', error);
    return { success: false, error: error.message };
  }
};

/**
 * Check if fits are ready for a user
 * @param {string} userEmail - User's email
 * @returns {Promise<{ready: boolean, fits_computed_at: string|null}>}
 */
export const checkFitsReady = async (userEmail) => {
  try {
    const result = await getPrecomputedFits(userEmail, {}, 1);
    return {
      ready: result.fits_ready === true,
      computed_at: result.fits_computed_at || null,
      total: result.total || 0
    };
  } catch (error) {
    return { ready: false, computed_at: null, total: 0 };
  }
};

/**
 * Get fits filtered by category (for Smart Discovery quick actions)
 * @param {string} userEmail - User's email
 * @param {string} category - Fit category: SAFETY, TARGET, REACH, SUPER_REACH (or null for all)
 * @param {string} state - State filter (e.g., "CA") or null
 * @param {Array<string>} excludeIds - University IDs to exclude
 * @param {number} limit - Max results
 * @returns {Promise<{success: boolean, results: Array, total: number}>}
 */
export const getFitsByCategory = async (userEmail, category = null, state = null, excludeIds = [], limit = 10) => {
  const filters = {};
  if (category) filters.category = category;
  if (state) filters.state = state;
  if (excludeIds && excludeIds.length > 0) filters.exclude_ids = excludeIds;

  return getPrecomputedFits(userEmail, filters, limit, 'rank');
};

/**
 * Get a balanced college list with safety, target, and reach schools
 * Fetches multiple categories in parallel for optimal performance
 * @param {string} userEmail - User's email
 * @param {Array<string>} excludeIds - University IDs to exclude
 * @returns {Promise<{success: boolean, results: Array, total: number, breakdown: Object}>}
 */
export const getBalancedList = async (userEmail, excludeIds = []) => {
  try {
    // Fetch fits for each category in parallel
    const [safetyResult, targetResult, reachResult] = await Promise.all([
      getFitsByCategory(userEmail, 'SAFETY', null, excludeIds, 3),
      getFitsByCategory(userEmail, 'TARGET', null, excludeIds, 4),
      getFitsByCategory(userEmail, 'REACH', null, excludeIds, 3)
    ]);

    // Merge results
    const balanced = [
      ...(safetyResult.results || []),
      ...(targetResult.results || []),
      ...(reachResult.results || [])
    ];

    return {
      success: true,
      results: balanced,
      total: balanced.length,
      breakdown: {
        safety: safetyResult.results?.length || 0,
        target: targetResult.results?.length || 0,
        reach: reachResult.results?.length || 0
      }
    };
  } catch (error) {
    console.error('Error getting balanced list:', error);
    return {
      success: false,
      error: error.message,
      results: [],
      total: 0
    };
  }
};


/**
 * Check if fit recomputation is needed (based on profile changes)
 * @param {string} userEmail - User's email
 * @returns {Promise<{needs_recomputation: boolean, reason: string|null, changes: array}>}
 */
export const checkFitRecomputationNeeded = async (userEmail) => {
  try {
    const baseUrl = getProfileManagerUrl();
    const response = await axios.post(`${baseUrl}/search`, {
      user_id: userEmail
    }, {
      headers: { 'X-User-Email': userEmail }
    });

    if (response.data.success && response.data.profiles?.length > 0) {
      const profile = response.data.profiles[0];
      return {
        needs_recomputation: profile.needs_fit_recomputation === true,
        reason: profile.last_change_reason || null,
        changes: profile.last_change_details || [],
        profile_updated_at: profile.profile_updated_at || null,
        fits_computed_at: profile.fits_computed_at || null
      };
    }
    return { needs_recomputation: false, reason: null, changes: [] };
  } catch (error) {
    console.error('Error checking fit recomputation status:', error);
    return { needs_recomputation: false, reason: null, changes: [] };
  }
};


// ============== CREDITS API ==============

/**
 * Get user's credit balance and tier info
 * @param {string} userEmail - User's email
 * @returns {Promise<{success: boolean, credits: object}>}
 */
export const getUserCredits = async (userEmail) => {
  try {
    const baseUrl = getProfileManagerUrl();
    const response = await axios.get(`${baseUrl}/get-credits`, {
      params: { user_email: userEmail },
      headers: { 'X-User-Email': userEmail }
    });
    return response.data;
  } catch (error) {
    console.error('Error getting user credits:', error);
    return {
      success: false,
      error: error.message,
      credits: {
        tier: 'free',
        credits_remaining: 0,
        credits_total: 0
      }
    };
  }
};

/**
 * Check if user has enough credits for an operation
 * @param {string} userEmail - User's email
 * @param {number} creditsNeeded - Number of credits required
 * @returns {Promise<{has_credits: boolean, credits_remaining: number}>}
 */
export const checkCredits = async (userEmail, creditsNeeded = 1) => {
  try {
    const baseUrl = getProfileManagerUrl();
    const response = await axios.post(`${baseUrl}/check-credits`, {
      user_email: userEmail,
      credits_needed: creditsNeeded
    }, {
      headers: { 'X-User-Email': userEmail }
    });
    return response.data;
  } catch (error) {
    console.error('Error checking credits:', error);
    return {
      success: false,
      has_credits: false,
      credits_remaining: 0,
      error: error.message
    };
  }
};

/**
 * Upgrade user to Pro tier (called after Stripe payment success)
 * @param {string} userEmail - User's email
 * @param {string} subscriptionExpires - Expiration date ISO string
 * @returns {Promise<{success: boolean, tier: string, credits_remaining: number}>}
 */
export const upgradeToPro = async (userEmail, subscriptionExpires) => {
  try {
    const baseUrl = getProfileManagerUrl();
    const response = await axios.post(`${baseUrl}/upgrade-to-pro`, {
      user_email: userEmail,
      subscription_expires: subscriptionExpires
    }, {
      headers: { 'X-User-Email': userEmail }
    });
    return response.data;
  } catch (error) {
    console.error('Error upgrading to Pro:', error);
    return {
      success: false,
      error: error.message
    };
  }
};

/**
 * Add credits to user's balance (called after credit pack purchase)
 * @param {string} userEmail - User's email
 * @param {number} creditCount - Number of credits to add
 * @param {string} source - Source of credits (e.g., 'credit_pack')
 * @returns {Promise<{success: boolean, credits_added: number, credits_remaining: number}>}
 */
export const addUserCredits = async (userEmail, creditCount, source = 'credit_pack') => {
  try {
    const baseUrl = getProfileManagerUrl();
    const response = await axios.post(`${baseUrl}/add-credits`, {
      user_email: userEmail,
      credit_count: creditCount,
      source: source
    }, {
      headers: { 'X-User-Email': userEmail }
    });
    return response.data;
  } catch (error) {
    console.error('Error adding credits:', error);
    return {
      success: false,
      error: error.message
    };
  }
};

/**
 * Deduct credits from user's balance
 * @param {string} userEmail - User's email
 * @param {number} creditCount - Number of credits to deduct (default 1)
 * @param {string} reason - Reason for deduction (e.g., 'fit_analysis', 'infographic_regeneration')
 * @returns {Promise<{success: boolean, credits_remaining: number}>}
 */
export const deductCredit = async (userEmail, creditCount = 1, reason = 'infographic_regeneration') => {
  try {
    const baseUrl = getProfileManagerUrl();
    const response = await axios.post(`${baseUrl}/deduct-credit`, {
      user_email: userEmail,
      credit_count: creditCount,
      reason: reason
    }, {
      headers: { 'X-User-Email': userEmail }
    });
    return response.data;
  } catch (error) {
    console.error('Error deducting credits:', error);
    return {
      success: false,
      error: error.message,
      credits_remaining: 0
    };
  }
};

// ============== END CREDITS API ==============

export default api;

