"""
Shared logging callbacks for Source Curator agents.
"""
import logging
import time
from typing import Optional, Any
from google.adk.agents.callback_context import CallbackContext
from google.adk.tools import BaseTool, ToolContext

logger = logging.getLogger(__name__)

# Track timing per agent
_agent_start_times = {}
_tool_start_times = {}


def agent_logging_before(callback_context: CallbackContext) -> Optional[dict]:
    """Log when agent starts executing."""
    agent_name = callback_context.agent_name
    _agent_start_times[agent_name] = time.time()
    logger.info(f"🚀 [{agent_name}] Starting execution...")
    return None


def agent_logging_after(callback_context: CallbackContext) -> Optional[dict]:
    """Log when agent completes with timing."""
    agent_name = callback_context.agent_name
    elapsed = 0
    if agent_name in _agent_start_times:
        elapsed = time.time() - _agent_start_times[agent_name]
        del _agent_start_times[agent_name]
    
    logger.info(f"✅ [{agent_name}] Completed in {elapsed:.2f}s")
    return None


def tool_logging_before(
    tool: BaseTool, 
    args: dict, 
    tool_context: ToolContext = None,
    **kwargs
) -> Optional[dict]:
    """Log when tool is called."""
    tool_name = tool.name if hasattr(tool, 'name') else str(tool)
    _tool_start_times[tool_name] = time.time()
    
    # Truncate args for cleaner logs
    args_preview = str(args)[:200] + "..." if len(str(args)) > 200 else str(args)
    logger.info(f"🔧 [Tool: {tool_name}] Called with: {args_preview}")
    return None


def tool_logging_after(
    tool: BaseTool,
    args: dict,
    tool_context: ToolContext = None,
    tool_response: Any = None,
    **kwargs
) -> Optional[dict]:
    """Log tool completion with timing."""
    tool_name = tool.name if hasattr(tool, 'name') else str(tool)
    elapsed = 0
    if tool_name in _tool_start_times:
        elapsed = time.time() - _tool_start_times[tool_name]
        del _tool_start_times[tool_name]
    
    # Summarize response
    if isinstance(tool_response, dict):
        keys = list(tool_response.keys())[:5]
        response_preview = f"keys: {keys}"
    else:
        response_preview = str(tool_response)[:100] if tool_response else "None"
    
    logger.info(f"✅ [Tool: {tool_name}] Done in {elapsed:.2f}s. Response: {response_preview}")
    return None
