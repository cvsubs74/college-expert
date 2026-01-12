"""
Minimal test version of Profile Manager V2 for debugging deployment issues.
ONLY includes health endpoint to test container startup.
"""

import logging
import functions_framework
from flask import Flask, jsonify

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

logger.info("[INIT] MINIMAL Profile Manager V2 starting...")

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'service': 'profile_manager_v2_minimal',
        'version': '2.0.0-test'
    })

# Cloud Functions entry point
@functions_framework.http
def profile_manager_v2_http_entry(request):
    """Cloud Functions HTTP entry point."""
    logger.info(f"[REQUEST] {request.method} {request.path}")
    
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
    app.run(host='0.0.0.0', port=8080, debug=True)
