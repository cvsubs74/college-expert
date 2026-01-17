"""
Google Cloud Function for managing student profiles with Firestore.
Version 2 - Migrated from Elasticsearch to Firestore backend.
NO Flask app -  follows ES pattern with direct request handling.
"""

import os
import logging
import json
from datetime import datetime
import functions_framework
from flask import jsonify, request

# Import all modules  
from firestore_db import get_db
from profile_operations import (
    process_and_index_profile,
    get_student_profile,
    cleanup_profile_on_document_delete,
    update_profile_field
)
from gcs_storage import (
    download_file_from_gcs,
    delete_file_from_gcs,
    list_user_files
)
from college_list import (
    add_university_to_list,
    remove_university_from_list,
    get_college_list,
    update_list_item
)
from fit_analysis import (
    save_fit_analysis,
    get_fit_analysis,
    get_all_fits,
    delete_fit_analysis
)
from credits import (
    get_user_credits,
    check_credits_available,
    deduct_credit,
    add_credits,
    upgrade_subscription
)
from profile_chat import profile_chat
from fit_chat_firestore import (
    fit_chat,
    save_fit_chat_conversation,
    list_fit_chat_conversations,
    load_fit_chat_conversation,
    delete_fit_chat_conversation
)
from essay_copilot import (
    generate_essay_starters,
    get_copilot_suggestion,
    essay_chat,
    get_draft_feedback,
    save_essay_draft,
    get_essay_drafts,
    get_starter_context,
    fetch_university_profile,
    generate_essay_outline
)
from fit_computation import calculate_fit_for_college

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get configuration
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID")
GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME", "college-counselling-478115-student-profiles")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

logger.info(f"[INIT] Profile Manager V2 (Firestore) starting...")
logger.info(f"[INIT] Project: {GCP_PROJECT_ID}, Bucket: {GCS_BUCKET_NAME}")


# ============== CORS HELPER ==============

def add_cors_headers(response_data, status_code=200):
    """Add CORS headers to response."""
    response = jsonify(response_data)
    response.status_code = status_code
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, X-User-Email'
    return response


# ============== MAIN ENTRY POINT ==============

