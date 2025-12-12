import os
import logging
from google import genai
from google.genai import types
from typing import Dict, Any

# Configure logging
logger = logging.getLogger(__name__)

def perform_deep_research(topic: str) -> Dict[str, Any]:
    """
    Performs deep web research on a specific topic using Google Search grounding.
    Use this for nuanced questions that require up-to-date or specific information
    not found in the standard university profiles (e.g., specific lab funding, 
    recent campus events, detailed dorm reviews).

    Args:
        topic: The research topic or question to investigate.
        
    Returns:
        Dictionary containing the research summary and source links.
    """
    try:
        logger.info(f"="*60)
        logger.info(f"🔍 TOOL: perform_deep_research")
        logger.info(f"   Topic: {topic}")
        logger.info(f"="*60)

        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            return {
                "success": False,
                "error": "GEMINI_API_KEY not found in environment",
                "message": "Cannot perform research: API key missing"
            }

        client = genai.Client(api_key=api_key)
        
        prompt = f"""
        Perform a deep dive research on the following topic:
        "{topic}"
        
        Provide a comprehensive summary of findings, focusing on specific details, 
        numbers, and qualitative insights. If there are conflicting views, mention them.
        """

        response = client.models.generate_content(
            model="gemini-2.5-flash-lite", # Using a strong model for research
            contents=prompt,
            tools=[types.Tool(google_search=types.GoogleSearch())]
        )
        
        # Extract grounding metadata if available (for citations) - simplified for now
        # meaningful_response = response.text
        
        return {
            "success": True,
            "topic": topic,
            "findings": response.text,
            "message": f"Research completed for: {topic}"
        }

    except Exception as e:
        logger.error(f"Deep research failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": f"Research failed: {str(e)}"
        }
