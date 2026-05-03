import React, { useContext, useState, useEffect, createContext } from 'react';
import { onAuthStateChanged } from 'firebase/auth';
import { auth } from '../firebase';

const AuthContext = createContext();

export function useAuth() {
  return useContext(AuthContext);
}

// Test-mode auth bypass for Playwright E2E. When localStorage contains a
// JSON-serialized user under this key AND we're not in a production build,
// AuthContext skips Firebase and treats that value as the signed-in user.
// The MODE guard means setting this in a real production browser has no
// effect — Vite bakes MODE=production into the production bundle at build
// time, so the conditional below is statically eliminated.
const E2E_USER_KEY = '__E2E_TEST_USER__';

export function AuthProvider({ children }) {
  const [currentUser, setCurrentUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (import.meta.env.MODE !== 'production') {
      try {
        const raw = localStorage.getItem(E2E_USER_KEY);
        if (raw) {
          setCurrentUser(JSON.parse(raw));
          setLoading(false);
          return undefined;
        }
      } catch {
        // Malformed JSON or storage error — fall through to real Firebase auth.
      }
    }

    const unsubscribe = onAuthStateChanged(auth, (user) => {
      // Always clear session data when auth state changes
      // This ensures fresh start for every login session
      localStorage.removeItem('college_counselor_session_id');
      localStorage.removeItem('chatMessages');
      localStorage.removeItem('collegeName');
      localStorage.removeItem('intendedMajor');
      
      if (user) {
        console.log('[AUTH] User signed in:', user.email, '- cleared all session data for fresh start');
      } else {
        console.log('[AUTH] User signed out - cleared all session data');
      }
      
      setCurrentUser(user);
      setLoading(false);
    });

    // Cleanup subscription on unmount
    return unsubscribe;
  }, []);

  const value = {
    currentUser,
    loading, // Expose the loading state
  };

  return (
    <AuthContext.Provider value={value}>
      {children} {/* Render children immediately */}
    </AuthContext.Provider>
  );
}
