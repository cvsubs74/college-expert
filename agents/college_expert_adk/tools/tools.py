"""
ADK RAG Agent Tools
Tools for searching Vertex AI RAG corpora.
Search capabilities for both knowledge base and user profiles.
"""
import os
import logging
from typing import Dict, Any, Optional
import vertexai
from vertexai import rag
import tempfile
import base64

logger = logging.getLogger(__name__)

# --- Configuration ---
PROJECT_ID = os.environ.get('GCP_PROJECT_ID', 'college-counselling-478115')
REGION = os.environ.get('REGION', 'us-east1')

# Initialize Vertex AI
vertexai.init(project=PROJECT_ID, location=REGION)

# Corpus names
KNOWLEDGE_BASE_CORPUS = "college-knowledge-base"
PROFILE_CORPUS_PREFIX = "profile_"

# Global corpus cache
_corpora_cache = {}

# --- Corpus Management ---
def get_or_create_corpus(corpus_name: str, description: str = "") -> Any:
    """Get or create a Vertex AI RAG corpus."""
    global _corpora_cache
    
    if corpus_name in _corpora_cache:
        return _corpora_cache[corpus_name]
    
    try:
        # List existing corpora
        corpora = rag.list_corpora()
        
        # Find existing corpus
        for corpus in corpora:
            if corpus.display_name == corpus_name:
                _corpora_cache[corpus_name] = corpus
                logger.info(f"Found existing corpus: {corpus.name}")
                return corpus
        
        # Create new corpus
        logger.info(f"Creating new corpus: {corpus_name}")
        corpus = rag.create_corpus(
            display_name=corpus_name,
            description=description or f"RAG corpus: {corpus_name}"
        )
        _corpora_cache[corpus_name] = corpus
        logger.info(f"Created corpus: {corpus.name}")
        return corpus
        
    except Exception as e:
        logger.error(f"Failed to get/create corpus: {e}")
        raise

def get_user_corpus_name(user_email: str) -> str:
    """Generate corpus name for user profiles."""
    sanitized_email = user_email.replace('@', '_').replace('.', '_').lower()
    return f"{PROFILE_CORPUS_PREFIX}{sanitized_email}"

# --- Upload Tools ---
def upload_document_to_knowledge_base(
    filename: str,
    file_content_base64: str,
    model: str = "gemini-2.5-flash"
) -> Dict[str, Any]:
    """
    Upload a document to the knowledge base corpus.
    
    Args:
        filename: Name of the file
        file_content_base64: Base64 encoded file content
        model: Model name (not used, for compatibility)
    
    Returns:
        Dict with success status and message
    """
    try:
        # Get or create knowledge base corpus
        corpus = get_or_create_corpus(
            KNOWLEDGE_BASE_CORPUS,
            "University knowledge base for college admissions counseling"
        )
        
        # Decode file content
        file_content = base64.b64decode(file_content_base64)
        
        # Save to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{filename}") as tmp_file:
            tmp_file.write(file_content)
            tmp_path = tmp_file.name
        
        try:
            # Import file to corpus
            response = rag.import_files(
                corpus_name=corpus.name,
                paths=[tmp_path],
                chunk_size=1024,
                chunk_overlap=200
            )
            
            logger.info(f"Uploaded document to knowledge base: {filename}")
            
            return {
                "success": True,
                "message": f"✅ Successfully uploaded {filename} to knowledge base",
                "filename": filename,
                "corpus_name": corpus.name
            }
            
        finally:
            # Clean up temp file
            import os as os_module
            if os_module.path.exists(tmp_path):
                os_module.remove(tmp_path)
        
    except Exception as e:
        logger.error(f"Failed to upload document: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": f"❌ Failed to upload {filename}: {str(e)}"
        }

def upload_profile(
    user_email: str,
    filename: str,
    file_content_base64: str,
    model: str = "gemini-2.5-flash"
) -> Dict[str, Any]:
    """
    Upload a student profile to user-specific corpus.
    
    Args:
        user_email: User's email address
        filename: Name of the profile file
        file_content_base64: Base64 encoded file content
        model: Model name (not used, for compatibility)
    
    Returns:
        Dict with success status and message
    """
    try:
        # Get or create user corpus
        corpus_name = get_user_corpus_name(user_email)
        corpus = get_or_create_corpus(
            corpus_name,
            f"Student profile corpus for {user_email}"
        )
        
        # Decode file content
        file_content = base64.b64decode(file_content_base64)
        
        # Save to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{filename}") as tmp_file:
            tmp_file.write(file_content)
            tmp_path = tmp_file.name
        
        try:
            # Import file to corpus
            response = rag.import_files(
                corpus_name=corpus.name,
                paths=[tmp_path],
                chunk_size=1024,
                chunk_overlap=200
            )
            
            logger.info(f"Uploaded profile for {user_email}: {filename}")
            
            return {
                "success": True,
                "message": f"✅ Successfully uploaded profile {filename}",
                "filename": filename,
                "user_email": user_email,
                "corpus_name": corpus.name
            }
            
        finally:
            # Clean up temp file
            import os as os_module
            if os_module.path.exists(tmp_path):
                os_module.remove(tmp_path)
        
    except Exception as e:
        logger.error(f"Failed to upload profile: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": f"❌ Failed to upload profile {filename}: {str(e)}"
        }

