# Firebase Authentication Setup Guide

This guide explains how to set up Firebase Authentication with Google Sign-In for the College Counselor application.

## Overview

The College Counselor app now includes Firebase Authentication with Google Sign-In, following the same pattern as the ExpenseWise application.

## Architecture

```
Landing Page (Public)
     ↓
  Sign in with Google
     ↓
Protected Routes (Authenticated)
  ├─ /profile - Student Profile Management
  ├─ /chat - College Information Chat
  └─ /analysis - Admissions Analysis
```

## Files Created

### 1. Firebase Configuration (`src/firebase.js`)
- Initializes Firebase app with environment variables
- Exports `auth` and `googleProvider` instances
- Loads configuration from `.env` file

### 2. Authentication Service (`src/services/authService.js`)
- `signInWithGoogle()` - Handles Google Sign-In popup
- `logout()` - Signs out the current user
- Error handling for authentication failures

### 3. Auth Context (`src/context/AuthContext.jsx`)
- Provides authentication state throughout the app
- `useAuth()` hook for accessing current user
- Listens to Firebase auth state changes
- Exposes `currentUser` and `loading` state

### 4. Protected Route Component (`src/components/auth/ProtectedRoute.jsx`)
- Wraps protected routes
- Redirects unauthenticated users to landing page
- Shows loading spinner during auth check
- Preserves intended destination for post-login redirect

### 5. Landing Page (`src/pages/LandingPage.jsx`)
- Public-facing homepage
- Google Sign-In button
- Feature showcase
- Redirects to `/chat` after successful login

### 6. Updated App.jsx
- Wraps app with `AuthProvider`
- Public route: `/` (Landing Page)
- Protected routes: `/profile`, `/chat`, `/analysis`
- Navigation with user profile and sign-out button

## Firebase Setup Steps

### Step 1: Enable Firebase Authentication

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Select your project: `college-counselling-478115`
3. Navigate to **Authentication** → **Get Started**
4. Click **Sign-in method** tab
5. Enable **Google** provider
6. Add authorized domains:
   - `localhost` (for development)
   - `college-strategy.web.app` (for production)
7. Save changes

### Step 2: Get Firebase Configuration

1. In Firebase Console, go to **Project Settings** (gear icon)
2. Scroll down to **Your apps** section
3. If no web app exists, click **Add app** → **Web** (</>) icon
4. Register app with nickname: "College Counselor"
5. Copy the Firebase configuration object

### Step 3: Configure Environment Variables

Create `frontend/.env` file with your Firebase credentials:

```bash
# Backend API Configuration
VITE_API_URL=https://college-counselor-agent-808989169388.us-east1.run.app
VITE_PROFILE_MANAGER_URL=https://profile-manager-pfnwjfp26a-ue.a.run.app

# Firebase Configuration (replace with your actual values)
VITE_FIREBASE_API_KEY=AIzaSy...
VITE_FIREBASE_AUTH_DOMAIN=college-counselling-478115.firebaseapp.com
VITE_FIREBASE_PROJECT_ID=college-counselling-478115
VITE_FIREBASE_STORAGE_BUCKET=college-counselling-478115.appspot.com
VITE_FIREBASE_MESSAGING_SENDER_ID=808989169388
VITE_FIREBASE_APP_ID=1:808989169388:web:...

# Application Settings
VITE_APP_NAME=College Counselor
VITE_APP_VERSION=1.0.0

# Default Data Stores
VITE_KNOWLEDGE_BASE_STORE=college_admissions_kb
VITE_STUDENT_PROFILE_STORE=student_profile
```

### Step 4: Install Dependencies

```bash
cd frontend
npm install
```

This will install the new `firebase` dependency added to `package.json`.

### Step 5: Update Deployment Script

Update `deploy_frontend.sh` to include Firebase environment variables:

```bash
# Add Firebase variables
export VITE_FIREBASE_API_KEY="your-api-key"
export VITE_FIREBASE_AUTH_DOMAIN="college-counselling-478115.firebaseapp.com"
export VITE_FIREBASE_PROJECT_ID="college-counselling-478115"
export VITE_FIREBASE_STORAGE_BUCKET="college-counselling-478115.appspot.com"
export VITE_FIREBASE_MESSAGING_SENDER_ID="808989169388"
export VITE_FIREBASE_APP_ID="your-app-id"
```

## Testing Locally

1. **Start the frontend:**
   ```bash
   cd frontend
   npm run dev
   ```

2. **Visit:** http://localhost:5173

3. **Test flow:**
   - Should see Landing Page
   - Click "Sign in with Google"
   - Complete Google authentication
   - Should redirect to `/chat`
   - Should see user profile in navigation
   - Try accessing protected routes
   - Test sign out functionality

