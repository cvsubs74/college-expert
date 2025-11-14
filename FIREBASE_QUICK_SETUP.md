# Firebase Authentication - Quick Setup Guide

## Error: `auth/invalid-api-key`

This error occurs because Firebase configuration is not set up in the frontend `.env` file.

## Quick Fix Steps

### Step 1: Get Firebase Configuration

1. **Go to Firebase Console:**
   ```
   https://console.firebase.google.com/project/college-counselling-478115/settings/general
   ```

2. **Add a Web App (if not already done):**
   - Scroll to "Your apps" section
   - Click "Add app" → Select Web (</>) icon
   - Nickname: `College Counselor`
   - Click "Register app"

3. **Copy the Firebase Configuration:**
   You'll see something like:
   ```javascript
   const firebaseConfig = {
     apiKey: "AIzaSy...",
     authDomain: "college-counselling-478115.firebaseapp.com",
     projectId: "college-counselling-478115",
     storageBucket: "college-counselling-478115.appspot.com",
     messagingSenderId: "808989169388",
     appId: "1:808989169388:web:..."
   };
   ```

### Step 2: Run Setup Script

```bash
./setup_firebase_env.sh
```

This will prompt you for each Firebase configuration value and create the `.env` file.

**OR** manually create `frontend/.env`:

```bash
# Backend API Configuration
VITE_API_URL=https://college-counselor-agent-pfnwjfp26a-ue.a.run.app
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

### Step 3: Enable Firebase Authentication

1. **Go to Authentication:**
   ```
   https://console.firebase.google.com/project/college-counselling-478115/authentication/providers
   ```

2. **Click "Get Started"** (if first time)

3. **Enable Google Sign-In:**
   - Click on "Google" in the Sign-in providers list
   - Toggle "Enable"
   - Select a support email
   - Click "Save"

4. **Add Authorized Domains:**
   - Go to "Settings" tab in Authentication
   - Under "Authorized domains", add:
     - `localhost` (for local development)
     - `college-strategy.web.app` (production)

### Step 4: Rebuild and Redeploy Frontend

```bash
cd frontend
npm run build
firebase deploy --only hosting --project college-counselling-478115
```

## Verification

1. Visit: https://college-strategy.web.app
2. You should see the landing page
3. Click "Sign in with Google"
4. Google authentication popup should appear
5. After signing in, you should be redirected to the chat page

## Troubleshooting

### Error: "Firebase: Error (auth/unauthorized-domain)"
**Solution:** Add your domain to authorized domains in Firebase Console

### Error: "Firebase: Error (auth/invalid-api-key)"
**Solution:** Check that `VITE_FIREBASE_API_KEY` is correctly set in `.env`

### Error: Sign-in popup blocked
**Solution:** Allow popups for the site in browser settings

### Changes not reflecting after deployment
**Solution:** 
1. Clear browser cache
2. Hard refresh (Cmd+Shift+R on Mac, Ctrl+Shift+R on Windows)
3. Try incognito/private browsing mode

## Current Deployment URLs

- **Frontend:** https://college-strategy.web.app
- **Backend Agent:** https://college-counselor-agent-pfnwjfp26a-ue.a.run.app
- **Profile Manager:** https://profile-manager-pfnwjfp26a-ue.a.run.app

## Firebase Console Links

- **Project Overview:** https://console.firebase.google.com/project/college-counselling-478115/overview
- **Authentication:** https://console.firebase.google.com/project/college-counselling-478115/authentication
- **Project Settings:** https://console.firebase.google.com/project/college-counselling-478115/settings/general
- **Hosting:** https://console.firebase.google.com/project/college-counselling-478115/hosting

## Complete Setup Checklist

- [ ] Get Firebase configuration from Console
- [ ] Create `frontend/.env` with Firebase config
- [ ] Enable Firebase Authentication
- [ ] Enable Google Sign-In provider
- [ ] Add authorized domains (localhost, college-strategy.web.app)
- [ ] Rebuild frontend (`npm run build`)
- [ ] Deploy frontend (`firebase deploy --only hosting`)
- [ ] Test sign-in at https://college-strategy.web.app
- [ ] Verify user-specific profile upload works
- [ ] Test admissions analysis with user profile

## Summary

The deployment was successful, but Firebase Authentication needs to be configured. Follow the steps above to:

1. ✅ Get Firebase config from Console
2. ✅ Run `./setup_firebase_env.sh` or manually create `.env`
3. ✅ Enable Google Sign-In in Firebase Console
4. ✅ Rebuild and redeploy frontend
5. ✅ Test authentication flow

Once configured, the multi-user system will work with:
- Firebase authentication for user identity
- User-specific profile stores: `student_profile_<email>`
- Shared knowledge base: `college_admissions_kb`
