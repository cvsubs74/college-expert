"""
Google Cloud Function for managing student profiles with Firestore.
Version 2 - Migrated from Elasticsearch to Firestore backend.

Clean modular architecture:
- firestore_db.py: Database operations
- profile_extraction.py: Gemini AI processing  
- file_processing.py: PDF/DOCX extraction
- profile_operations.py: Profile CRUD
- college_list.py: College list management
- fit_analysis.py: Fit analysis storage
- credits.py: Credit system
- gcs_storage.py: GCS file operations
"""

import os
import logging
import json
from datetime import datetime
import functions_framework
from flask import Flask, request, jsonify
from flask_cors import CORS

# Import all modules
from firestore_db import get_db
from profile_operations import (
    process_and_index_profile,
    get_student_profile,
    cleanup_profile_on_document_delete
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
from essay_copilot import (
    generate_essay_starters,
    get_copilot_suggestion,
    essay_chat,
    get_draft_feedback,
    save_essay_draft,
    get_essay_drafts,
    get_starter_context,
    fetch_university_profile  # Import from essay_copilot which already has it
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app)

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


# ============== HEALTH & STATUS ==============

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return add_cors_headers({
        'status': 'healthy',
        'service': 'profile_manager_v2',
        'backend': 'firestore',
        'version': '2.0.0'
    })


# ============== PROFILE OPERATIONS ==============

@app.route('/upload-profile', methods=['POST'])
def handle_upload_profile():
    """Upload and process student profile document."""
    try:
        # Get user email from header or form data
        user_email = request.headers.get('X-User-Email') or request.form.get('user_email')
        
        if not user_email:
            return add_cors_headers({'error': 'user_email required'}, 400)
        
        # Get uploaded file
        if 'file' not in request.files:
            return add_cors_headers({'error': 'No file uploaded'}, 400)
        
        file = request.files['file']
        if file.filename == '':
            return add_cors_headers({'error': 'Empty filename'}, 400)
        
        # Read file content
        file_content = file.read()
        filename = file.filename
        content_type = file.content_type
        
        logger.info(f"[UPLOAD] Processing {filename} for {user_email}")
        
        # Process and index
        result = process_and_index_profile(
            user_id=user_email,
            filename=filename,
            file_content=file_content,
            file_metadata={'content_type': content_type}
        )
        
        if result['success']:
            return add_cors_headers(result, 200)
        else:
            return add_cors_headers(result, 500)
            
    except Exception as e:
        logger.error(f"[UPLOAD] Error: {e}")
        return add_cors_headers({'success': False, 'error': str(e)}, 500)


@app.route('/list-profiles', methods=['GET'])
def handle_list_profiles():
    """List user's profile files."""
    try:
        user_email = request.args.get('user_email')
        
        if not user_email:
            return add_cors_headers({'error': 'user_email required'}, 400)
        
        # Get files from GCS
        files = list_user_files(user_email)
        
        return add_cors_headers({
            'success': True,
            'files': files,
            'total': len(files)
        })
        
    except Exception as e:
        logger.error(f"[LIST] Error: {e}")
        return add_cors_headers({'success': False, 'error': str(e)}, 500)


@app.route('/download-document', methods=['GET'])
def handle_download_document():
    """Download profile document from GCS."""
    try:
        user_email = request.args.get('user_email')
        filename = request.args.get('filename')
        
        if not user_email or not filename:
            return add_cors_headers({'error': 'user_email and filename required'}, 400)
        
        # Download from GCS
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
            
    except Exception as e:
        logger.error(f"[DOWNLOAD] Error: {e}")
        return add_cors_headers({'success': False, 'error': str(e)}, 500)


@app.route('/delete-profile', methods=['POST', 'DELETE'])
def handle_delete_profile():
    """Delete profile document."""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_email') or data.get('user_id')
        filename = data.get('filename')
        
        if not user_id or not filename:
            return add_cors_headers({'error': 'user_email and filename required'}, 400)
        
        # Clean up profile in Firestore
        cleanup_profile_on_document_delete(user_id, filename)
        
        # Delete from GCS
        result = delete_file_from_gcs(user_id, filename)
        
        return add_cors_headers(result)
        
    except Exception as e:
        logger.error(f"[DELETE] Error: {e}")
        return add_cors_headers({'success': False, 'error': str(e)}, 500)


@app.route('/search', methods=['POST'])
def handle_search():
    """
    Search/lookup endpoint for backward compatibility.
    Note: This is just a profile lookup, not full-text search.
    """
    try:
        data = request.get_json()
        user_id = data.get('user_email') or data.get('user_id')
        
        if not user_id:
            return add_cors_headers({'error': 'user_email or user_id required'}, 400)
        
        # Get profile from Firestore
        profile = get_student_profile(user_id)
        
        if profile:
            return add_cors_headers({
                'success': True,
                'documents': [{'document': profile}],
                'profiles': [profile],  # Also support profiles format
                'total': 1
            })
        else:
            return add_cors_headers({
                'success': True,
                'documents': [],
                'profiles': [],
                'total': 0
            })
            
    except Exception as e:
        logger.error(f"[SEARCH] Error: {e}")
        return add_cors_headers({'success': False, 'error': str(e)}, 500)


# ============== COLLEGE LIST ==============

@app.route('/add-to-list', methods=['POST'])
def handle_add_to_list():
    """Add university to college list."""
    try:
        data = request.get_json()
        user_email = data.get('user_email')
        university_id = data.get('university_id')
        
        if not user_email or not university_id:
            return add_cors_headers({'error': 'user_email and university_id required'}, 400)
        
        result = add_university_to_list(user_email, university_id, data)
        return add_cors_headers(result)
        
    except Exception as e:
        logger.error(f"[COLLEGE_LIST] Error: {e}")
        return add_cors_headers({'success': False, 'error': str(e)}, 500)


@app.route('/get-list', methods=['GET', 'POST'])
def handle_get_list():
    """Get user's college list."""
    try:
        if request.method == 'POST':
            data = request.get_json()
            user_email = data.get('user_email')
        else:
            user_email = request.args.get('user_email')
        
        if not user_email:
            return add_cors_headers({'error': 'user_email required'}, 400)
        
        colleges = get_college_list(user_email)
        
        return add_cors_headers({
            'success': True,
            'list_items': colleges,
            'total': len(colleges)
        })
        
    except Exception as e:
        logger.error(f"[COLLEGE_LIST] Error: {e}")
        return add_cors_headers({'success': False, 'error': str(e)}, 500)


@app.route('/remove-from-list', methods=['POST', 'DELETE'])
def handle_remove_from_list():
    """Remove university from college list."""
    try:
        data = request.get_json()
        user_email = data.get('user_email')
        university_id = data.get('university_id')
        
        if not user_email or not university_id:
            return add_cors_headers({'error': 'user_email and university_id required'}, 400)
        
        result = remove_university_from_list(user_email, university_id)
        return add_cors_headers(result)
        
    except Exception as e:
        logger.error(f"[COLLEGE_LIST] Error: {e}")
        return add_cors_headers({'success': False, 'error': str(e)}, 500)


@app.route('/update-list-item', methods=['POST'])
def handle_update_list_item():
    """Update college list item."""
    try:
        data = request.get_json()
        user_email = data.get('user_email')
        university_id = data.get('university_id')
        updates = data.get('updates', {})
        
        if not user_email or not university_id:
            return add_cors_headers({'error': 'user_email and university_id required'}, 400)
        
        result = update_list_item(user_email, university_id, updates)
        return add_cors_headers(result)
        
    except Exception as e:
        logger.error(f"[COLLEGE_LIST] Error: {e}")
        return add_cors_headers({'success': False, 'error': str(e)}, 500)


# ============== FIT ANALYSIS ==============

@app.route('/save-fit', methods=['POST'])
def handle_save_fit():
    """Save fit analysis result."""
    try:
        data = request.get_json()
        user_email = data.get('user_email')
        university_id = data.get('university_id')
        fit_data = data.get('fit_data', {})
        
        if not user_email or not university_id:
            return add_cors_headers({'error': 'user_email and university_id required'}, 400)
        
        result = save_fit_analysis(user_email, university_id, fit_data)
        return add_cors_headers(result)
        
    except Exception as e:
        logger.error(f"[FIT_ANALYSIS] Error: {e}")
        return add_cors_headers({'success': False, 'error': str(e)}, 500)


@app.route('/get-fit', methods=['GET', 'POST'])
def handle_get_fit():
    """Get fit analysis for a university."""
    try:
        if request.method == 'POST':
            data = request.get_json()
            user_email = data.get('user_email')
            university_id = data.get('university_id')
        else:
            user_email = request.args.get('user_email')
            university_id = request.args.get('university_id')
        
        if not user_email or not university_id:
            return add_cors_headers({'error': 'user_email and university_id required'}, 400)
        
        fit = get_fit_analysis(user_email, university_id)
        
        if fit:
            return add_cors_headers({
                'success': True,
                'fit': fit
            })
        else:
            return add_cors_headers({
                'success': False,
                'error': 'Fit analysis not found'
            }, 404)
        
    except Exception as e:
        logger.error(f"[FIT_ANALYSIS] Error: {e}")
        return add_cors_headers({'success': False, 'error': str(e)}, 500)


@app.route('/get-all-fits', methods=['GET', 'POST'])
def handle_get_all_fits():
    """Get all fit analyses for a user."""
    try:
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
            'fits': fits,
            'total': len(fits)
        })
        
    except Exception as e:
        logger.error(f"[FIT_ANALYSIS] Error: {e}")
        return add_cors_headers({'success': False, 'error': str(e)}, 500)


