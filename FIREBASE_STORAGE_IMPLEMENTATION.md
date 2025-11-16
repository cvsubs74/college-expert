# Firebase Storage Implementation for Document Preview

## Overview
Implemented Firebase Storage integration to enable document content preview for both Student Profiles and Knowledge Base documents.

## Architecture

### Storage Structure
```
Firebase Storage Bucket: college-counselling-478115.appspot.com
├── profiles/
│   └── {sanitized_email}/
│       └── {filename}
└── knowledge-base/
    └── {filename}
```

### Data Flow

**Upload Flow:**
1. User uploads file via frontend
2. Cloud Function receives file
3. **Step 1:** Upload to Firebase Storage (for preview/download)
4. **Step 2:** Upload to Gemini File Search (for AI embedding)
5. Return success to frontend

**Preview Flow:**
1. User clicks preview button
2. Frontend calls `/get-profile-content` or `/get-document-content`
3. Cloud Function retrieves file from Firebase Storage
4. Content returned to frontend
5. Display in modal

## Backend Changes

### Profile Manager (`cloud_functions/profile_manager/`)

**Dependencies Added:**
- `firebase-admin==6.4.0`

**New Functions:**
- `get_storage_bucket()` - Get Firebase Storage bucket
- `get_storage_path(user_email, filename)` - Generate storage path

**Updated Functions:**
- `handle_upload()` - Now uploads to both Firebase Storage and File Search
- `handle_get_content()` - Retrieves content from Firebase Storage

**API Endpoint:**
- `POST /get-profile-content`
  - Body: `{user_email, filename}`
  - Returns: `{success, content, mime_type, display_name, storage_path}`

### Knowledge Base Manager (`cloud_functions/knowledge_base_manager/`)

**Dependencies Added:**
- `firebase-admin==6.4.0`

**New Functions:**
- `get_storage_bucket()` - Get Firebase Storage bucket
- `get_storage_path(filename)` - Generate storage path

**Updated Functions:**
- `handle_upload()` - Now uploads to both Firebase Storage and File Search
- `handle_get_content()` - Retrieves content from Firebase Storage

**API Endpoint:**
- `POST /get-document-content`
  - Body: `{file_name}`
  - Returns: `{success, content, mime_type, display_name, storage_path}`

## Frontend Changes

### API Service (`frontend/src/services/api.js`)

**Updated Functions:**
- `getStudentProfileContent(userEmail, filename)` - Pass user email and filename
- `getKnowledgeBaseDocumentContent(fileName)` - Unchanged

### Profile Page (`frontend/src/pages/Profile.jsx`)

**Features:**
- Preview button with eye icon for each document
- Modal with document metadata and content
- Loading state while fetching content
- Scrollable content area with monospace font
- Error handling for missing files

**Preview Modal Sections:**
1. Document Information (name, size, upload date)
2. Document Content (scrollable, max-height 96)

### Knowledge Base Page (`frontend/src/pages/KnowledgeBase.jsx`)

**Features:**
- Same preview functionality as Profile page
- Shared knowledge base documents accessible to all users

## Security

### Firebase Storage Rules (To Be Configured)

```javascript
rules_version = '2';
service firebase.storage {
  match /b/{bucket}/o {
    // Student Profiles - user can only access their own
    match /profiles/{userId}/{allPaths=**} {
      allow read, write: if request.auth != null && 
                           request.auth.token.email.replace('@', '_').replace('.', '_').toLowerCase() == userId;
    }
    
    // Knowledge Base - all authenticated users can read, only admin can write
    match /knowledge-base/{allPaths=**} {
      allow read: if request.auth != null;
      allow write: if request.auth != null && 
                     request.auth.token.email == 'cvsubs@gmail.com';
    }
  }
}
```

## Benefits

1. **Full Content Access** - Can preview actual document content
2. **Better UX** - Users can verify uploaded documents
3. **Dual Storage** - Files in Firebase Storage (preview) + File Search (AI)
4. **Security** - Firebase Auth integration for access control
5. **Scalability** - Firebase Storage handles large files efficiently
6. **Cost Effective** - Free tier covers most use cases

## Deployment Steps

1. **Deploy Cloud Functions:**
   ```bash
   ./deploy_backend.sh
   ```

2. **Configure Firebase Storage Rules:**
   - Go to Firebase Console → Storage → Rules
   - Apply the security rules above

3. **Deploy Frontend:**
   ```bash
   ./deploy_frontend.sh
   ```

4. **Test:**
   - Upload a document
   - Click preview button
   - Verify content displays correctly

## File Types Supported

- **Text Files:** .txt, .md
- **Documents:** .pdf (extracted text), .docx (extracted text)
- **Code:** .py, .js, .json, etc.

Note: Binary files (images, videos) will not display as text. Future enhancement could add file type detection and appropriate viewers.

## Future Enhancements

1. **Direct Frontend Upload** - Upload directly to Firebase Storage from frontend
2. **Progress Tracking** - Show upload progress
3. **File Type Detection** - Display different viewers based on file type
4. **Download Button** - Allow users to download original files
5. **Syntax Highlighting** - For code files
6. **PDF Viewer** - Embedded PDF viewer for PDF files
