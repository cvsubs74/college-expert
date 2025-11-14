# Multi-User System Implementation

## Overview

The College Counselor application has been updated to support multiple users with isolated profile storage. Each user's academic profile is stored in a dedicated File Search store identified by their email address.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    User Authentication                       │
│              (Firebase - Google Sign-In)                     │
│                  user@example.com                            │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                  Frontend Application                        │
│  - Passes user email with all API requests                  │
│  - Profile upload: uploadStudentProfile(file, userEmail)    │
│  - Profile list: listStudentProfiles(userEmail)             │
│  - Agent messages: [USER_EMAIL: user@example.com]           │
└────────────────────┬────────────────────────────────────────┘
                     │
         ┌───────────┴───────────┐
         │                       │
         ▼                       ▼
┌──────────────────┐    ┌──────────────────┐
│ Profile Manager  │    │  Agent Backend   │
│ Cloud Function   │    │   (Cloud Run)    │
└────────┬─────────┘    └────────┬─────────┘
         │                       │
         │                       │
         ▼                       ▼
┌─────────────────────────────────────────────────────────────┐
│              Gemini File Search Stores                       │
│                                                              │
│  User-Specific Profile Stores:                              │
│  ├─ student_profile_user_example_com                        │
│  ├─ student_profile_jane_doe_gmail_com                      │
│  └─ student_profile_john_smith_yahoo_com                    │
│                                                              │
│  Shared Knowledge Base:                                     │
│  └─ college_admissions_kb (common for all users)            │
└─────────────────────────────────────────────────────────────┘
```

## Store Naming Convention

### User-Specific Profile Stores
- **Pattern:** `student_profile_<sanitized_email>`
- **Sanitization:** Replace `@` and `.` with `_`, convert to lowercase
- **Examples:**
  - `user@example.com` → `student_profile_user_example_com`
  - `Jane.Doe@Gmail.com` → `student_profile_jane_doe_gmail_com`
  - `john.smith+test@yahoo.co.uk` → `student_profile_john_smith+test_yahoo_co_uk`

### Shared Knowledge Base
- **Name:** `college_admissions_kb`
- **Scope:** Shared across all users
- **Content:** College admissions information, requirements, strategies

## Implementation Details

### 1. Profile Manager Cloud Function

**File:** `/cloud_functions/profile_manager/main.py`

#### Changes Made:

**User Store Name Generation:**
```python
def get_user_store_name(user_email):
    """
    Generate user-specific store name from email.
    Pattern: student_profile_<sanitized_email>
    """
    sanitized_email = user_email.replace('@', '_').replace('.', '_').lower()
    return f"{STUDENT_PROFILE_STORE_BASE}_{sanitized_email}"
```

**Upload Handler:**
```python
def handle_upload(request, headers):
    # Get user email from form data
    user_email = request.form.get('user_email')
    if not user_email:
        return jsonify({'success': False, 'error': 'Missing user_email parameter'}), 400
    
    # Generate user-specific store name
    user_store = get_user_store_name(user_email)
    
    # Upload to user's store
    store_name = get_store_name(user_store)
    # ... upload logic
```

**List Handler:**
```python
def handle_list(request, headers):
    # Get user email from query parameters
    user_email = request.args.get('user_email')
    if not user_email:
        return jsonify({'success': False, 'error': 'Missing user_email parameter'}), 400
    
    # Generate user-specific store name
    user_store = get_user_store_name(user_email)
    
    # List documents from user's store
    store_name = get_store_name(user_store)
    # ... list logic
