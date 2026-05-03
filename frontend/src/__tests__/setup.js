// Vitest global setup — runs once before any test file.
//
// Pulls in jest-dom matchers (toBeInTheDocument, toHaveClass, etc.) and
// mocks Vite's import.meta.env values so components that read URLs at
// module load time don't crash.

import '@testing-library/jest-dom/vitest';
import { vi } from 'vitest';

// import.meta.env values that components read at module init time. These
// match the production .env shape but with placeholder URLs — every API
// call is mocked in tests anyway, so the values just need to be truthy
// strings to satisfy module-level fallback checks.
const envMocks = {
    VITE_PROFILE_MANAGER_V2_URL: 'http://test-profile-manager.example',
    VITE_KNOWLEDGE_BASE_UNIVERSITIES_URL: 'http://test-kb.example',
    VITE_COUNSELOR_AGENT_URL: 'http://test-counselor.example',
    VITE_RAG_AGENT_URL: 'http://test-rag.example',
    VITE_ES_AGENT_URL: 'http://test-es.example',
    VITE_HYBRID_AGENT_URL: 'http://test-hybrid.example',
    VITE_VERTEXAI_AGENT_URL: 'http://test-vertex.example',
    VITE_PROFILE_MANAGER_URL: 'http://test-profile-manager-v1.example',
    VITE_PROFILE_MANAGER_ES_URL: 'http://test-pm-es.example',
    VITE_PROFILE_MANAGER_VERTEXAI_URL: 'http://test-pm-vx.example',
    VITE_KNOWLEDGE_BASE_URL: 'http://test-kb-rag.example',
    VITE_KNOWLEDGE_BASE_ES_URL: 'http://test-kb-es.example',
    VITE_KNOWLEDGE_BASE_VERTEXAI_URL: 'http://test-kb-vx.example',
    VITE_KNOWLEDGE_BASE_APPROACH: 'hybrid',
    VITE_FIREBASE_API_KEY: 'test-key',
    VITE_FIREBASE_AUTH_DOMAIN: 'test.firebaseapp.com',
    VITE_FIREBASE_PROJECT_ID: 'test-project',
    VITE_FIREBASE_STORAGE_BUCKET: 'test.appspot.com',
    VITE_FIREBASE_MESSAGING_SENDER_ID: '0',
    VITE_FIREBASE_APP_ID: 'test-app-id',
};
// Vitest doesn't expose import.meta.env directly to vi.stubEnv before
// modules load, so we patch the underlying object.
Object.assign(import.meta.env, envMocks);

// Silence the framer-motion "ReactDOM.findDOMNode" deprecation noise that
// shows up in jsdom — it's not an issue we can fix and floods the output.
const origConsoleError = console.error;
console.error = (...args) => {
    const msg = args[0];
    if (typeof msg === 'string' && msg.includes('ReactDOM.findDOMNode')) return;
    origConsoleError(...args);
};

// Make sure each test starts with a clean URL state. jsdom's history is
// per-window and tests don't share windows, but the navigate() helper from
// react-router relies on document.location; reset the search part so a
// previous test's ?tab=foo doesn't leak.
beforeEach(() => {
    window.history.replaceState({}, '', '/');
});

// Many components read currentUser.email; consumers can override with a
// fresh vi.mock at the file level when they need a different shape.
export const TEST_USER_EMAIL = 'test.user@example.com';

// Convenience: a minimal mock of the AuthContext so every test doesn't
// have to wrap in <AuthProvider> with full context plumbing.
vi.mock('../context/AuthContext', () => ({
    useAuth: () => ({
        currentUser: { email: 'test.user@example.com', uid: 'test-uid' },
    }),
    AuthProvider: ({ children }) => children,
}));

// Toast is also globally consumed; export the spies so individual tests
// can assert on success/error toasts.
export const toastSpy = {
    success: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
    loading: vi.fn(),
    remove: vi.fn(),
    update: vi.fn(),
};
vi.mock('../components/Toast', () => ({
    useToast: () => toastSpy,
    ToastProvider: ({ children }) => children,
}));

// Reset toast call history between tests automatically.
beforeEach(() => {
    Object.values(toastSpy).forEach((fn) => fn.mockClear());
});
