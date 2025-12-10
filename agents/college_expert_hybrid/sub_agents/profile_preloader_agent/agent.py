"""
Profile Preloader Agent
Custom agent that runs before the main reasoning loop.
It extracts the user's email from the conversation context and pre-loads 
their student profile into the session state cache.
"""
import logging
import re
from typing import AsyncGenerator
from typing_extensions import override

from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from google.genai import types

from ...tools.tools import search_user_profile

logger = logging.getLogger(__name__)

class ProfileLoaderAgent(BaseAgent):
    """
    Custom agent to preload student profile data.
    """
    
    def __init__(self, name: str = "ProfileLoaderAgent"):
        super().__init__(name=name, sub_agents=[])

    @override
    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        """
        Extract email and cache profile.
        """
        logger.info(f"[{self.name}] Starting profile preload check.")
        
        # 1. Try to find user email in current input or history
        user_email = None
        
        # Check current message parts
        # Try to find input in standard locations
        current_input = getattr(ctx, 'input', None)
        
        if not current_input:
             # Try getting event content if available
             event = getattr(ctx, 'event', None)
             if event:
                 current_input = getattr(event, 'content', None)
        
        if current_input and hasattr(current_input, 'parts'):
            for part in current_input.parts:
                if part.text:
                    email_match = re.search(r'\[USER_EMAIL:\s*([^\]]+)\]', part.text)
                    if email_match:
                        user_email = email_match.group(1).strip()
                        logger.info(f"[{self.name}] Found email in current input: {user_email}")
                        break
        
        # If not in current input, check history (from session state usually, or history list)
        if not user_email:
            # ADK provides history access via ctx.session.history if available, 
            # but simpler is to check if we already parsed it in a previous turn
            # stored in session state?
            # Or scan history if ADK exposes it. 
            # For now, let's rely on the mechanism that injects [USER_EMAIL] in the prompt.
            # If it's a multi-turn conversation, the frontend might inject it every time, 
            # OR we need to persist it.
            pass

        if user_email:
            # Check if already cached to avoid redundant calls (though tool handles it, good to double check)
            cache_key = '_cache:student_profile'
            cached_profile = ctx.session.state.get(cache_key)
            
            if not cached_profile:
                logger.info(f"[{self.name}] Profile not cached. Fetching for {user_email}...")
                try:
                    # Call the tool directly (synchronously is fine here as it's a tool function)
                    profile = search_user_profile(user_email)
                    
                    if profile and profile.get('success'):
                        logger.info(f"[{self.name}] Profile fetched successfully. Caching.")
                        ctx.session.state[cache_key] = profile
                    else:
                        logger.warning(f"[{self.name}] Failed to fetch profile or no profile found.")
                        # We can still cache a "not found" state if desired, or just leave empty
                except Exception as e:
                    logger.error(f"[{self.name}] Error fetching profile: {e}")
            else:
                logger.info(f"[{self.name}] Profile already cached.")
        else:
            logger.warning(f"[{self.name}] No [USER_EMAIL] tag found in input. Cannot preload profile.")

        # This agent doesn't yield any events visible to the user, just side-effects.
        # To make this an async generator that yields nothing, we use this pattern:
        if False:
            yield Event()
