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
    """Initializes session state with expected output keys to prevent KeyError."""
    
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator:
        keys = [
            "university_name",
            "strategy_output", "admissions_current_output", "admissions_trends_output",
            "admitted_profile_output", "colleges_output", "majors_output",
            "application_output", "strategy_tactics_output", "financials_output",
            "scholarships_output", "credit_policies_output", "student_insights_output",
            "outcomes_output"
        ]
        for key in keys:
            if key not in ctx.session.state:
                ctx.session.state[key] = "" if key == "university_name" else None
        logger.info(f"[StateInitializer] Initialized {len(keys)} output keys, university_name={ctx.session.state.get('university_name')}")
        if False:
            yield Event(author=self.name, content={})


state_initializer = StateInitializer(name="StateInitializer")