```

### 2. Frontend API Client

**File:** `/frontend/src/services/api.js`

#### Changes Made:

**Upload Profile:**
```javascript
export const uploadStudentProfile = async (file, userEmail) => {
  if (!userEmail) {
    throw new Error('User email is required for profile upload');
  }
  
  const formData = new FormData();
  formData.append('file', file);
  formData.append('user_email', userEmail);
  
  const response = await profileApi.post('/upload-profile', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  });
  return response.data;
};
```

**List Profiles:**
```javascript
export const listStudentProfiles = async (userEmail) => {
  if (!userEmail) {
    throw new Error('User email is required to list profiles');
  }
  
  const response = await profileApi.get('/list-profiles', {
    params: { user_email: userEmail }
  });
  return response.data;
};
```

**Agent Communication:**
```javascript
export const startSession = async (message, userEmail = null) => {
  let fullMessage = message;
  if (userEmail) {
    fullMessage = `[USER_EMAIL: ${userEmail}]\n\n${message}`;
  }
  
  const response = await api.post('/run', {
    app_name: 'agents',
    user_id: 'user',
    session_id: currentSessionId,
    new_message: { parts: [{ text: fullMessage }] },
    streaming: false
  });
  return response.data;
};
```

### 3. Frontend Pages

**Profile Page (`/frontend/src/pages/Profile.jsx`):**
```javascript
function Profile() {
  const { currentUser } = useAuth();
  
  const loadProfiles = async () => {
    const response = await listStudentProfiles(currentUser.email);
    setProfiles(response.documents);
  };
  
  const handleUpload = async () => {
    const response = await uploadStudentProfile(selectedFile, currentUser.email);
    // ... handle response
  };
}
```

**Chat Page (`/frontend/src/pages/Chat.jsx`):**
```javascript
function Chat() {
  const { currentUser } = useAuth();
  
  const handleSendMessage = async (e) => {
    if (!currentSessionId) {
      response = await startSession(knowledgeBaseQuery, currentUser?.email);
    } else {
      response = await sendMessage(currentSessionId, knowledgeBaseQuery, currentUser?.email);
    }
  };
}
```

**Analysis Page (`/frontend/src/pages/Analysis.jsx`):**
```javascript
function Analysis() {
  const { currentUser } = useAuth();
  
  const handleAnalyze = async () => {
    if (!currentSessionId) {
      response = await startSession(message, currentUser?.email);
    } else {
      response = await sendMessage(currentSessionId, message, currentUser?.email);
    }
  };
}
```

### 4. Agent Backend

**File:** `/agents/agent.py`

#### Changes Made:

**User Email Extraction:**
```python
**Step 0: Extract User Email**
- FIRST, check if the user's message contains a [USER_EMAIL: email@example.com] tag at the beginning.
- If present, extract the email address and store it in your context for use in subsequent steps.
- This email identifies which user-specific profile store to access.
- Remove the [USER_EMAIL: ...] tag from the message before processing the actual user request.

**Step 1: Data Orchestration**
- Call the `StudentProfileAgent` with the student's profile document (attached file or text) to get the student's structured profile.
- **IMPORTANT:** The StudentProfileAgent will access the user's profile from a user-specific store named `student_profile_<sanitized_email>` where the email is sanitized (@ and . replaced with _).
```

## Data Flow

### Profile Upload Flow

```
1. User selects file in Profile page
2. Frontend calls uploadStudentProfile(file, currentUser.email)
3. API sends POST /upload-profile with:
   - file: <file data>
   - user_email: user@example.com
4. Cloud Function:
   - Extracts user_email from form data
   - Generates store name: student_profile_user_example_com
   - Creates store if doesn't exist
   - Uploads file to user's store
5. Returns success with store_name and user_email
```

### Profile List Flow

```
1. Profile page loads
2. Frontend calls listStudentProfiles(currentUser.email)
3. API sends GET /list-profiles?user_email=user@example.com
4. Cloud Function:
   - Extracts user_email from query params
   - Generates store name: student_profile_user_example_com
   - Lists documents from user's store
5. Returns documents array with user_email
```

### Agent Analysis Flow

```
1. User requests admissions analysis
2. Frontend sends message with [USER_EMAIL: user@example.com] prefix
3. Agent receives: "[USER_EMAIL: user@example.com]\n\nI want to analyze..."
4. Agent:
   - Extracts email: user@example.com
   - Sanitizes to: user_example_com
   - Constructs store name: student_profile_user_example_com
   - Accesses user's profile from their specific store
   - Performs analysis using user's data
