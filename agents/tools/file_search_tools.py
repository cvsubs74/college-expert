"""
Gemini File Search Tools - Search college admissions knowledge base using File Search API.

Based on: https://ai.google.dev/gemini-api/docs/file-search

NOTE: File Search is only supported with the Gemini Developer API, not Vertex AI.
This requires using the Developer API key, not Vertex AI credentials.
"""
import os
from typing import Dict, Any
from google import genai
from google.genai import types
from .tool_logger import log_tool_call


# Initialize Gemini Developer API client (File Search requires Developer API, not Vertex AI)
# Make sure GEMINI_API_KEY is set to your Developer API key
client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY"),
    http_options={'api_version': 'v1alpha'}  # File Search requires v1alpha
)

# Get the data store name from environment variable
DATA_STORE = os.getenv("DATA_STORE", "college_admissions_kb")


def get_store_name(store_display_name=None):
    """Get the resource name of the File Search store, creating it if it doesn't exist.
    
    Args:
        store_display_name: Optional store name. If not provided, uses DATA_STORE env variable.
    """
    target_store = store_display_name or DATA_STORE
    try:
        # List all stores to find ours
        for store in client.file_search_stores.list():
            if getattr(store, 'display_name', '') == target_store:
                print(f"[STORE] Found store {target_store}: {store.name}")
                return store.name
        
        # Store doesn't exist, create it
        print(f"[STORE] Store {target_store} not found, creating...")
        store = client.file_search_stores.create(
            config={'display_name': target_store}
        )
        print(f"[STORE] Created store: {store.name}")
        return store.name
    except Exception as e:
        print(f"[STORE ERROR] Failed to get/create store: {str(e)}")
        import traceback
        traceback.print_exc()
        raise


@log_tool_call
def search_knowledge_base(
    query: str,
    model: str = "gemini-2.5-flash"
) -> Dict[str, Any]:
    """
    Search the college admissions knowledge base using semantic search.
    
    This function queries the File Search store and returns relevant information
    with citations from the indexed documents. Uses the DATA_STORE environment variable.
    
    Args:
        query: The search query
        model: Gemini model to use (default: gemini-2.5-flash)
        
    Returns:
        Dictionary with search results and citations
        
    Example:
        search_knowledge_base(
            query="What are the key factors in holistic admissions review?"
        )
    """
    try:
        # Get the actual store resource name (not just display name)
        store_name = get_store_name()
        
        response = client.models.generate_content(
            model=model,
            contents=query,
            config=types.GenerateContentConfig(
                tools=[
                    types.Tool(
                        file_search=types.FileSearch(
                            file_search_store_names=[store_name]
                        )
                    )
                ]
            )
        )
        
        # Extract answer
        answer = response.text if hasattr(response, 'text') else str(response)
        
        # Extract citations from grounding metadata
        citations = []
        if hasattr(response, 'candidates') and response.candidates:
            for candidate in response.candidates:
                if hasattr(candidate, 'grounding_metadata'):
                    metadata = candidate.grounding_metadata
                    if hasattr(metadata, 'grounding_chunks'):
                        for chunk in metadata.grounding_chunks:
                            # Try to get citation from retrieved_context first
                            if hasattr(chunk, 'retrieved_context'):
                                ctx = chunk.retrieved_context
                                source = getattr(ctx, 'title', getattr(ctx, 'uri', 'Unknown'))
                                content = getattr(ctx, 'text', '')
                                citations.append({
                                    "source": source,
                                    "content": content[:500] if content else ''  # Limit content length
                                })
                            # Fallback to direct attributes
                            elif hasattr(chunk, 'web') and hasattr(chunk.web, 'uri'):
                                citations.append({
                                    "source": getattr(chunk.web, 'title', chunk.web.uri),
                                    "content": getattr(chunk.web, 'uri', '')
                                })
        
        print(f"[SEARCH] Found answer with {len(citations)} citations")
        if citations:
            print(f"[SEARCH] Sample citation: {citations[0]['source']}")
        
        return {
            "success": True,
            "answer": answer,
            "citations": citations,
            "message": "✅ Search completed successfully"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"❌ Search failed: {str(e)}"
        }


@log_tool_call
def search_user_profile(
    user_email: str,
    query: str = "student academic profile transcript grades courses extracurriculars",
    model: str = "gemini-2.5-flash"
) -> Dict[str, Any]:
    """
    Search a user's specific profile store to retrieve their academic profile.
    
    This function searches the user-specific File Search store and returns the profile content.
    The store name is derived from the user's email: student_profile_<sanitized_email>
    
    Args:
        user_email: The user's email address (e.g., user@gmail.com)
        query: The search query (default: general profile query)
        model: Gemini model to use (default: gemini-2.5-flash)
        
    Returns:
        Dictionary with profile content and metadata
        
    Example:
        search_user_profile(
            user_email="user@gmail.com",
            query="student academic profile"
        )
    """
    try:
        # Sanitize email for store name
        sanitized_email = user_email.replace('@', '_').replace('.', '_').lower()
        user_store_name = f"student_profile_{sanitized_email}"
        
        print(f"[USER_PROFILE] Searching store: {user_store_name} for user: {user_email}")
        
        # Get the actual store resource name
        store_name = get_store_name(user_store_name)
        
        response = client.models.generate_content(
            model=model,
            contents=query,
            config=types.GenerateContentConfig(
                tools=[
                    types.Tool(
                        file_search=types.FileSearch(
                            file_search_store_names=[store_name]
                        )
                    )
                ]
            )
        )
        
        # Extract answer
        answer = response.text if hasattr(response, 'text') else str(response)
        
        # Extract citations
        citations = []
        if hasattr(response, 'candidates') and response.candidates:
            for candidate in response.candidates:
                if hasattr(candidate, 'grounding_metadata'):
                    metadata = candidate.grounding_metadata
                    if hasattr(metadata, 'grounding_chunks'):
                        for chunk in metadata.grounding_chunks:
                            if hasattr(chunk, 'retrieved_context'):
                                ctx = chunk.retrieved_context
                                source = getattr(ctx, 'title', getattr(ctx, 'uri', 'Unknown'))
                                content = getattr(ctx, 'text', '')
                                citations.append({
                                    "source": source,
                                    "content": content
                                })
        
        print(f"[USER_PROFILE] Found profile with {len(citations)} document chunks")
        
        return {
            "success": True,
            "profile_content": answer,
            "citations": citations,
            "user_email": user_email,
            "store_name": user_store_name,
            "message": f"✅ Retrieved profile for {user_email}"
        }
    except Exception as e:
        error_msg = str(e)
        print(f"[USER_PROFILE ERROR] {error_msg}")
        
        # Check if store doesn't exist
        if "not found" in error_msg.lower():
            return {
                "success": False,
                "error": "Profile not found",
                "message": f"❌ No profile found for {user_email}. Please upload your profile in the Student Profile page first.",
                "user_email": user_email
            }
        
        return {
            "success": False,
            "error": error_msg,
            "message": f"❌ Failed to retrieve profile: {error_msg}",
            "user_email": user_email
        }
