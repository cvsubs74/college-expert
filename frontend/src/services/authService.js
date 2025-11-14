import { signInWithPopup, signOut, GoogleAuthProvider } from 'firebase/auth';
import { auth, googleProvider } from '../firebase';

export const signInWithGoogle = async () => {
  try {
    const result = await signInWithPopup(auth, googleProvider);
    // The signed-in user info.
    const user = result.user;
    console.log('User signed in: ', user);
    return user;
  } catch (error) {
    // Handle Errors here.
    const errorCode = error.code;
    const errorMessage = error.message;
    console.error('Google Sign-In Error:', {
      errorCode,
      errorMessage,
    });
    throw error;
  }
};

export const logout = async () => {
  try {
    await signOut(auth);
    console.log('User signed out');
  } catch (error) {
    console.error('Sign Out Error:', error);
    throw error;
  }
};
