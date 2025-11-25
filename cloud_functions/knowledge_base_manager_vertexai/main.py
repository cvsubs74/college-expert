"""
Knowledge Base Manager - Vertex AI RAG
Handles pre-chunked markdown files with context tags.
Parses chunks and uploads to Vertex AI RAG corpus.
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
CORPUS_NAME = 'college-knowledge-base'

# Initialize Vertex AI
vertexai.init(project=PROJECT_ID, location=REGION)

# Global corpus cache
_corpus_cache = None

def get_or_create_corpus():
    """Get or create the knowledge base corpus."""
    global _corpus_cache
    
    if _corpus_cache:
        return _corpus_cache
    
    try:
        # List existing corpora
        corpora = rag.list_corpora()
        
        # Find existing corpus
        for corpus in corpora:
            if corpus.display_name == CORPUS_NAME:
                _corpus_cache = corpus
                logger.info(f"Found existing corpus: {corpus.name}")
                return corpus
        
        # Create new corpus
        logger.info(f"Creating new corpus: {CORPUS_NAME}")
        corpus = rag.create_corpus(
            display_name=CORPUS_NAME,
            description="University knowledge base for college admissions counseling"
        )
        _corpus_cache = corpus
        logger.info(f"Created corpus: {corpus.name}")
        return corpus
        
    except Exception as e:
        logger.error(f"Failed to get/create corpus: {e}")
        raise

def parse_markdown_chunks(markdown_text):
    """
    Parse markdown file into chunks separated by '---'.
    Expected format (UCSB):
    ---
    **Context:** Section context/title
    Content...
    ---
    """
    chunks = []
    
    # Split by '---' separator
    sections = markdown_text.split('\n---\n')
    
    # Process each section
    for i, section in enumerate(sections):
        section = section.strip()
        
        # Skip empty sections
        if not section or section == '---':
            continue
        
        # Extract context line and content
        lines = section.split('\n')
        context = ""
        content_lines = []
        
        for line in lines:
            # Check for **Context:** line
            if line.startswith('**Context:**'):
                context = line.replace('**Context:**', '').strip()
            else:
                content_lines.append(line)
        
        # Combine content
        content = '\n'.join(content_lines).strip()
        
        if content:
            chunks.append({
                'chunk_number': i + 1,
                'title': context or f"Section {i + 1}",
                'content': content
            })
    
    return chunks

def upload_and_index_document(file, filename):
    """Upload markdown document and index chunks in Vertex AI RAG."""
    temp_files = []
    try:
        # Read markdown content
        markdown_text = file.read().decode('utf-8')
        
        # Parse chunks
        chunks = parse_markdown_chunks(markdown_text)
        logger.info(f"Parsed {len(chunks)} chunks from {filename}")
        
        if not chunks:
            raise ValueError("No chunks found in markdown file")
        
        # Get or create corpus
        corpus = get_or_create_corpus()
        
        # Upload each chunk as a separate document to Vertex AI RAG
        for chunk in chunks:
            # Create chunk content with title
            chunk_content = f"Title: {chunk['title']}\n\n{chunk['content']}"
            
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
                            chunk_size=2048,  # Large size since we're already chunked
                            chunk_overlap=0    # No overlap needed
                        )
                    )
                )
                logger.info(f"Uploaded chunk {chunk['chunk_number']} from {filename}")
            except Exception as e:
                logger.error(f"Failed to upload chunk {chunk['chunk_number']}: {e}")
                # Continue with other chunks
        
        return {
            "success": True,
            "filename": filename,
            "chunks_indexed": len(chunks),
            "message": f"Successfully uploaded and indexed {len(chunks)} chunks from {filename}"
        }
        
    except Exception as e:
        logger.error(f"Upload and index failed: {e}", exc_info=True)
        raise
    finally:
        # Clean up temp files
        for temp_path in temp_files:
            if os.path.exists(temp_path):
                os.remove(temp_path)

def list_documents_from_rag():
    """List all documents from Vertex AI RAG corpus."""
    try:
        corpus = get_or_create_corpus()
        
        # List files from RAG corpus
        rag_files = rag.list_files(corpus_name=corpus.name)
        
        documents = []
        seen_base_names = set()
        
        for rag_file in rag_files:
            # Extract base filename (before _chunk_)
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
        
        logger.info(f"Listed {len(documents)} documents from knowledge base")
        return documents
        
    except Exception as e:
        logger.error(f"List documents failed: {e}")
        return []

def delete_document_from_rag(filename):
    """Delete all chunks of a document from Vertex AI RAG corpus."""
    try:
        corpus = get_or_create_corpus()
        
        # List all files in corpus
        rag_files = rag.list_files(corpus_name=corpus.name)
        
        # Find and delete all chunks for this document
        deleted_count = 0
        for rag_file in rag_files:
            # Check if this file belongs to the document
            if rag_file.display_name.startswith(filename):
                rag.delete_file(name=rag_file.name)
                deleted_count += 1
        
        logger.info(f"Deleted {deleted_count} chunks for document: {filename}")
        
        return {
            "success": True,
            "message": f"Successfully deleted {filename} ({deleted_count} chunks)"
        }
        
    except Exception as e:
        logger.error(f"Delete document failed: {e}")
        raise

@functions_framework.http
def knowledge_base_manager_vertexai_http_entry(request: Request):
    """HTTP Cloud Function entry point for knowledge base management."""
    
    # Set CORS headers
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, DELETE, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Cache-Control': 'no-store, no-cache, must-revalidate, proxy-revalidate',
        'Pragma': 'no-cache',
        'Expires': '0'
    }
    
    try:
        # Handle preflight
        if request.method == 'OPTIONS':
            return ('', 204, headers)
        
        # GET - list documents
        if request.method == 'GET':
            documents = list_documents_from_rag()
            return (jsonify({
                'success': True,
                'documents': documents,
                'total': len(documents)
            }), 200, headers)
        
        # POST - upload or delete
        elif request.method == 'POST':
            # Check if this is a delete request
            if request.path.endswith('/delete') or (request.json and 'file_name' in request.json):
                data = request.get_json()
                filename = data.get('file_name') or data.get('name')
                if not filename:
                    return (jsonify({'error': 'file_name required'}), 400, headers)
                
                result = delete_document_from_rag(filename)
                return (jsonify(result), 200, headers)
            
            # Upload request
            elif 'file' in request.files:
                file = request.files['file']
                if file.filename == '':
                    return (jsonify({'error': 'No file selected'}), 400, headers)
                
                if not file.filename.endswith('.md'):
                    return (jsonify({'error': 'Only markdown (.md) files are supported'}), 400, headers)
                
                filename = secure_filename(file.filename)
                result = upload_and_index_document(file, filename)
                
                return (jsonify(result), 200, headers)
            else:
                return (jsonify({'error': 'No file provided'}), 400, headers)
        
        # DELETE - delete document
        elif request.method == 'DELETE':
            data = request.get_json()
            if not data or 'name' not in data:
                return (jsonify({'error': 'Document name required'}), 400, headers)
            
            result = delete_document_from_rag(data['name'])
            return (jsonify(result), 200, headers)
        
        else:
            return (jsonify({'error': 'Method not allowed'}), 405, headers)
            
    except Exception as e:
        logger.error(f"Request failed: {e}", exc_info=True)
        return (jsonify({
            'success': False,
            'error': str(e)
        }), 500, headers)
