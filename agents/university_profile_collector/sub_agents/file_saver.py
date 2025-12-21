"""
FileSaver - Saves university profile to JSON file.
"""
from google.adk.agents import LlmAgent
from .shared_logging import (
    agent_logging_before, agent_logging_after,
    tool_logging_before, tool_logging_after
)

try:
    from ..tools import write_file
except ImportError:
    from tools import write_file

MODEL_NAME = "gemini-2.5-flash-lite"

file_saver_agent = LlmAgent(
    name="FileSaver",
    model=MODEL_NAME,
    description="Saves the final profile to a JSON file.",
    instruction="""YOU MUST CALL the write_file tool to save the profile.

=== STEP 1: Generate filename ===
Convert the university name to a lowercase slug:
- Replace spaces with underscores
- Remove punctuation
- Example: "UC San Diego" -> "uc_san_diego.json"

=== STEP 2: Prepare content ===
Take the complete JSON from {university_profile} and format it with proper indentation.

=== STEP 3: CALL THE TOOL ===
YOU MUST call write_file with these exact parameters:
- filename: the slug.json you generated
- content: the formatted JSON string
""",
    tools=[write_file],
    output_key="save_result",
    before_agent_callback=agent_logging_before,
    after_agent_callback=agent_logging_after
)