# --- Search Tools ---
def search_knowledge_base(
    query: str,
    model: str = "gemini-2.5-flash"
) -> Dict[str, Any]:
    """
    Search the knowledge base corpus using Vertex AI RAG.
    
    Args:
        query: Search query
        model: Model name (not used, for compatibility)
    
    Returns:
        Dict with search results and citations
    """
    try:
        # Get knowledge base corpus
        corpus = get_or_create_corpus(
            KNOWLEDGE_BASE_CORPUS,
            "University knowledge base for college admissions counseling"
        )
        
        # Configure retrieval parameters (aligned with reference implementation)
        rag_retrieval_config = rag.RagRetrievalConfig(
            top_k=10,  # Return top 10 results
            filter=rag.Filter(vector_distance_threshold=0.5)  # Similarity threshold
        )
        
        # Query the corpus
        response = rag.retrieval_query(
            rag_resources=[
                rag.RagResource(
                    rag_corpus=corpus.name,
                )
            ],
            text=query,
            rag_retrieval_config=rag_retrieval_config
        )
        
        # Format results (aligned with reference implementation)
        documents = []
        citations = []
        
        if hasattr(response, 'contexts') and response.contexts:
            for context in response.contexts.contexts:
                # Extract source information
                source_uri = context.source_uri if hasattr(context, 'source_uri') else ""
                source_name = context.source_display_name if hasattr(context, 'source_display_name') else ""
                text = context.text if hasattr(context, 'text') else ""
                score = context.score if hasattr(context, 'score') else 0.0
                
                doc = {
                    "id": source_uri or "unknown",
                    "score": score,
                    "filename": source_name or (source_uri.split('/')[-1] if source_uri else "unknown"),
                    "title": source_name or (source_uri.split('/')[-1] if source_uri else "unknown"),
                    "content": text,
                    "source_uri": source_uri,
                    "metadata": {}
                }
                documents.append(doc)
                
                # Add citation
                citations.append({
                    "source": doc["filename"],
                    "text": text[:200] + "..." if len(text) > 200 else text
                })
        
        # Return results
        if not documents:
            return {
                "success": True,
                "documents": [],
                "total_found": 0,
                "query": query,
                "answer": f"No results found in knowledge base for query: '{query}'",
                "citations": []
            }
        
        return {
            "success": True,
            "documents": documents,
            "total_found": len(documents),
            "query": query,
            "answer": f"Found {len(documents)} relevant documents in knowledge base",
            "citations": citations[:3]
        }
        
    except Exception as e:
        logger.error(f"Knowledge base search failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": f"❌ Knowledge base search failed: {str(e)}",
            "documents": []
        }

def search_user_profile(
    user_email: str,
    query: str = "student academic profile",
    model: str = "gemini-2.5-flash"
) -> Dict[str, Any]:
    """
    Search user's profile corpus using Vertex AI RAG.
    
    Args:
        user_email: User's email address
        query: Search query
        model: Model name (not used, for compatibility)
    
    Returns:
        Dict with search results and profile data
    """
    try:
        # Get user corpus
        corpus_name = get_user_corpus_name(user_email)
        corpus = get_or_create_corpus(
            corpus_name,
            f"Student profile corpus for {user_email}"
        )
        
        # Configure retrieval parameters (aligned with reference implementation)
        rag_retrieval_config = rag.RagRetrievalConfig(
            top_k=5,  # Return top 5 results for profiles
            filter=rag.Filter(vector_distance_threshold=0.5)  # Similarity threshold
        )
        
        # Query the corpus
        response = rag.retrieval_query(
            rag_resources=[
                rag.RagResource(
                    rag_corpus=corpus.name,
                )
            ],
            text=query,
            rag_retrieval_config=rag_retrieval_config
        )
        
        # Format results (aligned with reference implementation)
        documents = []
        profile_data = ""
        
        if hasattr(response, 'contexts') and response.contexts:
            for context in response.contexts.contexts:
                # Extract source information
                source_uri = context.source_uri if hasattr(context, 'source_uri') else ""
                source_name = context.source_display_name if hasattr(context, 'source_display_name') else ""
                text = context.text if hasattr(context, 'text') else ""
                score = context.score if hasattr(context, 'score') else 0.0
                
                doc = {
                    "id": source_uri or "unknown",
                    "score": score,
                    "filename": source_name or (source_uri.split('/')[-1] if source_uri else "unknown"),
                    "title": source_name or (source_uri.split('/')[-1] if source_uri else "unknown"),
                    "content": text,
                    "source_uri": source_uri,
                    "metadata": {}
                }
                documents.append(doc)
                
                # Accumulate profile data
                if not profile_data:
                    profile_data = text
        
        # Return results
        if not documents:
            return {
                "success": True,
                "documents": [],
                "total_found": 0,
                "user_email": user_email,
                "answer": f"No profile data found for {user_email}. Please upload a profile first.",
                "profile_data": "No profile data found"
            }
        
        return {
            "success": True,
            "documents": documents,
            "total_found": len(documents),
            "user_email": user_email,
            "answer": f"Found {len(documents)} profile documents for {user_email}",
            "profile_data": profile_data or "No profile data found"
        }
        
    except Exception as e:
        logger.error(f"Profile search failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": f"❌ Profile search failed: {str(e)}",
            "documents": []
        }

