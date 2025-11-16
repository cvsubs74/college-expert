# Storage Migration: Firebase Storage → Google Cloud Storage

## Migration Summary

Migrated from Firebase Storage to Google Cloud Storage (GCS) for better control and simpler architecture.

## Changes Made

### 1. Dependencies Updated

**Both `profile_manager` and `knowledge_base_manager`:**
- **Removed**: `firebase-admin==6.4.0`
- **Added**: `google-cloud-storage==2.14.0`

### 2. Code Changes

**Imports:**
```python
# Before
import firebase_admin
from firebase_admin import credentials, storage as firebase_storage

# After
from google.cloud import storage
```

**Storage Client:**
```python
# Before
if not firebase_admin._apps:
    firebase_admin.initialize_app()
bucket = firebase_storage.bucket(FIREBASE_STORAGE_BUCKET)

# After
storage_client = storage.Client()
bucket = storage_client.bucket(GCS_BUCKET_NAME)
```

### 3. Bucket Configuration

**Profile Manager:**
- Bucket: `college-counselling-478115-student-profiles`
- Path structure: `profiles/{sanitized_email}/{filename}`
- Auto-creates bucket on first use

**Knowledge Base Manager:**
- Bucket: `college-counselling-478115-knowledge-base`
- Path structure: `knowledge-base/{filename}`
- Auto-creates bucket on first use

### 4. Storage Flow

**Upload:**
1. File uploaded to GCS bucket
2. Same file uploaded to Gemini File Search (for AI)

**Preview:**
1. Fetch from GCS bucket
2. For PDFs: Show metadata (size, upload date)
3. For text: Show actual content

**Delete:**
1. Delete from GCS bucket
2. Delete from Gemini File Search (with `force=true`)

## Benefits of GCS

1. **Simpler**: No Firebase SDK initialization needed
2. **Direct Access**: Standard GCS APIs and tools
3. **Better Control**: Full bucket management capabilities
4. **Cost Effective**: Pay only for storage used
5. **Integration**: Works seamlessly with Cloud Functions

## Deployment Status

✅ **Profile Manager** - Deployed (revision 00025-zis)
✅ **Knowledge Base Manager** - Deployed (revision 00023-xik)

## Testing

1. Upload a document (PDF or text file)
2. Buckets will be auto-created on first upload
3. Preview should show file metadata
4. Delete should remove from both GCS and File Search

## Bucket Locations

- Region: `us-east1`
- Auto-created with default settings
- Access: Service account based (Cloud Functions default SA)

## Future Enhancements

- Add PDF text extraction (PyPDF2) for better previews
- Implement caching for frequently accessed files
- Add file versioning support