# ============== CREDITS ==============

@app.route('/get-credits', methods=['GET', 'POST'])
def handle_get_credits():
    """Get user's credit balance."""
    try:
        if request.method == 'POST':
            data = request.get_json()
            user_email = data.get('user_email')
        else:
            user_email = request.args.get('user_email')
        
        if not user_email:
            return add_cors_headers({'error': 'user_email required'}, 400)
        
        credits = get_user_credits(user_email)
        
        return add_cors_headers({
            'success': True,
            'credits': credits
        })
        
    except Exception as e:
        logger.error(f"[CREDITS] Error: {e}")
        return add_cors_headers({'success': False, 'error': str(e)}, 500)


@app.route('/deduct-credit', methods=['POST'])
def handle_deduct_credit():
    """Deduct credits from user's balance."""
    try:
        data = request.get_json()
        user_email = data.get('user_email')
        credit_count = data.get('credit_count', 1)
        reason = data.get('reason', 'fit_analysis')
        
        if not user_email:
            return add_cors_headers({'error': 'user_email required'}, 400)
        
        result = deduct_credit(user_email, credit_count, reason)
        return add_cors_headers(result)
        
    except Exception as e:
        logger.error(f"[CREDITS] Error: {e}")
        return add_cors_headers({'success': False, 'error': str(e)}, 500)