# --- List Tools ---
def list_knowledge_base_documents(
    user_email: str = "anonymous",
    model: str = "gemini-2.5-flash"
) -> Dict[str, Any]:
    """
    List all documents in the knowledge base corpus.
    
    Args:
        user_email: User email (not used, for compatibility)
        model: Model name (not used, for compatibility)
    
    Returns:
        Dict with list of documents
    """
    try:
        # Get knowledge base corpus
        corpus = get_or_create_corpus(
            KNOWLEDGE_BASE_CORPUS,
            "University knowledge base for college admissions counseling"
        )
        
        # List files in corpus
        files = rag.list_files(corpus_name=corpus.name)
        
        # Format documents
        documents = []
        for file in files:
            documents.append({
                "name": file.name,
                "display_name": file.display_name,
                "size_bytes": 0,  # Vertex AI doesn't provide size
                "mime_type": "application/pdf",  # Default
                "size": 0
            })
        
        return {
            "success": True,
            "documents": documents,
            "total": len(documents)
        }
        
    except Exception as e:
        logger.error(f"List documents failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "documents": []
        }

def list_user_profiles(
    user_email: str,
    model: str = "gemini-2.5-flash"
) -> Dict[str, Any]:
    """
    List all profiles for a user.
    
    Args:
        user_email: User's email address
        model: Model name (not used, for compatibility)
    
    Returns:
        Dict with list of profiles
    """
    try:
        # Get user corpus
        corpus_name = get_user_corpus_name(user_email)
        corpus = get_or_create_corpus(
            corpus_name,
            f"Student profile corpus for {user_email}"
        )
        
        # List files in corpus
        files = rag.list_files(corpus_name=corpus.name)
        
        # Format documents
        documents = []
        for file in files:
            documents.append({
                "name": file.name,
                "display_name": file.display_name,
                "size_bytes": 0,
                "mime_type": "application/pdf",
                "size": 0
            })
        
        return {
            "success": True,
            "documents": documents,
            "total": len(documents)
        }
        
    except Exception as e:
        logger.error(f"List profiles failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "documents": []
        }

# --- Delete Tools ---
def delete_knowledge_base_document(
    document_name: str,
    user_email: str = "anonymous",
    model: str = "gemini-2.5-flash"
) -> Dict[str, Any]:
    """
    Delete a document from the knowledge base corpus.
    
    Args:
        document_name: Name/ID of the document to delete
        user_email: User email (not used, for compatibility)
        model: Model name (not used, for compatibility)
    
    Returns:
        Dict with success status
    """
    try:
        # Delete file from corpus
        rag.delete_file(name=document_name)
        
        logger.info(f"Deleted document: {document_name}")
        
        return {
            "success": True,
            "message": f"Successfully deleted {document_name}"
        }
        
    except Exception as e:
        logger.error(f"Delete document failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to delete {document_name}"
        }

def delete_user_profile(
    document_name: str,
    user_email: str,
    model: str = "gemini-2.5-flash"
) -> Dict[str, Any]:
    """
    Delete a profile from user's corpus.
    
    Args:
        document_name: Name/ID of the profile to delete
        user_email: User's email address
        model: Model name (not used, for compatibility)
    
    Returns:
        Dict with success status
    """
    try:
        # Delete file from corpus
        rag.delete_file(name=document_name)
        
        logger.info(f"Deleted profile for {user_email}: {document_name}")
        
        return {
            "success": True,
            "message": f"Successfully deleted profile {document_name}"
        }
        
    except Exception as e:
        logger.error(f"Delete profile failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to delete profile {document_name}"
        }
