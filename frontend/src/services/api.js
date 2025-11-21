import axios from 'axios';

// Get API base URLs from environment or use defaults
const RAG_AGENT_URL = import.meta.env.VITE_RAG_AGENT_URL || 'https://college-expert-rag-agent-pfnwjfp26a-ue.a.run.app';
const ES_AGENT_URL = import.meta.env.VITE_ES_AGENT_URL || 'https://college-expert-es-agent-pfnwjfp26a-ue.a.run.app';

// Get knowledge base approach from environment
const KNOWLEDGE_BASE_APPROACH = import.meta.env.VITE_KNOWLEDGE_BASE_APPROACH || 'rag';

// Get the appropriate agent URL based on approach
const getAgentUrl = () => {
  const approach = localStorage.getItem('knowledgeBaseApproach') || KNOWLEDGE_BASE_APPROACH;
  return approach === 'elasticsearch' ? ES_AGENT_URL : RAG_AGENT_URL;
};

// Get the app name based on approach
const getAppName = () => {
  const approach = localStorage.getItem('knowledgeBaseApproach') || KNOWLEDGE_BASE_APPROACH;
  return approach === 'elasticsearch' ? 'college_expert_es' : 'college_expert_rag';
};

// Determine profile manager URL based on approach
const getProfileManagerUrl = () => {
  const approach = localStorage.getItem('knowledgeBaseApproach') || KNOWLEDGE_BASE_APPROACH;
  if (approach === 'elasticsearch') {
    return import.meta.env.VITE_PROFILE_MANAGER_ES_URL || 'https://profile-manager-es-pfnwjfp26a-ue.a.run.app';
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
 * Create a new session
 */
const createSession = async () => {
  try {
    console.log('[API] Creating new session...');
    const response = await api.post('/apps/agents/users/user/sessions', {});
    const sessionId = response.data.id;
    setSessionId(sessionId);
    console.log('[API] Session created:', sessionId);
    return sessionId;
  } catch (error) {
    console.error('[API] Error creating session:', error);
    throw error;
  }
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

    // Step 1: Create session with simple message (like integration test)
    const sessionResponse = await axios.post(
      `${agentUrl}/apps/${appName}/users/user/sessions`,
      { user_input: "Hello" },
      { 
        timeout: 300000,
        headers: { 'Content-Type': 'application/json' }
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
export const sendMessage = async (sessionId, message, userEmail = null) => {
  try {
    console.log('[API] Sending message to session:', sessionId);
    
    // Update stored session ID
    setSessionId(sessionId);

    const agentUrl = getAgentUrl();
    const appName = getAppName();
    const approach = getApproach();
    
    console.log(`[API] Using approach: ${approach}`);
    console.log(`[API] Agent URL: ${agentUrl}`);

    // Prepend user email to message if provided
    let fullMessage = message;
    if (userEmail) {
      fullMessage = `[USER_EMAIL: ${userEmail}]\n\n${message}`;
    }

    // Send message using ADK /run endpoint - matches integration test
    const requestData = {
      app_name: appName,
      user_id: "user",
      session_id: sessionId,
      new_message: {
        parts: [{
          text: fullMessage
        }]
      }
    };
    
    const response = await axios.post(
      `${agentUrl}/run`,
      requestData,
      { 
        timeout: 300000,
        headers: { 'Content-Type': 'application/json' }
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
      timeout: 60000,
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
      timeout: 60000,
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
      timeout: 60000,
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
      timeout: 60000,
      headers: { 'X-User-Email': userEmail }
    });
    return response.data;
  } catch (error) {
    console.error('Error getting profile content:', error);
    throw error;
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
  if (approach === 'elasticsearch') {
    return import.meta.env.VITE_KNOWLEDGE_BASE_ES_URL || 'https://knowledge-base-manager-es-pfnwjfp26a-ue.a.run.app';
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
      timeout: 60000,
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
 */
export const listKnowledgeBaseDocuments = async (userId) => {
  try {
    const baseUrl = getKnowledgeBaseUrl();
    const response = await axios.get(`${baseUrl}/documents`, {
      timeout: 60000,
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
 */
export const deleteKnowledgeBaseDocument = async (documentName, filename, userId) => {
  try {
    const baseUrl = getKnowledgeBaseUrl();
    const response = await axios.post(`${baseUrl}/delete`, {
      file_name: documentName,
      ...(userId && { user_id: userId })
    }, {
      timeout: 60000,
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

export default api;
