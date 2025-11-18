import axios from 'axios';

// Get API base URLs from environment or use defaults
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8080';
const PROFILE_MANAGER_URL = import.meta.env.VITE_PROFILE_MANAGER_URL || 'http://localhost:8080';

// Create axios instance for agent API
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 300000, // 5 minutes for agent processing (complex analysis with multiple sub-agents)
  headers: {
    'Content-Type': 'application/json',
  },
});

// Create axios instance for profile manager cloud function
const profileApi = axios.create({
  baseURL: PROFILE_MANAGER_URL,
  timeout: 60000, // 1 minute for file operations
  headers: {
    'Content-Type': 'application/json',
  },
});

// Session management - use localStorage to persist across page changes
const SESSION_STORAGE_KEY = 'college_counselor_session_id';

const getSessionId = () => {
  return localStorage.getItem(SESSION_STORAGE_KEY);
};

const setSessionId = (sessionId) => {
  localStorage.setItem(SESSION_STORAGE_KEY, sessionId);
};

const clearSessionId = () => {
  localStorage.removeItem(SESSION_STORAGE_KEY);
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
 * Start a new session with the College Counselor agent
 * Uses the /run endpoint for immediate execution
 */
export const startSession = async (message, userEmail = null) => {
  try {
    // Get or create session
    let sessionId = getSessionId();
    if (!sessionId) {
      sessionId = await createSession();
    }

    console.log('[API] Sending message to session:', sessionId);

    // Prepend user email to message if provided
    let fullMessage = message;
    if (userEmail) {
      fullMessage = `[USER_EMAIL: ${userEmail}]\n\n${message}`;
    }

    // Send message using /run endpoint (enabled with --with_ui flag)
    const response = await api.post('/run', {
      app_name: 'agents',
      user_id: 'user',
      session_id: sessionId,
      new_message: {
        parts: [{ text: fullMessage }]
      },
      streaming: false
    });

    console.log('[API] Response received:', response.data);
    
    return {
      id: sessionId,
      events: response.data || []
    };
  } catch (error) {
    console.error('Error starting session:', error);
    // If session not found, clear it and retry once
    if (error.response?.status === 404) {
      console.log('[API] Session not found, creating new session...');
      clearSessionId();
      // Don't retry here, let the caller handle it
    }
    throw error;
  }
};

/**
 * Send a message to an existing session
 */
export const sendMessage = async (sessionId, message, userEmail = null) => {
  try {
    console.log('[API] Sending message to session:', sessionId);
    
    // Update stored session ID
    setSessionId(sessionId);

    // Prepend user email to message if provided
    let fullMessage = message;
    if (userEmail) {
      fullMessage = `[USER_EMAIL: ${userEmail}]\n\n${message}`;
    }

    // Send message using /run endpoint
    const response = await api.post('/run', {
      app_name: 'agents',
      user_id: 'user',
      session_id: sessionId,
      new_message: {
        parts: [{ text: fullMessage }]
      },
      streaming: false
    });

    console.log('[API] Response received:', response.data);
    
    return {
      id: sessionId,
      events: response.data || []
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
    formData.append('user_email', userEmail);
    
    // Call the profile manager cloud function
    const response = await profileApi.post('/upload-profile', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
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
    
    const response = await profileApi.get('/list-profiles', {
      params: { user_email: userEmail }
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
export const deleteStudentProfile = async (documentName, userEmail, filename) => {
  try {
    const response = await profileApi.delete('/delete-profile', {
      data: { 
        document_name: documentName,
        user_email: userEmail,
        filename: filename
      }
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
    const response = await profileApi.post('/get-profile-content', {
      user_email: userEmail,
      filename: filename
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

// Get knowledge base approach from environment
const KNOWLEDGE_BASE_APPROACH = import.meta.env.VITE_KNOWLEDGE_BASE_APPROACH || 'rag';

// Determine knowledge base URL based on approach
const getKnowledgeBaseUrl = () => {
  switch (KNOWLEDGE_BASE_APPROACH) {
    case 'elasticsearch':
      return import.meta.env.VITE_KNOWLEDGE_BASE_ES_URL || 'http://localhost:8083';
    case 'firestore':
      return import.meta.env.VITE_KNOWLEDGE_BASE_FS_URL || 'http://localhost:8082';
    default: // rag
      return import.meta.env.VITE_KNOWLEDGE_BASE_URL || 'http://localhost:8081';
  }
};

// Create axios instance for knowledge base manager cloud function
const knowledgeBaseApi = axios.create({
  baseURL: getKnowledgeBaseUrl(),
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json',
  },
});

console.log(`[FRONTEND] Using knowledge base approach: ${KNOWLEDGE_BASE_APPROACH}`);
console.log(`[FRONTEND] Knowledge base URL: ${getKnowledgeBaseUrl()}`);

/**
 * Upload university research document to the college_admissions_kb store
 * Uses the knowledge base manager cloud function
 */
export const uploadKnowledgeBaseDocument = async (file) => {
  try {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await knowledgeBaseApi.post('/upload-document', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
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
      url: knowledgeBaseApi.defaults.baseURL + '/upload-document'
    });
    throw error;
  }
};

/**
 * List all documents in the knowledge base
 * Uses the knowledge base manager cloud function
 */
export const listKnowledgeBaseDocuments = async () => {
  try {
    const response = await knowledgeBaseApi.get('/documents');
    return response.data;
  } catch (error) {
    console.error('Error listing knowledge base documents:', error);
    throw error;
  }
};

/**
 * Delete a document from the knowledge base
 * Uses the knowledge base manager cloud function
 */
export const deleteKnowledgeBaseDocument = async (documentName, filename) => {
  try {
    const response = await knowledgeBaseApi.post('/delete', {
      file_name: documentName  // Backend expects file_name parameter
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
    const response = await knowledgeBaseApi.post('/get-document-content', {
      file_name: fileName
    });
    return response.data;
  } catch (error) {
    console.error('Error getting document content:', error);
    throw error;
  }
};

export default api;
