"""
Shared logging callbacks for all sub-agents.

This module provides:
1. before_agent_callback / after_agent_callback - Track agent-level timing
2. before_tool_callback / after_tool_callback - Track tool-level timing

Import and use in LlmAgent:
    from .shared_logging import (
        agent_logging_before, agent_logging_after,
        tool_logging_before, tool_logging_after
    )
    
    my_agent = LlmAgent(
        ...
        before_agent_callback=agent_logging_before,
        after_agent_callback=agent_logging_after,
        before_tool_callback=tool_logging_before,
        after_tool_callback=tool_logging_after,
    )
"""

import time
from typing import Dict, Any, Optional
from google.genai import types


# Global timing storage
_agent_start_times: Dict[str, float] = {}
_tool_start_times: Dict[str, float] = {}


# ==============================================================================
# AGENT-LEVEL CALLBACKS (tracks when sub-agents start/end)
# ==============================================================================

def agent_logging_before(callback_context) -> Optional[types.Content]:
    """Log when an agent starts processing."""
    agent_name = callback_context.agent_name
    invocation_id = callback_context.invocation_id
    timing_key = f"{invocation_id}:{agent_name}"
    
    _agent_start_times[timing_key] = time.time()
    
    print(f"\n{'🚀'*3} AGENT START: {agent_name} {'🚀'*3}", flush=True)
    print(f"   Invocation: {invocation_id}", flush=True)
    
    return None  # Allow agent to proceed


def agent_logging_after(callback_context) -> Optional[types.Content]:
    """Log when an agent completes processing with timing."""
    agent_name = callback_context.agent_name
    invocation_id = callback_context.invocation_id
    timing_key = f"{invocation_id}:{agent_name}"
    
    start_time = _agent_start_times.pop(timing_key, None)
    elapsed_str = f"{time.time() - start_time:.2f}s" if start_time else "N/A"
    
    print(f"\n{'🏁'*3} AGENT END: {agent_name} | ⏱️ {elapsed_str} {'🏁'*3}", flush=True)
    
    return None  # Use original output


# ==============================================================================
# TOOL-LEVEL CALLBACKS (tracks tool calls like google_search)
# ==============================================================================

def tool_logging_before(tool, args: Dict[str, Any], tool_context) -> Optional[Dict]:
    """Log tool entry and start timing."""
    agent_name = tool_context.agent_name
    tool_name = tool.name
    timing_key = f"{id(tool_context)}:{tool_name}"
    
    _tool_start_times[timing_key] = time.time()
    
    print(f"\n{'='*60}", flush=True)
    print(f"🔧 TOOL START: {tool_name}", flush=True)
    print(f"   Agent: {agent_name}", flush=True)
    args_str = str(args)[:150] + "..." if len(str(args)) > 150 else str(args)
    print(f"   Args: {args_str}", flush=True)
    print(f"{'='*60}", flush=True)
    
    return None  # Allow tool to execute


def tool_logging_after(tool, args: Dict[str, Any], tool_context, tool_response: Dict) -> Optional[Dict]:
    """Log tool exit with timing."""
    agent_name = tool_context.agent_name
    tool_name = tool.name
    timing_key = f"{id(tool_context)}:{tool_name}"
    
    start_time = _tool_start_times.pop(timing_key, None)
    elapsed_str = f"{time.time() - start_time:.2f}s" if start_time else "N/A"
    
    print(f"\n{'─'*60}", flush=True)
    print(f"✅ TOOL END: {tool_name} | ⏱️ {elapsed_str}", flush=True)
    resp_str = str(tool_response)[:200] + "..." if len(str(tool_response)) > 200 else str(tool_response)
    print(f"   Response: {resp_str}", flush=True)
    print(f"{'─'*60}\n", flush=True)
    
    return None  # Use original response