## User Flow

### First Visit (Unauthenticated)
1. User visits `https://college-strategy.web.app`
2. Sees Landing Page with features and "Sign in with Google" button
3. Clicks sign-in button
4. Google authentication popup appears
5. User selects Google account
6. Redirected to `/chat` page
7. Navigation shows user profile and "Sign Out" button

### Authenticated User
1. User visits any URL
2. Auth state is checked
3. If authenticated, shows requested page
4. If not authenticated, redirects to Landing Page
5. Navigation shows:
   - User's photo and name
   - Sign Out button
   - Links to all protected pages

### Sign Out
1. User clicks "Sign Out" button
2. Firebase signs out user
3. Redirected to Landing Page
4. Protected routes become inaccessible

## Security Features

✅ **Protected Routes** - All main pages require authentication
✅ **Secure Tokens** - Firebase handles JWT tokens automatically
✅ **Session Persistence** - User stays logged in across page refreshes
✅ **Automatic Redirect** - Unauthenticated users redirected to landing page
✅ **State Preservation** - Intended destination saved for post-login redirect

## Navigation Updates

### Before Authentication
- Landing Page only
- No navigation bar

### After Authentication
- Full navigation bar with:
  - College Counselor logo
  - Student Profile link
  - College Info Chat link
  - Admissions Analysis link
  - User profile (photo + name)
  - Sign Out button

## API Integration

The authentication state is available throughout the app via the `useAuth()` hook:

```javascript
import { useAuth } from './context/AuthContext';

function MyComponent() {
  const { currentUser, loading } = useAuth();
  
  if (loading) {
    return <div>Loading...</div>;
  }
  
  if (currentUser) {
    console.log('User:', currentUser.displayName);
    console.log('Email:', currentUser.email);
    console.log('Photo:', currentUser.photoURL);
  }
}
```

## Deployment

### Build with Firebase Config

```bash
cd frontend
npm run build
```

### Deploy to Firebase Hosting

```bash
firebase deploy --only hosting --project college-counselling-478115
```

### Verify Deployment

1. Visit: https://college-strategy.web.app
2. Should see Landing Page
3. Test Google Sign-In
4. Verify protected routes work
5. Test sign out

## Troubleshooting

### Issue: "Firebase: Error (auth/unauthorized-domain)"
**Solution:** Add your domain to Firebase Console → Authentication → Settings → Authorized domains

### Issue: "Firebase configuration not found"
**Solution:** Ensure `.env` file exists with all Firebase variables

### Issue: Sign-in popup blocked
**Solution:** Allow popups for the site in browser settings

### Issue: Redirect loop after sign-in
**Solution:** Check that protected routes are properly configured in App.jsx

### Issue: User state not persisting
**Solution:** Verify Firebase is initialized before rendering app

## File Structure

```
frontend/
├── src/
│   ├── components/
│   │   └── auth/
│   │       └── ProtectedRoute.jsx
│   ├── context/
│   │   └── AuthContext.jsx
│   ├── pages/
│   │   ├── LandingPage.jsx
│   │   ├── Profile.jsx
│   │   ├── Chat.jsx
│   │   └── Analysis.jsx
│   ├── services/
│   │   ├── authService.js
│   │   └── api.js
│   ├── firebase.js
│   └── App.jsx
├── .env (create this with your Firebase config)
├── .env.example
└── package.json
```

## Next Steps

1. ✅ Enable Firebase Authentication in console
2. ✅ Get Firebase configuration
3. ✅ Create `.env` file with credentials
4. ✅ Install dependencies (`npm install`)
5. ✅ Test locally
6. ✅ Update deployment script with Firebase vars
7. ✅ Deploy to production
8. ✅ Test production deployment

## Benefits

✅ **Secure Authentication** - Industry-standard OAuth 2.0
✅ **Easy Integration** - One-click Google Sign-In
✅ **No Backend Changes** - Frontend-only authentication
✅ **User Management** - Firebase handles user accounts
✅ **Session Management** - Automatic token refresh
✅ **Professional UX** - Clean landing page and protected routes

## Support

For issues or questions:
1. Check Firebase Console for authentication logs
2. Review browser console for errors
3. Verify environment variables are set correctly
4. Ensure Firebase project is properly configured

## References

- [Firebase Authentication Docs](https://firebase.google.com/docs/auth)
- [Google Sign-In for Web](https://firebase.google.com/docs/auth/web/google-signin)
- [React Firebase Hooks](https://github.com/CSFrequency/react-firebase-hooks)
