import logging
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
)
logger = logging.getLogger(__name__)

# Callback functions for agent lifecycle logging
def log_agent_entry(callback_context, llm_request):
    """Logs when an agent is about to be executed."""
    logger.info("="*80)
    logger.info(f"🔄 AGENT ENTRY / TRANSFER: {callback_context.agent_name}")
    logger.info("="*80)

def log_agent_exit(callback_context, llm_response):
    """Logs when an agent has finished execution."""
    logger.info("="*80)
    logger.info(f"✅ AGENT EXIT: {callback_context.agent_name}")
    # Optionally log the type of response (e.g., function call)
    if llm_response.content and llm_response.content.parts:
        for part in llm_response.content.parts:
            if part.function_call:
                logger.info(f"   ↪️ Suggested Action: Call tool '{part.function_call.name}'")
    logger.info("="*80)

# Callback functions for tool lifecycle logging
def log_tool_entry(tool_context):
    """Logs when a tool is about to be executed."""
    logger.info("-"*80)
    logger.info(f"🔧 TOOL ENTRY: {tool_context.tool_name}")
    logger.info(f"   Agent: {tool_context.agent_name}")
    
    # Log tool arguments if available
    if hasattr(tool_context, 'args') and tool_context.args:
        try:
            args_str = json.dumps(tool_context.args, indent=2)
            logger.info(f"   Arguments:\n{args_str}")
        except:
            logger.info(f"   Arguments: {tool_context.args}")
    
    logger.info("-"*80)

def log_tool_exit(tool_context, result):
    """Logs when a tool has finished execution."""
    logger.info("-"*80)
    logger.info(f"✅ TOOL EXIT: {tool_context.tool_name}")
    
    # Log result summary
    if result:
        try:
            # Try to log as JSON if it's a dict
            if isinstance(result, dict):
                result_str = json.dumps(result, indent=2)
                logger.info(f"   Result:\n{result_str}")
            else:
                result_preview = str(result)[:500]  # Limit to 500 chars
                logger.info(f"   Result: {result_preview}")
        except:
            logger.info(f"   Result: {result}")
    
    logger.info("-"*80)
