"""
Profile Preloader Agent
Custom agent that runs before the main reasoning loop.
It extracts the user's email from the conversation context, fetches their profile
from Elasticsearch, and caches the raw response AS-IS in session state.
"""
import logging
import re
from typing import AsyncGenerator
from typing_extensions import override

from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event

from ...tools.tools import search_user_profile

logger = logging.getLogger(__name__)

# Cache keys - keep it simple, cache raw response as-is
CACHE_KEY_PROFILE = '_cache:student_profile'    # Full raw response from search_user_profile (preserves all data)
CACHE_KEY_EMAIL = '_cache:user_email'           # User email for quick lookup


class ProfileLoaderAgent(BaseAgent):
    """
    Custom agent to preload student profile data.
    Caches the raw ES response as-is to preserve all data.
    """
    
    def __init__(self, name: str = "ProfileLoaderAgent"):
        super().__init__(name=name, sub_agents=[])

    @override
    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        """
        Extract email from user input, fetch profile from ES, and cache as-is.
        Uses ctx.user_content as per ADK documentation.
        """
        logger.info(f"[{self.name}] Starting profile preload check.")
        
        user_email = None
        
        # Primary method: Access user_content from InvocationContext (per ADK docs)
        if ctx.user_content and ctx.user_content.parts:
            for part in ctx.user_content.parts:
                if hasattr(part, 'text') and part.text:
                    text = part.text
                    logger.info(f"[{self.name}] Found user_content text: {text[:100]}...")
                    
                    # Try tagged format first: [USER_EMAIL: email@example.com]
                    email_match = re.search(r'\[USER_EMAIL:\s*([^\]]+)\]', text)
                    if email_match:
                        user_email = email_match.group(1).strip()
                        logger.info(f"[{self.name}] Found email in tag format: {user_email}")
                        break
                    
                    # Try bare email format: email@domain.com
                    bare_email_match = re.search(r'\b([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b', text)
                    if bare_email_match:
                        user_email = bare_email_match.group(1).strip()
                        logger.info(f"[{self.name}] Found bare email: {user_email}")
                        break
        else:
            logger.warning(f"[{self.name}] ctx.user_content is empty or has no parts")

        
        # Fallback: Check session events/history
        if not user_email:
            try:
                events = getattr(ctx.session, 'events', []) or []
                logger.info(f"[{self.name}] Checking {len(events)} session events for email")
                
                for event in reversed(events):
                    content = getattr(event, 'content', None)
                    if content and hasattr(content, 'parts') and content.parts:
                        for part in content.parts:
                            if hasattr(part, 'text') and part.text:
                                text = part.text
                                
                                # Try tagged format first
                                email_match = re.search(r'\[USER_EMAIL:\s*([^\]]+)\]', text)
                                if email_match:
                                    user_email = email_match.group(1).strip()
                                    logger.info(f"[{self.name}] Found email in session events (tag): {user_email}")
                                    break
                                
                                # Try bare email format
                                bare_email_match = re.search(r'\b([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b', text)
                                if bare_email_match:
                                    user_email = bare_email_match.group(1).strip()
                                    logger.info(f"[{self.name}] Found bare email in session events: {user_email}")
                                    break
                        if user_email:
                            break
            except Exception as e:
                logger.warning(f"[{self.name}] Error checking session events: {e}")

        
        # Final fallback: Check cached email
        if not user_email:
            user_email = ctx.session.state.get(CACHE_KEY_EMAIL)
            if user_email:
                logger.info(f"[{self.name}] Using cached email: {user_email}")

        # Cache the email and fetch profile if we have an email
        if user_email:
            ctx.session.state[CACHE_KEY_EMAIL] = user_email
            
            # Check if profile is already cached
            cached_profile = ctx.session.state.get(CACHE_KEY_PROFILE)
            
            if cached_profile:
                # Profile already cached - just log what we have
                docs = cached_profile.get('documents', [])
                if docs:
                    meta = docs[0].get('metadata', {}).get('extracted_data', {}).get('structured_content', {})
                    logger.info(f"[{self.name}] Profile already cached. Student: {meta.get('student_name', 'N/A')}")
                else:
                    logger.info(f"[{self.name}] Profile already cached (no documents)")
            else:
                # Fetch and cache the profile AS-IS from cloud function
                logger.info(f"[{self.name}] Fetching profile for {user_email}...")
                try:
                    raw_profile = search_user_profile(user_email)
                    
                    if raw_profile and raw_profile.get('success'):
                        # Cache the ENTIRE response as-is - preserves ALL data
                        ctx.session.state[CACHE_KEY_PROFILE] = raw_profile
                        
                        # Log what we got for debugging
                        documents = raw_profile.get('documents', [])
                        logger.info(f"[{self.name}] Profile cached! Found {len(documents)} documents")
                        
                        if documents:
                            first_doc = documents[0]
                            metadata = first_doc.get('metadata', {})
                            extracted = metadata.get('extracted_data', {})
                            structured = extracted.get('structured_content', {})
                            
                            logger.info(f"[{self.name}] Cached data includes:")
                            logger.info(f"   - content length: {len(first_doc.get('content', ''))}")
                            logger.info(f"   - metadata keys: {list(metadata.keys())}")
                            logger.info(f"   - structured_content keys: {list(structured.keys())}")
                            logger.info(f"   - student_name: {structured.get('student_name', 'N/A')}")
                    else:
                        logger.warning(f"[{self.name}] Failed to fetch profile: {raw_profile}")
                except Exception as e:
                    logger.error(f"[{self.name}] Error fetching profile: {e}", exc_info=True)
        else:
            logger.warning(f"[{self.name}] No [USER_EMAIL] tag found. user_content exists: {ctx.user_content is not None}")

        # This agent doesn't yield any events visible to the user
        if False:
            yield Event()