@functions_framework.http
def profile_manager_v2_http_entry(request):
    """HTTP Cloud Function entry point - ES pattern."""
    
    # Enable CORS
    if request.method == 'OPTIONS':
        return add_cors_headers({'status': 'ok'}, 200)
    
    # Parse path to determine resource type
    path_parts = request.path.strip('/').split('/')
    
    if not path_parts or len(path_parts) == 0:
        return add_cors_headers({'error': 'Not Found'}, 404)
    
    resource_type = path_parts[0]
    logger.info(f"Processing {request.method} request for resource_type: {resource_type}, path: {request.path}")
    
    try:
        # --- HEALTH CHECK ---
        if resource_type == 'health' and request.method == 'GET':
            return add_cors_headers({
                'status': 'healthy',
                'service': 'profile_manager_v2',
                'backend': 'firestore',
                'version': '2.0.0'
            })
        
        # --- UPLOAD PROFILE ---
        elif resource_type == 'upload-profile' and request.method == 'POST':
            try:
                user_email = request.headers.get('X-User-Email') or request.form.get('user_email')
                
                if not user_email:
                    return add_cors_headers({'error': 'user_email required'}, 400)
                
                if 'file' not in request.files:
                    return add_cors_headers({'error': 'No file uploaded'}, 400)
                
                file = request.files['file']
                if file.filename == '':
                    return add_cors_headers({'error': 'Empty filename'}, 400)
                
                file_content = file.read()
                filename = file.filename
                content_type = file.content_type
                
                logger.info(f"[UPLOAD] Processing {filename} for {user_email}")
                
                result = process_and_index_profile(
                    user_id=user_email,
                    filename=filename,
                    file_content=file_content,
                    file_metadata={'content_type': content_type}
                )
                
                return add_cors_headers(result, 200 if result.get('success') else 500)
            except Exception as e:
                logger.error(f"[UPLOAD] Error: {e}", exc_info=True)
                return add_cors_headers({'success': False, 'error': str(e)}, 500)
        
        # --- LIST PROFILES ---
        elif resource_type == 'list-profiles' and request.method == 'GET':
            user_email = request.args.get('user_email')
            
            if not user_email:
                return add_cors_headers({'error': 'user_email required'}, 400)
            
            files = list_user_files(user_email)
            
            # Transform to match ES format - frontend expects 'documents' not 'files'
            documents = []
            for file in files:
                documents.append({
                    'name': f"{user_email}/{file['filename']}",  # Full GCS path as 'name'
                    'display_name': file['filename'],
                    'size_bytes': file['size'],
                    'create_time': file['updated'],
                    'state': 'ACTIVE',
                    'content_type': file['content_type']
                })
            
            return add_cors_headers({
                'success': True,
                'documents': documents,  # Frontend expects 'documents' not 'files'
                'total': len(documents)
            })
        
        # --- DOWNLOAD DOCUMENT ---
        elif resource_type == 'download-document' and request.method == 'GET':
            user_email = request.args.get('user_email')
            filename = request.args.get('filename')
            
            if not user_email or not filename:
                return add_cors_headers({'error': 'user_email and filename required'}, 400)
            
            result = download_file_from_gcs(user_email, filename)
            
            if result['success']:
                from flask import send_file
                import io
                return send_file(
                    io.BytesIO(result['file_content']),
                    mimetype=result.get('content_type', 'application/octet-stream'),
                    as_attachment=True,
                    download_name=filename
                )
            else:
                return add_cors_headers(result, 404)
        
        # --- DELETE PROFILE ---
        elif resource_type == 'delete-profile' and request.method in ['POST', 'DELETE']:
            data = request.get_json() or {}
            user_id = data.get('user_email') or data.get('user_id')
            filename = data.get('filename')
            
            if not user_id or not filename:
                return add_cors_headers({'error': 'user_email and filename required'}, 400)
            
            cleanup_profile_on_document_delete(user_id, filename)
            result = delete_file_from_gcs(user_id, filename)
            
            return add_cors_headers(result)
        
        # --- PROFILE LOOKUP ---
        elif resource_type == 'get-profile' and request.method in ['GET', 'POST']:
            if request.method == 'POST':
                data = request.get_json()
                user_id = data.get('user_email') or data.get('user_id')
            else:
                # GET request - use query parameters
                user_id = request.args.get('user_email') or request.args.get('user_id')
            
            if not user_id:
                return add_cors_headers({'error': 'user_email or user_id required'}, 400)
            
            profile = get_student_profile(user_id)
            
            if profile:
                # Match ES format - return singular 'profile' not arrays
                # Also include 'content' field for frontend markdown display
                return add_cors_headers({
                    'success': True,
                    'profile': profile,
                    'content': profile.get('raw_content', ''),  # Frontend expects this
                    'filename': profile.get('original_filename')
                })
            else:
                return add_cors_headers({
                    'success': False,
                    'error': 'No profile found for user',
                    'profile': None
                }, 404)
        
        
        # --- SEARCH ENDPOINT (for fit recomputation check) ---
        elif resource_type == 'update-structured-field' and request.method == 'POST':
            data = request.get_json() or {}
            user_id = data.get('user_email') or data.get('user_id')
            field_path = data.get('field_path')
            value = data.get('value')
            operation = data.get('operation', 'set')
            
            if not user_id:
                return add_cors_headers({'error': 'user_email required'}, 400)
            if not field_path:
                return add_cors_headers({'error': 'field_path required'}, 400)
            
            result = update_profile_field(user_id, field_path, value, operation)
            return add_cors_headers(result, 200 if result.get('success') else 400)
        
        
        # --- SEARCH ENDPOINT (for fit recomputation check) ---
        elif resource_type == 'search' and request.method == 'POST':
            data = request.get_json() or {}
            user_id = data.get('user_email') or data.get('user_id')
            
            if not user_id:
                return add_cors_headers({'error': 'User ID/Email is required'}, 400)
            
            # Return profile info for fit recomputation checking
            profile = get_student_profile(user_id)
            if profile:
                return add_cors_headers({
                    'success': True,
                    'profiles': [profile],
                    'total': 1
                })
            else:
                return add_cors_headers({
                    'success': True,
                    'profiles': [],
                    'total': 0
                })
        
        # --- COLLEGE LIST MANAGEMENT ---
        elif resource_type == 'add-to-list' and request.method == 'POST':
            data = request.get_json()
            user_email = data.get('user_email')
            university_id = data.get('university_id')
            
            if not user_email or not university_id:
                return add_cors_headers({'error': 'user_email and university_id required'}, 400)
            
            result = add_university_to_list(user_email, university_id, data)
            return add_cors_headers(result)
        
        # --- UPDATE COLLEGE LIST (add or remove) ---
        elif resource_type == 'update-college-list' and request.method == 'POST':
            data = request.get_json() or {}
            user_id = data.get('user_id') or data.get('user_email')
            action = data.get('action')  # 'add' or 'remove'
            university = data.get('university', {})
            
            if not user_id:
                return add_cors_headers({'error': 'User ID is required'}, 400)
            if not action or action not in ['add', 'remove']:
                return add_cors_headers({'error': 'Action must be "add" or "remove"'}, 400)
            if not university or not university.get('id'):
                return add_cors_headers({'error': 'University with id is required'}, 400)
            
            university_id = university['id']
            
            if action == 'add':
                # Extract university_name from multiple possible sources
                university_data = {
                    'university_name': university.get('name') or data.get('university_name') or university_id,
                    'category': university.get('category', 'target'),
                    'notes': university.get('notes', ''),
                    'status': university.get('status', 'planning'),
                    'application_deadline': university.get('application_deadline')
                }
                result = add_university_to_list(user_id, university_id, university_data)
            else:  # remove
                result = remove_university_from_list(user_id, university_id)
            
            return add_cors_headers(result)
        
        elif resource_type == 'get-college-list' and request.method in ['GET', 'POST']:
            if request.method == 'POST':
                data = request.get_json()
                user_email = data.get('user_email')
            else:
                user_email = request.args.get('user_email')
            
            if not user_email:
                return add_cors_headers({'error': 'user_email required'}, 400)
            
            universities = get_college_list(user_email)
            return add_cors_headers({
                'success': True,
                'college_list': universities  # Frontend expects 'college_list' not 'universities'
            })
        
        elif resource_type == 'remove-from-list' and request.method in ['POST', 'DELETE']:
            data = request.get_json()
            user_email = data.get('user_email')
            university_id = data.get('university_id')
            
            if not user_email or not university_id:
                return add_cors_headers({'error': 'user_email and university_id required'}, 400)
            
            result = remove_university_from_list(user_email, university_id)
            return add_cors_headers(result)
        
        elif resource_type == 'update-list-item' and request.method in ['POST', 'PUT']:
            data = request.get_json()
            user_email = data.get('user_email')
            university_id = data.get('university_id')
            
            if not user_email or not university_id:
                return add_cors_headers({'error': 'user_email and university_id required'}, 400)
            
            result = update_list_item(user_email, university_id, data)
            return add_cors_headers(result)
        
        # --- FIT ANALYSIS OPERATIONS ---
        elif resource_type == 'save-fit-analysis' and request.method == 'POST':
            data = request.get_json()
            user_email = data.get('user_email')
            university_id = data.get('university_id')
            fit_analysis = data.get('fit_analysis')
            
            if not user_email or not university_id or not fit_analysis:
                return add_cors_headers({'error': 'user_email, university_id, and fit_analysis required'}, 400)
            
            result = save_fit_analysis(user_email, university_id, fit_analysis)
            return add_cors_headers(result)
        
        elif resource_type == 'get-fit-analysis' and request.method in ['GET', 'POST']:
            if request.method == 'POST':
                data = request.get_json()
                user_email = data.get('user_email')
                university_id = data.get('university_id')
            else:
                user_email = request.args.get('user_email')
                university_id = request.args.get('university_id')
            
            if not user_email or not university_id:
                return add_cors_headers({'error': 'user_email and university_id required'}, 400)
            
            result = get_fit_analysis(user_email, university_id)
            return add_cors_headers(result)
        
        elif resource_type == 'get-fits' and request.method in ['GET', 'POST']:
            if request.method == 'POST':
                data = request.get_json()
                user_email = data.get('user_email')
            else:
                user_email = request.args.get('user_email')
            
            if not user_email:
                return add_cors_headers({'error': 'user_email required'}, 400)
            
            fits = get_all_fits(user_email)
            return add_cors_headers({
                'success': True,
                'fits': fits
            })
        
        elif resource_type == 'delete-fit-analysis' and request.method in ['POST', 'DELETE']:
            data = request.get_json()
            user_email = data.get('user_email')
            university_id = data.get('university_id')
            
            if not user_email or not university_id:
                return add_cors_headers({'error': 'user_email and university_id required'}, 400)
            
            result = delete_fit_analysis(user_email, university_id)
            return add_cors_headers(result)
        
        # --- COMPUTE SINGLE FIT ---
        elif resource_type == 'compute-single-fit' and request.method == 'POST':
            data = request.get_json()
            user_email = data.get('user_email')
            university_id = data.get('university_id')
            
            if not user_email or not university_id:
                return add_cors_headers({'error': 'user_email and university_id required'}, 400)
            
            # Get student profile
            profile = get_student_profile(user_email)
            if not profile:
                return add_cors_headers({'error': 'Profile not found'}, 404)
            
            # Fetch university profile
            university_profile = fetch_university_profile(university_id)
            if not university_profile:
                return add_cors_headers({'error': 'University profile not found'}, 404)
            
            # Compute fit
            fit_analysis = calculate_fit_for_college(user_email, university_id, intended_major=profile.get('intended_major', ''))
            
            # Save fit analysis
            save_fit_analysis(user_email, university_id, fit_analysis)
            
            return add_cors_headers({
                'success': True,
                'fit_analysis': fit_analysis,
                'university_id': university_id
            })
        
        # --- CREDITS ---
        elif resource_type == 'get-credits' and request.method in ['GET', 'POST']:
            if request.method == 'POST':
                data = request.get_json()
                user_email = data.get('user_email')
            else:
                user_email = request.args.get('user_email')
            
            if not user_email:
                return add_cors_headers({'error': 'user_email required'}, 400)
            
            result = get_user_credits(user_email)
            return add_cors_headers(result)
        
        elif resource_type == 'check-credits' and request.method == 'POST':
            data = request.get_json()
            user_email = data.get('user_email')
            credits_required = data.get('credits_required', 1)
            
            if not user_email:
                return add_cors_headers({'error': 'user_email required'}, 400)
            
            result = check_credits_available(user_email, credits_required)
            return add_cors_headers(result)
        
        elif resource_type == 'deduct-credit' and request.method == 'POST':
            data = request.get_json()
            user_email = data.get('user_email')
            # Accept multiple parameter names for credits count
            credit_count = data.get('amount') or data.get('credits') or data.get('credit_count', 1)
            # Accept multiple parameter names for reason
            reason = data.get('action') or data.get('operation') or data.get('reason', 'fit_analysis')
            
            if not user_email:
                return add_cors_headers({'error': 'user_email required'}, 400)
            
            # Call with correct parameter order: user_id, credit_count, reason
            result = deduct_credit(user_email, credit_count, reason)
            return add_cors_headers(result)
        
        elif resource_type == 'add-credits' and request.method == 'POST':
            data = request.get_json()
            user_email = data.get('user_email')
            credits = data.get('credits')
            source = data.get('source', 'manual')
            
            if not user_email or credits is None:
                return add_cors_headers({'error': 'user_email and credits required'}, 400)
            
            result = add_credits(user_email, credits, source)
            return add_cors_headers(result)
        
        elif resource_type == 'upgrade-subscription' and request.method == 'POST':
            data = request.get_json()
            user_email = data.get('user_email')
            tier = data.get('tier')
            
            if not user_email or not tier:
                return add_cors_headers({'error': 'user_email and tier required'}, 400)
            
            result = upgrade_subscription(user_email, plan_type=tier)
            return add_cors_headers(result)
        
        # --- PROFILE CHAT ---
        elif resource_type == 'profile-chat' and request.method == 'POST':
            data = request.get_json() or {}
            user_email = data.get('user_email') or request.headers.get('X-User-Email')
            question = data.get('question', '')
            conversation_history = data.get('conversation_history', [])
            
            if not user_email:
                return add_cors_headers({'error': 'user_email required'}, 400)
            
            result = profile_chat(user_email, question, conversation_history)
            return add_cors_headers(result)
        
        # --- FIT CHAT (Context Injection) ---
        elif resource_type == 'fit-chat' and request.method == 'POST':
            data = request.get_json() or {}
            user_email = data.get('user_email') or request.headers.get('X-User-Email')
            university_id = data.get('university_id')
            question = data.get('question', '')
            history = data.get('conversation_history', [])
            
            if not user_email:
                return add_cors_headers({'success': False, 'error': 'user_email required'}, 400)
            if not university_id or not question:
                return add_cors_headers({'success': False, 'error': 'university_id and question required'}, 400)
            
            result = fit_chat(user_email, university_id, question, history)
            return add_cors_headers(result, 200 if result.get('success') else 400)
        
        # --- FIT CHAT CONVERSATION SAVE ---
        elif resource_type == 'fit-chat-save' and request.method == 'POST':
            data = request.get_json() or {}
            user_email = data.get('user_email') or request.headers.get('X-User-Email')
            university_id = data.get('university_id')
            university_name = data.get('university_name', university_id)
            messages = data.get('messages', [])
            conversation_id = data.get('conversation_id')  # Optional for updates
            title = data.get('title')  # Optional, auto-generated if not provided
            
            if not user_email or not university_id:
                return add_cors_headers({'success': False, 'error': 'user_email and university_id required'}, 400)
            if not messages:
                return add_cors_headers({'success': False, 'error': 'messages required'}, 400)
            
            result = save_fit_chat_conversation(user_email, university_id, university_name, 
                                               messages, conversation_id, title)
            return add_cors_headers(result, 200 if result.get('success') else 400)
        
        # --- FIT CHAT CONVERSATION LIST ---
        elif resource_type == 'fit-chat-list' and request.method in ['GET', 'POST']:
            if request.method == 'POST':
                data = request.get_json() or {}
            else:
                data = {}
            user_email = data.get('user_email') or request.args.get('user_email') or request.headers.get('X-User-Email')
            university_id = data.get('university_id') or request.args.get('university_id')  # Optional filter
            limit = int(data.get('limit') or request.args.get('limit') or 20)
            
            if not user_email:
                return add_cors_headers({'success': False, 'error': 'user_email required'}, 400)
            
            result = list_fit_chat_conversations(user_email, university_id, limit)
            return add_cors_headers(result, 200 if result.get('success') else 400)
        
        # --- FIT CHAT CONVERSATION LOAD ---
        elif resource_type == 'fit-chat-load' and request.method in ['GET', 'POST']:
            if request.method == 'POST':
                data = request.get_json() or {}
            else:
                data = {}
            user_email = data.get('user_email') or request.args.get('user_email') or request.headers.get('X-User-Email')
            conversation_id = data.get('conversation_id') or request.args.get('conversation_id')
            
            if not user_email or not conversation_id:
                return add_cors_headers({'success': False, 'error': 'user_email and conversation_id required'}, 400)
            
            result = load_fit_chat_conversation(user_email, conversation_id)
            return add_cors_headers(result, 200 if result.get('success') else 400)
        
        # --- FIT CHAT CONVERSATION DELETE ---
        elif resource_type == 'fit-chat-delete' and request.method in ['POST', 'DELETE']:
            data = request.get_json() or {}
            user_email = data.get('user_email') or request.headers.get('X-User-Email')
            conversation_id = data.get('conversation_id')
            
            if not user_email or not conversation_id:
                return add_cors_headers({'success': False, 'error': 'user_email and conversation_id required'}, 400)
            
            result = delete_fit_chat_conversation(user_email, conversation_id)
            return add_cors_headers(result, 200 if result.get('success') else 400)
        
        # --- PROFILE (SELF-DISCOVERY) CHAT SAVE ---
        elif resource_type == 'profile-chat-save' and request.method == 'POST':
            data = request.get_json() or {}
            user_email = data.get('user_email') or request.headers.get('X-User-Email')
            messages = data.get('messages', [])
            conversation_id = data.get('conversation_id')  # Optional for updates
            title = data.get('title')  # Optional, auto-generated if not provided
            
            if not user_email:
                return add_cors_headers({'success': False, 'error': 'user_email required'}, 400)
            if not messages:
                return add_cors_headers({'success': False, 'error': 'messages required'}, 400)
            
            db = get_db()
            import json
            from datetime import datetime
            
            # Generate conversation ID if not provided (new conversation)
            if not conversation_id:
                conversation_id = f"profile_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
            
            # Auto-generate title from first user message if not provided
            if not title and messages:
                for msg in messages:
                    if msg.get('role') == 'user':
                        first_question = msg.get('content', '')[:50]
                        title = first_question + ('...' if len(msg.get('content', '')) > 50 else '')
                        break
            if not title:
                title = f"Self-Discovery {datetime.utcnow().strftime('%b %d')}"
            
            # Preserve created_at if updating existing
            existing = db.get_profile_conversation(user_email, conversation_id)
            created_at = existing.get('created_at') if existing else datetime.utcnow().isoformat()
            
            conversation_data = {
                'conversation_id': conversation_id,
                'title': title,
                'messages': json.dumps(messages),
                'message_count': len(messages),
                'created_at': created_at
            }
            success = db.save_profile_conversation(user_email, conversation_id, conversation_data)
            return add_cors_headers({
                'success': success,
                'conversation_id': conversation_id,
                'title': title
            }, 200 if success else 400)
        
        # --- PROFILE (SELF-DISCOVERY) CHAT LIST ---
        elif resource_type == 'profile-chat-list' and request.method in ['GET', 'POST']:
            if request.method == 'POST':
                data = request.get_json() or {}
            else:
                data = {}
            user_email = data.get('user_email') or request.args.get('user_email') or request.headers.get('X-User-Email')
            limit = int(data.get('limit') or request.args.get('limit') or 20)
            
            if not user_email:
                return add_cors_headers({'success': False, 'error': 'user_email required'}, 400)
            
            db = get_db()
            conversations = db.list_profile_conversations(user_email, limit)
            
            # Format for frontend
            formatted = []
            for conv in conversations:
                formatted.append({
                    'conversation_id': conv.get('conversation_id'),
                    'title': conv.get('title', 'Untitled'),
                    'message_count': conv.get('message_count', 0),
                    'updated_at': conv.get('updated_at'),
                    'created_at': conv.get('created_at')
                })
            
            return add_cors_headers({
                'success': True,
                'conversations': formatted
            })
        
        # --- PROFILE (SELF-DISCOVERY) CHAT LOAD ---
        elif resource_type == 'profile-chat-load' and request.method in ['GET', 'POST']:
            if request.method == 'POST':
                data = request.get_json() or {}
            else:
                data = {}
            user_email = data.get('user_email') or request.args.get('user_email') or request.headers.get('X-User-Email')
            conversation_id = data.get('conversation_id') or request.args.get('conversation_id')
            
            if not user_email or not conversation_id:
                return add_cors_headers({'success': False, 'error': 'user_email and conversation_id required'}, 400)
            
            db = get_db()
            import json
            conversation = db.get_profile_conversation(user_email, conversation_id)
            if conversation:
                messages = json.loads(conversation.get('messages', '[]'))
                return add_cors_headers({
                    'success': True,
                    'conversation': {
                        'conversation_id': conversation.get('conversation_id'),
                        'title': conversation.get('title'),
                        'messages': messages,
                        'message_count': conversation.get('message_count', 0),
                        'updated_at': conversation.get('updated_at'),
                        'created_at': conversation.get('created_at')
                    }
                })
            else:
                return add_cors_headers({
                    'success': False,
                    'error': 'Conversation not found'
                }, 404)
        
        # --- PROFILE (SELF-DISCOVERY) CHAT DELETE ---
        elif resource_type == 'profile-chat-delete' and request.method in ['POST', 'DELETE']:
            data = request.get_json() or {}
            user_email = data.get('user_email') or request.headers.get('X-User-Email')
            conversation_id = data.get('conversation_id')
            
            if not user_email or not conversation_id:
                return add_cors_headers({'success': False, 'error': 'user_email and conversation_id required'}, 400)
            
            db = get_db()
            success = db.delete_profile_conversation(user_email, conversation_id)
            return add_cors_headers({
                'success': success,
                'message': 'Conversation deleted' if success else 'Failed to delete'
            })

        
        # --- UNIVERSITY CHAT SAVE ---
        elif resource_type == 'university-chat-save' and request.method == 'POST':
            data = request.get_json() or {}
            user_email = data.get('user_email') or request.headers.get('X-User-Email')
            university_id = data.get('university_id')
            university_name = data.get('university_name', university_id)
            messages = data.get('messages', [])
            
            if not user_email or not university_id:
                return add_cors_headers({'success': False, 'error': 'user_email and university_id required'}, 400)
            
            db = get_db()
            import json
            conversation_data = {
                'university_name': university_name,
                'messages': json.dumps(messages),
                'message_count': len(messages)
            }
            success = db.save_university_conversation(user_email, university_id, conversation_data)
            return add_cors_headers({
                'success': success,
                'message': 'Conversation saved' if success else 'Failed to save'
            }, 200 if success else 400)
        
        # --- UNIVERSITY CHAT LOAD ---
        elif resource_type == 'university-chat-load' and request.method in ['GET', 'POST']:
            if request.method == 'POST':
                data = request.get_json() or {}
            else:
                data = {}
            user_email = data.get('user_email') or request.args.get('user_email') or request.headers.get('X-User-Email')
            university_id = data.get('university_id') or request.args.get('university_id')
            
            if not user_email or not university_id:
                return add_cors_headers({'success': False, 'error': 'user_email and university_id required'}, 400)
            
            db = get_db()
            import json
            conversation = db.get_university_conversation(user_email, university_id)
            if conversation:
                messages = json.loads(conversation.get('messages', '[]'))
                return add_cors_headers({
                    'success': True,
                    'university_name': conversation.get('university_name'),
                    'messages': messages,
                    'message_count': conversation.get('message_count', 0)
                })
            else:
                return add_cors_headers({
                    'success': True,
                    'messages': [],
                    'message_count': 0
                })
        
        # --- ESSAY COPILOT ---
        elif resource_type == 'generate-essay-starters' and request.method == 'POST':
            data = request.get_json()
            user_email = data.get('user_email') or request.headers.get('X-User-Email')
            university_id = data.get('university_id')
            prompt_text = data.get('prompt_text')
            
            if not user_email or not university_id or not prompt_text:
                return add_cors_headers({'error': 'user_email, university_id, and prompt_text required'}, 400)
            
            result = generate_essay_starters(user_email, university_id, prompt_text)
            return add_cors_headers(result, 200 if result.get('success') else 500)
        
        # Alias for frontend compatibility
        elif resource_type == 'essay-starters' and request.method == 'POST':
            data = request.get_json()
            user_email = data.get('user_email') or request.headers.get('X-User-Email')
            university_id = data.get('university_id')
            prompt_text = data.get('prompt_text')
            notes = data.get('notes', '')
            
            if not user_email or not university_id or not prompt_text:
                return add_cors_headers({'error': 'user_email, university_id, and prompt_text required'}, 400)
            
            result = generate_essay_starters(user_email, university_id, prompt_text, notes)
            return add_cors_headers(result, 200 if result.get('success') else 500)
        
        # Context for selected essay starter
        elif resource_type == 'starter-context' and request.method == 'POST':
            data = request.get_json()
            user_email = data.get('user_email') or request.headers.get('X-User-Email')
            university_id = data.get('university_id')
            selected_hook = data.get('selected_hook')
            prompt_text = data.get('prompt_text')
            
            if not user_email or not university_id or not selected_hook:
                return add_cors_headers({'error': 'user_email, university_id, and selected_hook required'}, 400)
            
            result = get_starter_context(user_email, university_id, selected_hook, prompt_text)
            return add_cors_headers(result, 200 if result.get('success') else 500)
        
        # Essay copilot suggestions
        elif resource_type == 'essay-copilot' and request.method == 'POST':
            data = request.get_json()
            prompt_text = data.get('prompt_text')
            current_text = data.get('current_text', '')
            action = data.get('action', 'suggest')
            
            if not prompt_text:
                return add_cors_headers({'error': 'prompt_text required'}, 400)
            
            result = get_copilot_suggestion(prompt_text, current_text, action)
            return add_cors_headers(result, 200 if result.get('success') else 500)
        
        # Essay feedback
        elif resource_type == 'essay-feedback' and request.method == 'POST':
            data = request.get_json()
            prompt_text = data.get('prompt_text')
            draft_text = data.get('draft_text')
            university_name = data.get('university_name', '')
            
            if not prompt_text or not draft_text:
                return add_cors_headers({'error': 'prompt_text and draft_text required'}, 400)
            
            result = get_draft_feedback(prompt_text, draft_text, university_name)
            return add_cors_headers(result, 200 if result.get('success') else 500)
        
        # Generate essay outline
        elif resource_type == 'generate-outline' and request.method == 'POST':
            data = request.get_json()
            user_email = data.get('user_email') or request.headers.get('X-User-Email')
            university_id = data.get('university_id')
            prompt_text = data.get('prompt_text')
            selected_hook = data.get('selected_hook')
            word_limit = data.get('word_limit')  # Optional
            
            if not user_email or not university_id or not prompt_text:
                return add_cors_headers({'error': 'user_email, university_id, and prompt_text required'}, 400)
            
            result = generate_essay_outline(user_email, university_id, prompt_text, selected_hook, word_limit)
            return add_cors_headers(result, 200 if result.get('success') else 500)
        
        elif resource_type == 'copilot-suggest' and request.method == 'POST':
            data = request.get_json()
            user_email = data.get('user_email') or request.headers.get('X-User-Email')
            university_id = data.get('university_id')
            current_text = data.get('current_text', '')
            
            if not user_email or not university_id:
                return add_cors_headers({'error': 'user_email and university_id required'}, 400)
            
            result = get_copilot_suggestion(user_email, university_id, current_text)
            return add_cors_headers(result, 200 if result.get('success') else 500)
        
        elif resource_type == 'draft-feedback' and request.method == 'POST':
            data = request.get_json()
            user_email = data.get('user_email') or request.headers.get('X-User-Email')
            university_id = data.get('university_id')
            draft_text = data.get('draft_text')
            prompt_text = data.get('prompt_text')
            
            if not user_email or not university_id or not draft_text:
                return add_cors_headers({'error': 'user_email, university_id, and draft_text required'}, 400)
            
            result = get_draft_feedback(user_email, university_id, draft_text, prompt_text)
            return add_cors_headers(result, 200 if result.get('success') else 500)
        
        elif resource_type == 'essay-chat' and request.method == 'POST':
            data = request.get_json()
            user_email = data.get('user_email') or request.headers.get('X-User-Email')
            university_id = data.get('university_id')
            
            # Support both 'question' (frontend) and 'message' (legacy/API)
            user_question = data.get('question') or data.get('message')
            
            # Support both 'current_text' (frontend) and 'draft_text' (legacy)
            current_text = data.get('current_text') or data.get('draft_text', '')
            prompt_text = data.get('prompt_text', '')
            
            if not user_email or not university_id or not user_question:
                return add_cors_headers({'error': 'user_email, university_id, and question required'}, 400)
            
            # Correct argument order: user_email, university_id, prompt_text, current_text, user_question
            result = essay_chat(user_email, university_id, prompt_text, current_text, user_question)
            return add_cors_headers(result, 200 if result.get('success') else 500)
        
        # --- PROFILE CHAT ---
        elif resource_type == 'profile-chat' and request.method == 'POST':
            data = request.get_json() or {}
            user_email = data.get('user_email') or request.headers.get('X-User-Email')
            question = data.get('question', '')
            conversation_history = data.get('conversation_history', [])
            
            if not user_email:
                return add_cors_headers({'success': False, 'error': 'user_email required'}, 400)
            
            result = profile_chat(user_email, question, conversation_history)
            return add_cors_headers(result, 200 if result.get('success') else 500)
        
        elif resource_type == 'save-essay-draft' and request.method == 'POST':
            data = request.get_json()
            user_email = data.get('user_email') or request.headers.get('X-User-Email')
            university_id = data.get('university_id')
            prompt_index = data.get('prompt_index', 0)
            prompt_text = data.get('prompt_text', '')
            draft_text = data.get('draft_text', '')
            notes = data.get('notes', '')
            version = data.get('version', 0)
            version_name = data.get('version_name', '')
            
            if not user_email or not university_id:
                return add_cors_headers({'error': 'user_email and university_id required'}, 400)
            
            result = save_essay_draft(user_email, university_id, prompt_index, prompt_text, draft_text, notes, version, version_name)
            return add_cors_headers(result, 200 if result.get('success') else 500)
        
        elif resource_type == 'get-essay-drafts' and request.method in ['GET', 'POST']:
            if request.method == 'GET':
                user_email = request.args.get('user_email')
                university_id = request.args.get('university_id')
            else:
                data = request.get_json() or {}
                user_email = data.get('user_email') or request.headers.get('X-User-Email')
                university_id = data.get('university_id')
            
            if not user_email:
                return add_cors_headers({'error': 'user_email required'}, 400)
            
            result = get_essay_drafts(user_email, university_id)
            return add_cors_headers(result, 200 if result.get('success') else 500)
        
        elif resource_type == 'get-starter-context' and request.method == 'POST':
            data = request.get_json()
            user_email = data.get('user_email') or request.headers.get('X-User-Email')
            university_id = data.get('university_id')
            
            if not user_email or not university_id:
                return add_cors_headers({'error': 'user_email and university_id required'}, 400)
            
            result = get_starter_context(user_email, university_id)
            return add_cors_headers(result, 200 if result.get('success') else 500)
        
        # --- RESET PROFILE ---
        elif resource_type == 'reset-all-profile' and request.method == 'POST':
            data = request.get_json() or {}
            user_id = data.get('user_email') or data.get('user_id')
            delete_college_list_flag = data.get('delete_college_list', False)
            
            if not user_id:
                return add_cors_headers({'error': 'User email is required'}, 400)
            
            logger.info(f"[RESET_ALL_PROFILE] Starting reset for {user_id}")
            
            deleted_counts = {
                'profile': 0,
                'fits': 0,
                'college_list': 0,
                'files': 0
            }
            
            try:
                # 1. Delete profile document from Firestore
                db = get_db()
                if db.delete_profile(user_id):
                    deleted_counts['profile'] = 1
                    logger.info(f"[RESET_ALL_PROFILE] Deleted profile for {user_id}")
                
                # 2. Delete all GCS files
                files = list_user_files(user_id)
                for file in files:
                    delete_file_from_gcs(user_id, file['filename'])
                    deleted_counts['files'] += 1
                
                # 3. Delete all fit analyses
                fits_list = get_all_fits(user_id)  # Returns list directly
                if fits_list:
                    for fit in fits_list:
                        university_id = fit.get('university_id')
                        if university_id:
                            delete_fit_analysis(user_id, university_id)
                            deleted_counts['fits'] += 1
                
                # 4. Optionally delete college list
                if delete_college_list_flag:
                    list_result = get_college_list(user_id)
                    if list_result.get('success') and list_result.get('universities'):
                        for univ in list_result['universities']:
                            remove_university_from_list(user_id, univ.get('university_id'))
                            deleted_counts['college_list'] += 1
                
                logger.info(f"[RESET_ALL_PROFILE] Reset complete for {user_id}: {deleted_counts}")
                
                return add_cors_headers({
                    'success': True,
                    'deleted': deleted_counts,
                    'message': f"Profile reset complete. Deleted {deleted_counts['profile']} profile(s), {deleted_counts['fits']} fits, {deleted_counts['files']} files, {deleted_counts['college_list']} college list items."
                })
                
            except Exception as e:
                logger.error(f"[RESET_ALL_PROFILE ERROR] {str(e)}")
                return add_cors_headers({
                    'success': False,
                    'error': f'Reset failed: {str(e)}'
                }, 500)
        
        # --- NOT FOUND ---
        else:
            return add_cors_headers({'error': 'Not Found', 'resource': resource_type}, 404)
            
    except Exception as e:
        logger.error(f"[ERROR] {str(e)}", exc_info=True)
        return add_cors_headers({
            'success': False,
            'error': f'Server error: {str(e)}'
        }, 500)
