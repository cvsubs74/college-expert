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

MODEL_NAME = "gemini-2.5-flash"

file_saver_agent = LlmAgent(
    name="FileSaver",
    model=MODEL_NAME,
    description="Saves the final profile to a JSON file using the write_file tool.",
    instruction="""YOUR ONLY JOB IS TO SAVE THE FILE. YOU MUST CALL write_file.

=== CRITICAL: YOU MUST CALL THE write_file TOOL ===

DO NOT just respond with text. You MUST use the write_file function tool.

=== STEP 1: Generate filename ===
Take the university name from {university_name} and convert to filename:
- Lowercase everything
- Replace spaces with underscores  
- Remove punctuation (commas, apostrophes, periods)
- Add .json extension

Examples:
- "Stanford University" → "stanford_university.json"
- "UC San Diego" → "uc_san_diego.json"
- "University of North Carolina at Chapel Hill" → "university_of_north_carolina_at_chapel_hill.json"

=== STEP 2: Get the content ===
The content to save is in {university_profile}. 
Format it as a properly indented JSON string.

=== STEP 3: CALL THE write_file TOOL NOW ===

IMMEDIATELY call the write_file tool with:
- filename: <the .json filename you generated>
- content: <the JSON string from university_profile>

The write_file tool will automatically:
1. Save to the local research directory
2. Upload to Google Cloud Storage (GCS)

After calling write_file, report the result: "Saved to <filename> and uploaded to GCS"

REMEMBER: YOU MUST CALL write_file. This is not optional.""",
    tools=[write_file],
    output_key="save_result",
    before_agent_callback=agent_logging_before,
    after_agent_callback=agent_logging_after
)
