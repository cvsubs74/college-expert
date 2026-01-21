
import os
import logging
import json
from datetime import datetime
import functions_framework
from flask import jsonify
import requests

# Import sub-modules
# Import sub-modules
# from planner import generate_roadmap (Imported lazily)
# from list_advisor import analyze_list_balance
# from counselor_chat import handle_chat
# from tools import extract_deadlines

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
PROFILE_MANAGER_URL = os.getenv('PROFILE_MANAGER_URL')

def add_cors_headers(response_data, status_code=200):
    """Add CORS headers to response."""
    if isinstance(response_data, dict):
        response = jsonify(response_data)
    else:
        response = response_data
        
    response.status_code = status_code
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-User-Email'
    return response

@functions_framework.http
def counselor_agent_http(request):
    """Entry point for the Intelligent Counselor Agent."""
    
    # Handle CORS preflight
    if request.method == 'OPTIONS':
        return add_cors_headers({'status': 'ok'}, 200)
        
    try:
        path = request.path.strip('/')
        
        # Dispatcher logic
        if path == 'roadmap':
            # Lazy import to handle cold start errors gracefully
            try:
                from planner import generate_roadmap
                # Call planner logic
                result = generate_roadmap(request)
                
                # Unwrap tuple if present (json, status)
                status = 200
                data = result
                if isinstance(result, tuple):
                    data = result[0]
                    status = result[1]
                    
                # If data is already a Response object (from jsonify), get the json
                if hasattr(data, 'get_json'):
                    try:
                        data = data.get_json()
                    except:
                        pass # keep as is if get_json fails
                
                return add_cors_headers(data, status)
                
            except ImportError as e:
                logger.error(f"Failed to import planner: {e}")
                return add_cors_headers({'error': f"Import Error: {str(e)}"}, 500)
            except Exception as e:
                logger.error(f"Error in planner: {e}")
                return add_cors_headers({'error': str(e)}, 500)
            
        elif path == 'chat':
            try:
                from counselor_chat import chat_with_counselor
                # Call chat logic
                result = chat_with_counselor(request)
                
                # Unwrap tuple if present
                status = 200
                data = result
                if isinstance(result, tuple):
                    data = result[0]
                    status = result[1]
                
                return add_cors_headers(data, status)
                
            except ImportError as e:
                logger.error(f"Failed to import counselor_chat: {e}")
                return add_cors_headers({'error': f"Import Error: {str(e)}"}, 500)
            except Exception as e:
                logger.error(f"Error in chat: {e}")
                return add_cors_headers({'error': str(e)}, 500)
            
        elif path == 'analyze':
            # return analyze_list_balance(request)
            return add_cors_headers({'message': 'Analysis not implemented'}, 501)
        
        elif path == 'mark-task':
            # Persist task completion to Firestore via Profile Manager
            try:
                data = request.get_json() or {}
                user_email = data.get('user_email')
                task_id = data.get('task_id')
                completed = data.get('completed', True)
                
                if not user_email or not task_id:
                    return add_cors_headers({'error': 'user_email and task_id required'}, 400)
                
                # Forward to profile manager for storage
                import requests as http_requests
                pm_url = f"{PROFILE_MANAGER_URL}/update-structured-field"
                result = http_requests.post(pm_url, json={
                    'user_email': user_email,
                    'field_path': f'roadmap_progress.{task_id}',
                    'value': {'completed': completed, 'completed_at': datetime.now().isoformat() if completed else None},
                    'operation': 'set'
                }, timeout=10)
                
                if result.status_code == 200:
                    return add_cors_headers({'success': True, 'task_id': task_id, 'completed': completed})
                else:
                    return add_cors_headers({'success': False, 'error': 'Failed to save task status'}, 500)
                    
            except Exception as e:
                logger.error(f"Error in mark-task: {e}")
                return add_cors_headers({'error': str(e)}, 500)
            
        elif path == 'health':
            return add_cors_headers({'status': 'ok', 'agent': 'counselor_v1', 'upstream': PROFILE_MANAGER_URL})
            
        else:
            return add_cors_headers({'error': f'Unknown path: {path}'}, 404)
            
    except Exception as e:
        logger.error(f"Error in counselor_agent: {e}")
        return add_cors_headers({'error': str(e)}, 500)