@app.route('/add-credits', methods=['POST'])
def handle_add_credits():
    """Add credits to user's balance."""
    try:
        data = request.get_json()
        user_email = data.get('user_email')
        credit_count = data.get('credit_count')
        source = data.get('source', 'credit_pack')
        
        if not user_email or not credit_count:
            return add_cors_headers({'error': 'user_email and credit_count required'}, 400)
        
        result = add_credits(user_email, credit_count, source)
        return add_cors_headers(result)
        
    except Exception as e:
        logger.error(f"[CREDITS] Error: {e}")
        return add_cors_headers({'success': False, 'error': str(e)}, 500)


@app.route('/upgrade-subscription', methods=['POST'])
def handle_upgrade_subscription():
    """Upgrade user to pro tier."""
    try:
        data = request.get_json()
        user_email = data.get('user_email')
        subscription_expires = data.get('subscription_expires')
        plan_type = data.get('plan_type', 'monthly')
        
        if not user_email:
            return add_cors_headers({'error': 'user_email required'}, 400)
        
        result = upgrade_subscription(user_email, subscription_expires, plan_type)
        return add_cors_headers(result)
        
    except Exception as e:
        logger.error(f"[CREDITS] Error: {e}")
        return add_cors_headers({'success': False, 'error': str(e)}, 500)


# ============== PROFILE CHAT ==============

@app.route('/profile-chat', methods=['POST'])
def handle_profile_chat():
    """Chat about user's profile."""
    try:
        data = request.get_json()
        user_id = data.get('user_id') or data.get('user_email')
        question = data.get('question') or data.get('message')
        conversation_history = data.get('conversation_history', [])
        
        if not user_id or not question:
            return add_cors_headers({'error': 'user_id and question required'}, 400)
        
        result = profile_chat(user_id, question, conversation_history)
        return add_cors_headers(result)
        
    except Exception as e:
        logger.error(f"[PROFILE_CHAT] Error: {e}")
        return add_cors_headers({'success': False, 'error': str(e)}, 500)


# ============== ESSAY COPILOT ==============

@app.route('/generate-essay-starters', methods=['POST'])
def handle_generate_starters():
    """Generate essay opening suggestions."""
    try:
        data = request.get_json()
        result = generate_essay_starters(
            user_email=data.get('user_email'),
            university_id=data.get('university_id'),
            prompt_text=data.get('prompt_text'),
            notes=data.get('notes', '')
        )
        return add_cors_headers(result)
        
    except Exception as e:
        logger.error(f"[ESSAY_COPILOT] Error: {e}")
        return add_cors_headers({'success': False, 'error': str(e)}, 500)


