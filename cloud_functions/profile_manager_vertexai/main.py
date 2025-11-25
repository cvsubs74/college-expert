"""
Profile Manager - Vertex AI RAG
Handles pre-chunked markdown profile files with context tags.
Parses chunks and uploads to user-specific Vertex AI RAG corpus.
"""
import os
import logging
import tempfile
import re
import functions_framework
from flask import Request, jsonify
import vertexai
from vertexai import rag
from werkzeug.utils import secure_filename

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
PROJECT_ID = os.environ.get('GCP_PROJECT_ID', 'college-counselling-478115')
REGION = os.environ.get('REGION', 'us-east1')
PROFILE_CORPUS_PREFIX = 'profile_'

# Initialize Vertex AI
vertexai.init(project=PROJECT_ID, location=REGION)

# Global corpus cache per user
_corpus_cache = {}

def get_user_corpus_name(user_email):
    """Generate corpus name for user profiles."""
    sanitized_email = user_email.replace('@', '_').replace('.', '_').lower()
    return f"{PROFILE_CORPUS_PREFIX}{sanitized_email}"

def get_or_create_user_corpus(user_email):
    """Get or create a Vertex AI RAG corpus for a specific user."""
    global _corpus_cache
    
    corpus_name = get_user_corpus_name(user_email)
    
    if corpus_name in _corpus_cache:
        return _corpus_cache[corpus_name]
    
    try:
        # List existing corpora
        corpora = rag.list_corpora()
        
        # Find existing corpus
        for corpus in corpora:
            if corpus.display_name == corpus_name:
                _corpus_cache[corpus_name] = corpus
                logger.info(f"Found existing corpus: {corpus.name}")
                return corpus
        
        # Create new corpus
        logger.info(f"Creating new corpus: {corpus_name}")
        corpus = rag.create_corpus(
            display_name=corpus_name,
            description=f"Student profile corpus for {user_email}"
        )
        _corpus_cache[corpus_name] = corpus
        logger.info(f"Created corpus: {corpus.name}")
        return corpus
        
    except Exception as e:
        logger.error(f"Failed to get/create corpus: {e}")
        raise

def parse_markdown_chunks(markdown_text):
    """
    Parse markdown file into chunks.
    Expected format:
    ### Chunk 1
    **Context Tag:** [context]
    **Content:**
    [content]
    ---
    """
    chunks = []
    
    # Split by chunk headers
    chunk_pattern = r'###\s+Chunk\s+(\d+)'
    chunk_splits = re.split(chunk_pattern, markdown_text)
    
    # First element is header/intro, skip it
    for i in range(1, len(chunk_splits), 2):
        chunk_number = int(chunk_splits[i])
        chunk_text = chunk_splits[i+1] if i+1 < len(chunk_splits) else ""
        
        # Extract context tag
        context_match = re.search(r'\*\*Context Tag:\*\*\s*(.+?)(?:\n|$)', chunk_text, re.IGNORECASE)
        context_tag = context_match.group(1).strip() if context_match else ""
        
        # Extract content
        content_match = re.search(r'\*\*Content:\*\*\s*(.+?)(?:---|\Z)', chunk_text, re.DOTALL | re.IGNORECASE)
        content = content_match.group(1).strip() if content_match else chunk_text.strip()
        
        # Remove overlap markers
        content = re.sub(r'\*\*\[Overlap from Previous Chunk\]\*\*.*?\*\*\[End Overlap\]\*\*', '', content, flags=re.DOTALL)
        content = content.strip()
        
        if content:
            chunks.append({
                'chunk_number': chunk_number,
                'context_tag': context_tag,
                'content': content
            })
    
    return chunks

def upload_and_index_profile(file, filename, user_email):
    """Upload markdown profile and index chunks in user's Vertex AI RAG corpus."""
    temp_files = []
    try:
        # Read markdown content
        markdown_text = file.read().decode('utf-8')
        
        # Parse chunks
        chunks = parse_markdown_chunks(markdown_text)
        logger.info(f"Parsed {len(chunks)} chunks from {filename}")
        
        if not chunks:
            raise ValueError("No chunks found in markdown file")
        
        # Get or create user corpus
        corpus = get_or_create_user_corpus(user_email)
        
        # Upload each chunk as a separate document
        for chunk in chunks:
            # Create chunk content with context tag
            chunk_content = f"Context: {chunk['context_tag']}\n\n{chunk['content']}"
            
            # Create temp file for this chunk
            chunk_filename = f"{filename}_chunk_{chunk['chunk_number']}.txt"
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt', encoding='utf-8') as tmp_file:
                tmp_file.write(chunk_content)
                temp_path = tmp_file.name
                temp_files.append(temp_path)
            
            # Import this chunk to Vertex AI RAG
            try:
                rag.import_files(
                    corpus.name,
                    [temp_path],
                    transformation_config=rag.TransformationConfig(
                        chunking_config=rag.ChunkingConfig(
                            chunk_size=2048,
                            chunk_overlap=0
                        )
                    )
                )
                logger.info(f"Uploaded chunk {chunk['chunk_number']} from {filename} for {user_email}")
            except Exception as e:
                logger.error(f"Failed to upload chunk {chunk['chunk_number']}: {e}")
        
        return {
            "success": True,
            "filename": filename,
            "chunks_indexed": len(chunks),
            "message": f"Successfully uploaded profile {filename}"
        }
        
    except Exception as e:
        logger.error(f"Upload and index failed: {e}", exc_info=True)
        raise
    finally:
        # Clean up temp files
        for temp_path in temp_files:
            if os.path.exists(temp_path):
                os.remove(temp_path)

