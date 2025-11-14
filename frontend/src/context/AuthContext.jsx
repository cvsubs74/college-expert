import React, { useContext, useState, useEffect, createContext } from 'react';
import { onAuthStateChanged } from 'firebase/auth';
import { auth } from '../firebase';

const AuthContext = createContext();

export function useAuth() {
  return useContext(AuthContext);
}

export function AuthProvider({ children }) {
  const [currentUser, setCurrentUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
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
