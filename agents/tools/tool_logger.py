"""
Tool logging wrapper to add entry/exit logging to all tools.
"""
import functools
import time
from typing import Any, Callable


def log_tool_call(func: Callable) -> Callable:
    """
    Decorator to log tool entry and exit with timing information.
    
    Args:
        func: The tool function to wrap
        
    Returns:
        Wrapped function with logging
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        tool_name = func.__name__
        
        # Log entry
        print(f"[TOOL_ENTRY] 🔧 {tool_name}")
        print(f"[TOOL_ENTRY] Args: {args if args else 'None'}")
        print(f"[TOOL_ENTRY] Kwargs: {list(kwargs.keys()) if kwargs else 'None'}")
        
        start_time = time.time()
        
        try:
            # Execute the tool
            result = func(*args, **kwargs)
            
            # Log successful exit
            elapsed = time.time() - start_time
            print(f"[TOOL_EXIT] ✅ {tool_name} - Success ({elapsed:.2f}s)")
            print(f"[TOOL_EXIT] Result type: {type(result).__name__}")
            
            # Log result summary (truncate if too long)
            result_str = str(result)
            if len(result_str) > 200:
                result_str = result_str[:200] + "..."
            print(f"[TOOL_EXIT] Result: {result_str}")
            
            return result
            
        except Exception as e:
            # Log error exit
            elapsed = time.time() - start_time
            print(f"[TOOL_EXIT] ❌ {tool_name} - Error ({elapsed:.2f}s)")
            print(f"[TOOL_EXIT] Error: {type(e).__name__}: {str(e)}")
            raise
    
    return wrapper
