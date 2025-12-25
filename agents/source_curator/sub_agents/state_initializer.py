"""
StateInitializer - Initializes session state with expected output keys.
"""
import logging
from google.adk.agents import BaseAgent
from google.adk.events import Event
from google.adk.agents.invocation_context import InvocationContext
from typing import AsyncGenerator

logger = logging.getLogger(__name__)


class StateInitializer(BaseAgent):
    """Initializes session state with expected output keys for source discovery."""
    
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator:
        keys = [
            "university_name",
            "university_id",
            "ipeds_id",
            "discovered_sources",
            "yaml_output_path",
            "discovery_summary"
        ]
        for key in keys:
            if key not in ctx.session.state:
                ctx.session.state[key] = None
        
        logger.info(f"[StateInitializer] Initialized {len(keys)} output keys")
        
        if False:
            yield Event(author=self.name, content={})


state_initializer = StateInitializer(name="StateInitializer")
