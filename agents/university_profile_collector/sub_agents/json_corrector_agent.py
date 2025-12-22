"""
JSON Corrector Agent - Uses ADK native BuiltInCodeExecutor to fix malformed JSON.

Per ADK docs: The BuiltInCodeExecutor cannot be combined with other tools in the same agent.
This agent is dedicated to fixing JSON errors via code execution.
"""
from google.adk.agents import LlmAgent
from .shared_logging import (
    agent_logging_before, agent_logging_after,
    tool_logging_before, tool_logging_after
)
from google.adk.code_executors import BuiltInCodeExecutor

MODEL_NAME = "gemini-2.5-flash"

json_corrector_agent = LlmAgent(
    name="JsonCorrectorAgent",
    model=MODEL_NAME,
    description="Fixes malformed JSON by analyzing errors and executing Python code.",
    code_executor=BuiltInCodeExecutor(),
    instruction="""You are a JSON repair specialist. Given malformed JSON and an error message,
you must:

1. Analyze the error message to understand what's wrong.
2. Write Python code to fix the JSON.
3. Execute the code and return ONLY the corrected JSON (no markdown, no explanation).

Common fixes:
- Replace unescaped quotes inside strings with escaped quotes
- Replace `null` with empty values where appropriate ([] for lists, "" for strings)
- Fix trailing commas
- Fix unescaped backslashes
- Convert "7.47%" to 7.47 for numeric fields

Your output should be the corrected JSON only, wrapped in ```json``` code blocks.
"""
)
