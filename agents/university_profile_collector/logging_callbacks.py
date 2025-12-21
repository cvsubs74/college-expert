"""
Detailed Logging Callbacks for ADK Agents

This module provides before/after tool callbacks that log:
- Tool call entry with args
- Tool call exit with result
- Elapsed time per tool call
- Agent context information

Usage:
    from logging_callbacks import tool_logging_before, tool_logging_after

    my_agent = LlmAgent(
        name="MyAgent",
        ...
        before_tool_callback=tool_logging_before,
        after_tool_callback=tool_logging_after,
    )
"""

import time
import logging
from typing import Dict, Any, Optional
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext

# Configure logging - use CRITICAL level for cleaner output
logging.basicConfig(
    level=logging.WARNING,  # Reduce noise from ADK
    format='%(asctime)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("adk.tools")
logger.setLevel(logging.INFO)

# Global storage for timing (keyed by invocation_id + tool_name)
_tool_start_times: Dict[str, float] = {}


def _get_timing_key(tool_context: ToolContext, tool_name: str) -> str:
    """Generate a unique key for tracking tool timing."""
    invocation_id = getattr(tool_context, 'invocation_id', 'unknown')
    return f"{invocation_id}:{tool_name}"


def tool_logging_before(
    tool: BaseTool,
    args: Dict[str, Any],
    tool_context: ToolContext
) -> Optional[Dict]:
    """
    Before-tool callback that logs entry and starts timing.
    
    Returns None to allow normal tool execution.
    """
    agent_name = tool_context.agent_name
    tool_name = tool.name
    timing_key = _get_timing_key(tool_context, tool_name)
    
    # Record start time
    _tool_start_times[timing_key] = time.time()
    
    # Log entry with clear separator
    print(f"\n{'='*60}")
    print(f"🔧 TOOL START: {tool_name}")
    print(f"   Agent: {agent_name}")
    print(f"   Args: {_truncate_args(args)}")
    print(f"{'='*60}")
    
    # Return None to proceed with normal tool execution
    return None


def tool_logging_after(
    tool: BaseTool,
    args: Dict[str, Any],
    tool_context: ToolContext,
    tool_response: Dict
) -> Optional[Dict]:
    """
    After-tool callback that logs exit with timing.
    
    Returns None to use original response.
    """
    agent_name = tool_context.agent_name
    tool_name = tool.name
    timing_key = _get_timing_key(tool_context, tool_name)
    
    # Calculate elapsed time
    start_time = _tool_start_times.pop(timing_key, None)
    if start_time:
        elapsed_sec = time.time() - start_time
        elapsed_str = f"{elapsed_sec:.2f}s"
    else:
        elapsed_str = "N/A"
    
    # Log exit with timing
    print(f"\n{'─'*60}")
    print(f"✅ TOOL END: {tool_name} | ⏱️ {elapsed_str}")
    print(f"   Response preview: {_truncate_response(tool_response)}")
    print(f"{'─'*60}\n")
    
    # Return None to use original response
    return None


def _truncate_args(args: Dict[str, Any], max_len: int = 150) -> str:
    """Truncate args for readable logging."""
    args_str = str(args)
    if len(args_str) > max_len:
        return args_str[:max_len] + "..."
    return args_str


def _truncate_response(response: Dict, max_len: int = 200) -> str:
    """Truncate response for readable logging."""
    response_str = str(response)
    if len(response_str) > max_len:
        return response_str[:max_len] + "..."
    return response_str

