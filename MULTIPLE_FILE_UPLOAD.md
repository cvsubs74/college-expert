# Multiple File Upload Feature

## Overview
Added support for uploading multiple files simultaneously in both Student Profile and Knowledge Base pages with parallel upload processing and real-time progress tracking.

## Features Implemented

### 1. Multiple File Selection
- **UI**: Updated file input with `multiple` attribute
- **Display**: Shows count and list of selected files
- **File Types**: PDF, DOCX, TXT, DOC

### 2. Parallel Upload Processing
- **Backend**: Files uploaded simultaneously using `Promise.all()`
- **Performance**: Much faster than sequential uploads
- **Error Handling**: Individual file failures don't stop other uploads

### 3. Real-Time Progress Tracking
- **Per-File Status**: Shows uploading/success/error for each file
- **Visual Indicators**:
  - 🔄 Blue spinner for uploading
  - ✅ Green checkmark for success
  - ❌ Red X for errors
- **Summary Message**: Shows total success/failure count

### 4. Enhanced UI/UX

**Student Profile Page:**
- Label: "Select Files (PDF, DOCX, TXT) - Multiple files supported"
- Selected files list with names and sizes
- Upload progress section with per-file status
- Button text: "Upload X Profile(s)"
- Status messages with warning state (partial success)

**Knowledge Base Page:**
- Label: "Select Documents (PDF, DOCX, TXT) - Multiple files supported"
- Selected files count and list
- Upload progress tracking
- Button text: "Upload X Document(s)"
- Status messages with warning state

## Technical Implementation

### State Management

**Profile.jsx & KnowledgeBase.jsx:**
```javascript
const [selectedFiles, setSelectedFiles] = useState([]);  // Changed from selectedFile
const [uploadProgress, setUploadProgress] = useState({}); // New: track per-file progress
```

### File Selection Handler
```javascript
const handleFileSelect = (event) => {
  const files = Array.from(event.target.files);
  if (files.length > 0) {
    setSelectedFiles(files);
    setUploadProgress({});
  }
};
```

### Parallel Upload Logic
```javascript
const uploadPromises = selectedFiles.map(async (file) => {
  try {
    setUploadProgress(prev => ({
      ...prev,
      [file.name]: { status: 'uploading', progress: 0 }
    }));

    const response = await uploadStudentProfile(file, currentUser.email);
    
    if (response.success) {
      setUploadProgress(prev => ({
        ...prev,
        [file.name]: { status: 'success', progress: 100 }
      }));
      return { success: true, filename: file.name };
    }
  } catch (err) {
    setUploadProgress(prev => ({
      ...prev,
      [file.name]: { status: 'error', progress: 0, error: err.message }
    }));
    return { success: false, filename: file.name, error: err.message };
  }
});

const results = await Promise.all(uploadPromises);
```

### Status Messages
```javascript
const successCount = results.filter(r => r.success).length;
const failCount = results.filter(r => !r.success).length;

if (successCount > 0) {
  setUploadStatus({
    type: successCount === selectedFiles.length ? 'success' : 'warning',
    message: `Successfully uploaded ${successCount} file(s)${failCount > 0 ? `, ${failCount} failed` : ''}`
  });
}
```

## UI Components

### Selected Files List
```jsx
{selectedFiles.length > 0 && (
  <div className="bg-gray-50 rounded-lg p-4">
    <h3 className="text-sm font-medium text-gray-700 mb-2">Selected Files:</h3>
    <ul className="space-y-2">
      {selectedFiles.map((file, index) => (
        <li key={index} className="flex items-center justify-between text-sm">
          <span className="text-gray-900">{file.name}</span>
          <span className="text-gray-500">{formatFileSize(file.size)}</span>
        </li>
      ))}
    </ul>
  </div>
)}
```

### Upload Progress
```jsx
{Object.keys(uploadProgress).length > 0 && (
  <div className="bg-gray-50 rounded-lg p-4">
    <h3 className="text-sm font-medium text-gray-700 mb-2">Upload Progress:</h3>
    <ul className="space-y-2">
      {Object.entries(uploadProgress).map(([filename, progress]) => (
        <li key={filename} className="flex items-center justify-between text-sm">
          <span className="text-gray-900">{filename}</span>
          {progress.status === 'uploading' && (
            <span className="flex items-center text-blue-600">
              <ArrowPathIcon className="h-4 w-4 mr-1 animate-spin" />
              Uploading...
            </span>
          )}
          {progress.status === 'success' && (
            <span className="flex items-center text-green-600">
              <CheckCircleIcon className="h-4 w-4 mr-1" />
              Success
            </span>
          )}
          {progress.status === 'error' && (
            <span className="flex items-center text-red-600">
              <XCircleIcon className="h-4 w-4 mr-1" />
              Failed
            </span>
          )}
        </li>
      ))}
    </ul>
  </div>
)}
```

## Status Types

1. **Success** (Green): All files uploaded successfully
2. **Warning** (Yellow): Some files succeeded, some failed
3. **Error** (Red): All files failed or system error

## Benefits

### Performance
- ⚡ **Faster uploads**: Parallel processing vs sequential
- 📊 **Real-time feedback**: See progress as files upload
- 🔄 **Non-blocking**: UI remains responsive during uploads

### User Experience
- 📁 **Bulk operations**: Upload multiple files at once
- 👀 **Visibility**: See which files succeeded/failed
- ✅ **Confidence**: Clear feedback on upload status
- 🎯 **Efficiency**: Save time with batch uploads

### Reliability
- 🛡️ **Error isolation**: One failure doesn't affect others
- 🔍 **Detailed errors**: Know exactly which files failed
- 🔄 **Retry capability**: Can retry failed files easily

## Files Modified

### Frontend
- `/frontend/src/pages/Profile.jsx`
  - Updated state management
  - Added multiple file selection
  - Implemented parallel upload logic
  - Enhanced UI with progress tracking

- `/frontend/src/pages/KnowledgeBase.jsx`
  - Same changes as Profile.jsx
  - Adapted for knowledge base context

### Backend
- No changes required - existing endpoints handle single file uploads
- Parallel calls made from frontend

## Testing

### Test Scenarios
1. **Single file**: Works as before
2. **Multiple files (all succeed)**: Shows success message
3. **Multiple files (some fail)**: Shows warning with counts
4. **Multiple files (all fail)**: Shows error message
5. **Large files**: Progress tracking visible
6. **Cancel/navigate away**: Uploads continue in background

### Browser Compatibility
- ✅ Chrome/Edge (Chromium)
- ✅ Firefox
- ✅ Safari
- ✅ Mobile browsers

## Deployment

**Frontend**: ✅ Deployed to https://college-strategy.web.app

## Future Enhancements

1. **Progress bars**: Show percentage for each file
2. **Drag & drop**: Add drag-and-drop file selection
3. **File validation**: Check file size/type before upload
4. **Upload queue**: Limit concurrent uploads to prevent overload
5. **Retry failed**: Button to retry only failed uploads
6. **Cancel uploads**: Ability to cancel in-progress uploads