@app.route('/essay-copilot-suggestion', methods=['POST'])
def handle_copilot_suggestion():
    """Get writing suggestions."""
    try:
        data = request.get_json()
        result = get_copilot_suggestion(
            prompt_text=data.get('prompt_text'),
            current_text=data.get('current_text'),
            action=data.get('action', 'suggest'),
            university_id=data.get('university_id', ''),
            user_email=data.get('user_email', '')
        )
        return add_cors_headers(result)
        
    except Exception as e:
        logger.error(f"[ESSAY_COPILOT] Error: {e}")
        return add_cors_headers({'success': False, 'error': str(e)}, 500)


@app.route('/essay-chat', methods=['POST'])
def handle_essay_chat():
    """Chat about essay context."""
    try:
        data = request.get_json()
        result = essay_chat(
            user_email=data.get('user_email'),
            university_id=data.get('university_id'),
            prompt_text=data.get('prompt_text'),
            current_text=data.get('current_text'),
            user_question=data.get('user_question')
        )
        return add_cors_headers(result)
        
    except Exception as e:
        logger.error(f"[ESSAY_COPILOT] Error: {e}")
        return add_cors_headers({'success': False, 'error': str(e)}, 500)


@app.route('/essay-feedback', methods=['POST'])
def handle_essay_feedback():
    """Get essay draft feedback."""
    try:
        data = request.get_json()
        result = get_draft_feedback(
            prompt_text=data.get('prompt_text'),
            draft_text=data.get('draft_text'),
            university_name=data.get('university_name', '')
        )
        return add_cors_headers(result)
        
    except Exception as e:
        logger.error(f"[ESSAY_COPILOT] Error: {e}")
        return add_cors_headers({'success': False, 'error': str(e)}, 500)


@app.route('/save-essay-draft', methods=['POST'])
def handle_save_essay_draft():
    """Save essay draft."""
    try:
        data = request.get_json()
        result = save_essay_draft(
            user_email=data.get('user_email'),
            university_id=data.get('university_id'),
            prompt_index=data.get('prompt_index', 0),
            prompt_text=data.get('prompt_text', ''),
            draft_text=data.get('draft_text', ''),
            notes=data.get('notes', []),
            version=data.get('version', 0),
            version_name=data.get('version_name', '')
        )
        return add_cors_headers(result)
        
    except Exception as e:
        logger.error(f"[ESSAY_COPILOT] Error: {e}")
        return add_cors_headers({'success': False, 'error': str(e)}, 500)


@app.route('/get-essay-drafts', methods=['POST', 'GET'])
def handle_get_essay_drafts():
    """Get essay drafts."""
    try:
        if request.method == 'POST':
            data = request.get_json()
            user_email = data.get('user_email')
            university_id = data.get('university_id')
        else:
            user_email = request.args.get('user_email')
            university_id = request.args.get('university_id')
        
        if not user_email:
            return add_cors_headers({'error': 'user_email required'}, 400)
        
        result = get_essay_drafts(user_email, university_id)
        return add_cors_headers(result)
        
    except Exception as e:
        logger.error(f"[ESSAY_COPILOT] Error: {e}")
        return add_cors_headers({'success': False, 'error': str(e)}, 500)


@app.route('/save-onboarding-profile', methods=['POST'])
def handle_save_onboarding_profile():
    """
    Save initial profile from onboarding wizard.
    Creates a structured profile from onboarding form data.
    """
    try:
        data = request.get_json()
        user_email = data.get('user_email')
        profile_data = data.get('profile_data', {})
        
        if not user_email:
            return add_cors_headers({'error': 'user_email required'}, 400)
        
        # Build structured profile from onboarding data
        structured_profile = {
            'name': profile_data.get('name', ''),
            'school': profile_data.get('school', ''),
            'grade': profile_data.get('grade', ''),
            'graduation_year': profile_data.get('graduation_year'),
            'intended_major': profile_data.get('intended_major', ''),
            'gpa_unweighted': profile_data.get('gpa', {}).get('unweighted'),
            'gpa_weighted': profile_data.get('gpa', {}).get('weighted'),
            'sat_total': profile_data.get('sat', {}).get('total'),
            'sat_math': profile_data.get('sat', {}).get('math'),
            'sat_reading': profile_data.get('sat', {}).get('reading'),
            'act_composite': profile_data.get('act', {}).get('composite'),
            'extracurriculars': profile_data.get('extracurriculars', []),
            'awards': profile_data.get('awards', []),
            'leadership_roles': profile_data.get('leadership', []),
            'academic_interests': profile_data.get('interests', []),
        }
        
        # Save directly to Firestore
        db = get_db()
        
        # Build complete document
        document = {
            'user_id': user_email,
            'indexed_at': datetime.utcnow().isoformat(),
            'source': 'onboarding_wizard',
            **structured_profile
        }
        
        success = db.save_profile(user_email, document, merge=True)
        
        if success:
            logger.info(f"[ONBOARDING] Saved onboarding profile for {user_email}")
            return add_cors_headers({
                'success': True,
                'message': 'Onboarding profile saved'
            })
        else:
            return add_cors_headers({
                'success': False,
                'error': 'Failed to save onboarding profile'
            }, 500)
        
    except Exception as e:
        logger.error(f"[ONBOARDING] Error: {e}")
        return add_cors_headers({'success': False, 'error': str(e)}, 500)