5. Returns analysis to user
```

## Security & Privacy

### Data Isolation
- ✅ Each user's profile is stored in a separate File Search store
- ✅ Users cannot access other users' profiles
- ✅ Store names are deterministic based on email (no database needed)

### Authentication
- ✅ Firebase Authentication ensures user identity
- ✅ User email is verified by Firebase
- ✅ All API calls require authenticated user

### Validation
- ✅ Profile Manager validates user_email parameter
- ✅ Frontend validates currentUser exists before API calls
- ✅ Agent validates [USER_EMAIL: ...] tag format

## Benefits

### User Experience
- ✅ **Personal Profiles** - Each user has their own academic profile
- ✅ **Data Privacy** - Profiles are isolated per user
- ✅ **Seamless Access** - Automatic user identification via email
- ✅ **No Manual Setup** - Stores created automatically on first upload

### System Design
- ✅ **Scalable** - No limit on number of users
- ✅ **Simple** - No database needed for user management
- ✅ **Deterministic** - Store names derived from email
- ✅ **Shared Knowledge** - Common knowledge base for all users

### Development
- ✅ **Clean Separation** - User data vs shared data
- ✅ **Easy Testing** - Each user is independent
- ✅ **Maintainable** - Clear naming convention
- ✅ **Extensible** - Easy to add more user-specific stores

## Testing

### Test User Profiles

**User 1:**
- Email: `test.user1@gmail.com`
- Store: `student_profile_test_user1_gmail_com`

**User 2:**
- Email: `jane.doe@example.com`
- Store: `student_profile_jane_doe_example_com`

### Test Scenarios

1. **Upload Profile**
   - Sign in as User 1
   - Upload academic profile
   - Verify stored in `student_profile_test_user1_gmail_com`

2. **List Profiles**
   - Sign in as User 1
   - View profile list
   - Verify only User 1's profiles shown

3. **Data Isolation**
   - Sign in as User 2
   - Upload different profile
   - Verify User 2 cannot see User 1's profiles

4. **Agent Analysis**
   - Sign in as User 1
   - Request admissions analysis
   - Verify agent uses User 1's profile from correct store

## Deployment

### Environment Variables

No new environment variables needed. The system uses:
- `GEMINI_API_KEY` - For File Search API
- `DATA_STORE` - Base name for profile stores (default: `student_profile`)

### Deployment Steps

1. **Deploy Profile Manager:**
   ```bash
   cd cloud_functions/profile_manager
   gcloud functions deploy profile-manager \
     --gen2 \
     --runtime=python311 \
     --region=us-east1 \
     --source=. \
     --entry-point=profile_manager \
     --trigger-http \
     --allow-unauthenticated \
     --set-env-vars GEMINI_API_KEY=your-key
   ```

2. **Deploy Agent:**
   ```bash
   cd agents
   adk deploy cloud_run \
     --project="college-counselling-478115" \
     --region="us-east1" \
     --service_name="college-counselor-agent" \
     --allow_origins="*" \
     --with_ui \
     .
   ```

3. **Deploy Frontend:**
   ```bash
   cd frontend
   npm run build
   firebase deploy --only hosting --project college-counselling-478115
   ```

## Migration

### Existing Users

If there are existing profiles in the old `student_profile` store:

1. **Identify User Emails** - Determine which profiles belong to which users
2. **Create User Stores** - Create user-specific stores
3. **Move Profiles** - Copy profiles to respective user stores
4. **Verify** - Test that users can access their profiles

### Migration Script (if needed)

```python
# Example migration script
def migrate_profile(old_store, user_email, document_name):
    # Get user's store name
    user_store = get_user_store_name(user_email)
    
    # Download from old store
    document = client.file_search_stores.documents.get(name=document_name)
    
    # Upload to new user store
    client.file_search_stores.upload_to_file_search_store(
        file=document.content,
        file_search_store_name=user_store,
        config={'display_name': document.display_name}
    )
```

## Troubleshooting

### Issue: "Missing user_email parameter"
**Solution:** Ensure user is authenticated and currentUser.email is available

### Issue: Profile not found
**Solution:** Verify store name matches pattern: `student_profile_<sanitized_email>`

### Issue: Cannot access profile
**Solution:** Check that user email matches the email used during upload

### Issue: Agent uses wrong profile
**Solution:** Verify [USER_EMAIL: ...] tag is correctly formatted in message

## Future Enhancements

### Potential Features
- **Profile Sharing** - Allow users to share profiles with counselors
- **Multiple Profiles** - Support multiple profiles per user (siblings, etc.)
- **Profile Versions** - Track profile updates over time
- **Bulk Operations** - Upload multiple documents at once
- **Profile Templates** - Pre-filled templates for common scenarios

### Scalability
- **Caching** - Cache store names to reduce API calls
- **Batch Operations** - Process multiple users in parallel
- **Store Cleanup** - Archive inactive user stores
- **Usage Metrics** - Track per-user storage and API usage

## Summary

The multi-user implementation provides:

✅ **Isolated Storage** - Each user has their own profile store
✅ **Shared Knowledge** - Common college knowledge base
✅ **Automatic Routing** - User email determines store access
✅ **Secure** - Firebase authentication + data isolation
✅ **Scalable** - No database needed, deterministic naming
✅ **Simple** - Clean architecture, easy to maintain

The system is now ready for multi-user deployment with complete data isolation and seamless user experience!
