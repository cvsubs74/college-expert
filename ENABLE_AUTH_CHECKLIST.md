# Firebase Authentication Setup Checklist

## Current Error
```
Firebase: Error (auth/configuration-not-found)
CONFIGURATION_NOT_FOUND
```

This means Firebase Authentication is not enabled yet.

## ✅ Setup Steps

### 1. Enable Firebase Authentication

**URL:** https://console.firebase.google.com/project/college-counsellor/authentication/providers

**Steps:**
- [ ] Click **"Get Started"** button (if you see it)
- [ ] You should now see the "Sign-in method" tab

### 2. Enable Google Sign-In Provider

**In the Sign-in providers list:**
- [ ] Click on **"Google"** row
- [ ] Toggle **"Enable"** switch to ON
- [ ] Select your email address in the "Project support email" dropdown
- [ ] Click **"Save"** button

### 3. Verify Authorized Domains

**Click on "Settings" tab:**
- [ ] Verify `localhost` is in the authorized domains list
- [ ] Verify `college-strategy.web.app` is in the authorized domains list
- [ ] If not, click "Add domain" and add them

### 4. Test Authentication

**After enabling:**
- [ ] Go to: https://college-strategy.web.app
- [ ] Click "Sign in with Google"
- [ ] Google authentication popup should appear
- [ ] Select your Google account
- [ ] Should redirect to /chat page
- [ ] Should see your profile picture and name in navigation

## What Each Step Does

### Get Started
- Initializes the Authentication service in your Firebase project
- Creates the authentication configuration

### Enable Google Provider
- Activates Google OAuth 2.0 sign-in
- Configures the OAuth consent screen
- Allows users to sign in with their Google accounts

### Authorized Domains
- Whitelists domains that can use Firebase Auth
- Prevents unauthorized sites from using your Firebase project
- Required for both local development and production

## Expected Result

After completing these steps:

✅ **Landing Page:**
- Shows "Sign in with Google" button
- Clicking it opens Google account selection popup

✅ **After Sign-In:**
- Redirects to `/chat` page
- Navigation shows user's photo and name
- User can access all protected routes

✅ **Profile Management:**
- User can upload academic profile
- Profile stored in user-specific store: `student_profile_<email>`
- Each user has isolated data

✅ **Admissions Analysis:**
- Agent uses correct user's profile
- Analysis based on user's academic data
- Results personalized per user

## Troubleshooting

### Still seeing "configuration-not-found"?
1. Wait 1-2 minutes after enabling (propagation time)
2. Hard refresh the page (Cmd+Shift+R / Ctrl+Shift+R)
3. Clear browser cache
4. Try incognito/private browsing mode

### "unauthorized-domain" error?
1. Go to Settings tab in Authentication
2. Add the domain to authorized domains list
3. Wait a minute and try again

### Sign-in popup blocked?
1. Allow popups for college-strategy.web.app
2. Check browser popup blocker settings

## Current Configuration

**Project:** college-counsellor
**Frontend:** https://college-strategy.web.app
**Backend Agent:** https://college-counselor-agent-pfnwjfp26a-ue.a.run.app
**Profile Manager:** https://profile-manager-pfnwjfp26a-ue.a.run.app

**Firebase Config:**
- API Key: AIzaSyB21YdLOZTjO1przhjsX1Es64-kFGov5XE ✅
- Auth Domain: college-counsellor.firebaseapp.com ✅
- Project ID: college-counsellor ✅

## Next Steps After Authentication Works

1. **Upload Profile:**
   - Go to "Student Profile" page
   - Upload your academic profile document
   - Verify it appears in the list

2. **Test Analysis:**
   - Go to "Admissions Analysis" page
   - Enter college name and major
   - Click "Analyze"
   - Verify agent uses your profile data

3. **Verify Multi-User:**
   - Sign out
   - Sign in with different Google account
   - Upload different profile
   - Verify profiles are isolated

## Summary

The deployment is complete, but Firebase Authentication needs to be enabled in the Console. Follow the checklist above to activate it, then test the sign-in flow. Once working, the multi-user system will be fully operational! 🚀
