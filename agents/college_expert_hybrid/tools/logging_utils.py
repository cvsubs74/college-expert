"""Logging utilities for agent callbacks."""
import logging
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
)
logger = logging.getLogger(__name__)


def log_agent_entry(callback_context, llm_request):
    """Logs when an agent is about to be executed."""
    logger.info(f"[{callback_context.agent_name}] Starting processing...")
    # Must return the request or None
    return None


def log_agent_exit(callback_context, llm_response):
    """Logs when an agent has finished execution."""
    logger.info(f"[{callback_context.agent_name}] Completed processing")
    # Must return the response or None
    return None
