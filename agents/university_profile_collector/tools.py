"""
Tools for University Profile Collector agents.
"""
import os
import logging
from google.adk.tools import ToolContext

logger = logging.getLogger(__name__)

# Get the research directory path
RESEARCH_DIR = os.path.join(os.path.dirname(__file__), 'research')


def write_file(
    tool_context: ToolContext,
    filename: str,
    content: str
) -> dict:
    """Writes content to a file in the research directory."""
    os.makedirs(RESEARCH_DIR, exist_ok=True)
    target_path = os.path.join(RESEARCH_DIR, filename)
    with open(target_path, "w", encoding="utf-8") as f:
        f.write(content)
    logger.info(f"Saved file to: {target_path}")
    return {"status": "success", "path": target_path}