@app.route('/compute-single-fit', methods=['POST'])
def handle_compute_single_fit():
    """
    Compute fit analysis for a single university.
    This is the main fit computation endpoint used by the frontend.
    Uses EXACT logic from profile_manager_es adapted for Firestore.
    """
    try:
        from fit_computation import calculate_fit_for_college
        
        data = request.get_json()
        user_email = data.get('user_email')
        university_id = data.get('university_id')
        force_recompute = data.get('force_recompute', False)
        
        if not user_email or not university_id:
            return add_cors_headers({
                'error': 'user_email and university_id required'
            }, 400)
        
        # Check for cached fit analysis unless force recompute
        if not force_recompute:
            existing_fit = get_fit_analysis(user_email, university_id)
            if existing_fit:
                logger.info(f"[FIT] Returning cached fit for {university_id}")
                return add_cors_headers({
                    'success': True,
                    'fit': existing_fit,
                    'fit_analysis': existing_fit,  # ES format compatibility
                    'from_cache': True
                })
        
        # Check credits
        credit_check = check_credits_available(user_email, credits_needed=1)
        if not credit_check['has_credits']:
            logger.warning(f"[FIT] Insufficient credits for {user_email}")
            return add_cors_headers({
                'success': False,
                'error': 'insufficient_credits',
                'message': 'You need more credits to run fit analysis',
                'credits_remaining': credit_check['credits_remaining'],
                'upgrade_required': True
            }, 402)  # Payment Required
        
        # Get user profile
        profile = get_student_profile(user_email)
        if not profile:
            return add_cors_headers({
                'success': False,
                'error': 'No profile found. Please upload your profile first.'
            }, 404)
        
        # Get intended major from request or profile
        intended_major = data.get('intended_major', '') or profile.get('intended_major', '')
        
        # Compute fit using EXACT ES logic
        logger.info(f"[FIT] Computing fit for {university_id}")
        fit_analysis = calculate_fit_for_college(user_email, university_id, intended_major)
        
        if not fit_analysis:
            return add_cors_headers({
                'success': False,
                'error': 'Failed to compute fit analysis',
                'university_id': university_id
            }, 500)
        
        # Save fit analysis to Firestore
        save_result = save_fit_analysis(user_email, university_id, fit_analysis)
        
        if not save_result['success']:
            logger.warning(f"[FIT] Failed to save fit analysis: {save_result}")
        
        # Deduct credit AFTER successful computation
        deduct_credit(user_email, credit_count=1, reason=f'fit_analysis_{university_id}')
        
        logger.info(f"[FIT] Result: {fit_analysis.get('fit_category')} ({fit_analysis.get('match_percentage')}%)")
        
        return add_cors_headers({
            'success': True,
            'university_id': university_id,
            'university_name': fit_analysis.get('university_name', university_id),
            'fit_analysis': fit_analysis,
            'fit': fit_analysis,  # Also include for compatibility
            'from_cache': False
        })
        
    except Exception as e:
        logger.error(f"[FIT] Error: {e}", exc_info=True)
        return add_cors_headers({'success': False, 'error': str(e)}, 500)


# ============== CLOUD FUNCTIONS ENTRY POINT ==============

@functions_framework.http
def profile_manager_v2_http_entry(request):
    """Cloud Functions HTTP entry point."""
    # Handle CORS preflight
    if request.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, DELETE, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, X-User-Email',
            'Access-Control-Max-Age': '3600'
        }
        return ('', 204, headers)
    
    # Process request with Flask app
    with app.request_context(request.environ):
        try:
            response = app.full_dispatch_request()
            return response
        except Exception as e:
            logger.error(f"[ERROR] Request failed: {e}", exc_info=True)
            return jsonify({'success': False, 'error': str(e)}), 500


if __name__ == '__main__':
    # For local testing
    app.run(host='0.0.0.0', port=8080, debug=True)