def list_profiles_from_rag(user_email):
    """List all profiles from user's Vertex AI RAG corpus."""
    try:
        corpus = get_or_create_user_corpus(user_email)
        
        # List files from RAG corpus
        rag_files = rag.list_files(corpus_name=corpus.name)
        
        documents = []
        seen_base_names = set()
        
        for rag_file in rag_files:
            # Extract base filename
            display_name = rag_file.display_name
            base_name = re.sub(r'_chunk_\d+\.txt$', '', display_name)
            
            # Only add unique base names
            if base_name not in seen_base_names and not base_name.endswith('.txt'):
                seen_base_names.add(base_name)
                documents.append({
                    'name': base_name,
                    'display_name': base_name,
                    'size_bytes': 0,
                    'mime_type': 'text/markdown',
                    'size': 0
                })
        
        logger.info(f"Listed {len(documents)} profiles for {user_email}")
        return documents
        
    except Exception as e:
        logger.error(f"List profiles failed: {e}")
        return []

def delete_profile_from_rag(filename, user_email):
    """Delete all chunks of a profile from user's Vertex AI RAG corpus."""
    try:
        corpus = get_or_create_user_corpus(user_email)
        
        # List all files in corpus
        rag_files = rag.list_files(corpus_name=corpus.name)
        
        # Find and delete all chunks for this profile
        deleted_count = 0
        for rag_file in rag_files:
            if rag_file.display_name.startswith(filename):
                rag.delete_file(name=rag_file.name)
                deleted_count += 1
        
        logger.info(f"Deleted {deleted_count} chunks for profile: {filename} for {user_email}")
        
        return {
            "success": True,
            "message": f"Successfully deleted profile {filename}"
        }
        
    except Exception as e:
        logger.error(f"Delete profile failed: {e}")
        raise

@functions_framework.http
def profile_manager_vertexai_http_entry(request: Request):
    """HTTP Cloud Function entry point for profile management."""
    
    # Set CORS headers
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, DELETE, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, X-User-Email',
        'Cache-Control': 'no-store, no-cache, must-revalidate, proxy-revalidate',
        'Pragma': 'no-cache',
        'Expires': '0'
    }
    
    try:
        # Handle preflight
        if request.method == 'OPTIONS':
            return ('', 204, headers)
        
        # Get user email from header
        user_email = request.headers.get('X-User-Email')
        if not user_email:
            return (jsonify({'error': 'X-User-Email header required'}), 400, headers)
        
        # GET - list profiles
        if request.method == 'GET':
            documents = list_profiles_from_rag(user_email)
            return (jsonify({
                'success': True,
                'documents': documents,
                'total': len(documents)
            }), 200, headers)
        
        # POST - upload or delete
        elif request.method == 'POST':
            # Check if this is a delete request
            if request.path.endswith('/delete-profile') or (request.json and 'file_name' in request.json):
                data = request.get_json()
                filename = data.get('file_name') or data.get('name')
                if not filename:
                    return (jsonify({'error': 'file_name required'}), 400, headers)
                
                result = delete_profile_from_rag(filename, user_email)
                return (jsonify(result), 200, headers)
            
            # Upload request
            elif 'file' in request.files:
                file = request.files['file']
                if file.filename == '':
                    return (jsonify({'error': 'No file selected'}), 400, headers)
                
                if not file.filename.endswith('.md'):
                    return (jsonify({'error': 'Only markdown (.md) files are supported'}), 400, headers)
                
                filename = secure_filename(file.filename)
                result = upload_and_index_profile(file, filename, user_email)
                
                return (jsonify(result), 200, headers)
            else:
                return (jsonify({'error': 'No file provided'}), 400, headers)
        
        # DELETE - delete profile
        elif request.method == 'DELETE':
            data = request.get_json()
            if not data or 'name' not in data:
                return (jsonify({'error': 'Profile name required'}), 400, headers)
            
            result = delete_profile_from_rag(data['name'], user_email)
            return (jsonify(result), 200, headers)
        
        else:
            return (jsonify({'error': 'Method not allowed'}), 405, headers)
            
    except Exception as e:
        logger.error(f"Request failed: {e}", exc_info=True)
        return (jsonify({
            'success': False,
            'error': str(e)
        }), 500, headers)
