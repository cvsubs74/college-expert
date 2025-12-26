"""
Application Agent - Uses ParallelAgent pattern with focused micro-agents.

This agent runs 3 micro-agents in parallel to gather application process info,
then aggregates their outputs into a single structured result.
"""
from google.adk.agents import LlmAgent, ParallelAgent, SequentialAgent
from .shared_logging import (
    agent_logging_before, agent_logging_after,
    tool_logging_before, tool_logging_after
)
from google.adk.tools import google_search

MODEL_NAME = "gemini-2.5-flash"

# ==============================================================================
# MICRO-AGENTS
# ==============================================================================

# Micro-agent 1: Platforms and deadlines
deadlines_micro = LlmAgent(
    name="DeadlinesMicro",
    model=MODEL_NAME,
    description="Fetches application platforms and deadlines.",
    instruction="""Research application deadlines for {university_name}:

1. platforms (list): ["Common App", "Coalition App", etc.]
2. For each deadline type (ED, EA, ED2, RD):
   - plan_type: "Early Decision", "Early Action", "Regular Decision"
   - date: "YYYY-MM-DD" format
   - is_binding: true/false
   - notes: Any special notes

Search: "{university_name}" application deadline current cycle
Search: site:commonapp.org "{university_name}"

OUTPUT (JSON):
{
  "platforms": ["Common App"],
  "application_deadlines": [
    {"plan_type": "Early Decision", "date": "2024-11-01", "is_binding": true, "notes": ""},
    {"plan_type": "Regular Decision", "date": "2025-01-05", "is_binding": false, "notes": ""}
  ]
}""",
    tools=[google_search],
    output_key="deadlines",
    before_agent_callback=agent_logging_before,
    after_agent_callback=agent_logging_after
)

# Micro-agent 2: Supplemental requirements
supplementals_micro = LlmAgent(
    name="SupplementalsMicro",
    model=MODEL_NAME,
    description="Fetches supplemental essay and audition requirements.",
    instruction="""Research supplemental requirements for {university_name}:

For each requirement:
- target_program: "All", "Music", "Architecture", etc.
- requirement_type: "Essays", "Audition", "Portfolio"
- deadline: Date or null
- details: What's required

Search: "{university_name}" supplemental essays current year
Search: site:acceptd.com "{university_name}" audition

OUTPUT (JSON array):
[
  {
    "target_program": "All",
    "requirement_type": "Essays",
    "deadline": null,
    "details": "Two supplemental essays required"
  }
]""",
    tools=[google_search],
    output_key="supplemental_requirements",
    before_agent_callback=agent_logging_before,
    after_agent_callback=agent_logging_after
)

# Micro-agent 3: Holistic review factors
holistic_factors_micro = LlmAgent(
    name="HolisticFactorsMicro",
    model=MODEL_NAME,
    description="Fetches holistic review factors.",
    instruction="""Research holistic review factors for {university_name}:

⚠️ CRITICAL: You MUST return a JSON OBJECT with these exact keys. NEVER return a string or paragraph.

EXACT REQUIRED FIELDS (return this JSON object structure):
  - primary_factors (array of strings): Most important factors from CDS Section C7
  - secondary_factors (array of strings): Secondary/considered factors
  - essay_importance (string): MUST be one of: "Critical", "High", "Moderate", "Low"
  - demonstrated_interest (string): MUST be one of: "Important", "Considered", "Not Considered"
  - interview_policy (string): MUST be one of: "Required", "Recommended", "Evaluative", "Informational", "Not Offered"
  - legacy_consideration (string): MUST be one of: "Strong", "Moderate", "Minimal", "None", "Unknown"
  - first_gen_boost (string): MUST be one of: "Strong", "Moderate", "Minimal", "None", "Unknown"
  - specific_differentiators (string): What makes their process unique

Search: "{university_name}" Common Data Set Section C7
Search: "{university_name}" demonstrated interest policy

OUTPUT (JSON OBJECT - NOT A STRING):
{
  "holistic_factors": {
    "primary_factors": ["Course Rigor", "GPA", "Essays", "Recommendations"],
    "secondary_factors": ["Extracurriculars", "Talents", "Character"],
    "essay_importance": "Critical",
    "demonstrated_interest": "Not Considered",
    "interview_policy": "Recommended",
    "legacy_consideration": "Moderate",
    "first_gen_boost": "Moderate",
    "specific_differentiators": "Values intellectual curiosity"
  }
}""",
    tools=[google_search],
    output_key="holistic_factors",
    before_agent_callback=agent_logging_before,
    after_agent_callback=agent_logging_after
)

# Micro-agent 4: Essay Prompts with Brainstorming Questions
essay_prompts_micro = LlmAgent(
    name="EssayPromptsMicro",
    model=MODEL_NAME,
    description="Fetches actual supplemental essay prompts and generates brainstorming questions.",
    instruction="""Research the EXACT supplemental essay prompts for {university_name} for the current application cycle (2024-2025):

⚠️ CRITICAL: Find the ACTUAL essay prompts, not summaries. These should be the EXACT questions students need to answer.

For EACH essay prompt you find:
1. Record the exact prompt text
2. Note the word/character limit
3. Categorize the type (Why This School, Major, Community, Personal, Activity, etc.)
4. Note if required or optional
5. Generate 5 SPECIFIC brainstorming questions to help students self-reflect on THIS exact prompt

The brainstorming questions should:
- Be specific to THIS exact prompt, not generic
- Guide students to self-reflection without giving answers
- Help them find authentic, personal stories
- Each unlock a different angle or memory

Search: site:{university_name}.edu supplemental essay prompts 2024-2025
Search: site:commonapp.org "{university_name}" essay prompts
Search: "{university_name}" supplemental essays 2024-2025 prompts

OUTPUT (JSON array):
[
  {
    "prompt": "Most students choose their intended major or area of study based on a passion or inspiration that's developed over time—what passion or inspiration led you to choose this area of study?",
    "word_limit": "300 words",
    "type": "Major",
    "required": true,
    "brainstorming_questions": [
      "When did you first become interested in this field? Was there a specific moment or experience?",
      "What problems or questions in this field excite you most?",
      "How have you explored this interest outside of required coursework?",
      "What do you hope to discover or create in this field?",
      "Who has influenced your thinking about this subject?"
    ]
  }
]""",
    tools=[google_search],
    output_key="essay_prompts",
    before_agent_callback=agent_logging_before,
    after_agent_callback=agent_logging_after
)

# ==============================================================================
# PARALLEL AGENT
# ==============================================================================

application_parallel_collector = ParallelAgent(
    name="ApplicationParallelCollector",
    sub_agents=[
        deadlines_micro,
        supplementals_micro,
        holistic_factors_micro,
        essay_prompts_micro
    ]
)

# ==============================================================================
# AGGREGATOR
# ==============================================================================

application_aggregator = LlmAgent(
    name="ApplicationAggregator",
    model=MODEL_NAME,
    description="Aggregates all application micro-agent outputs.",
    instruction="""Aggregate ALL micro-agent outputs into final application_process structure.

=== INPUT DATA ===
- deadlines: platforms, application_deadlines array
- supplemental_requirements: array of requirements
- holistic_factors: review factors
- essay_prompts: array of actual essay prompts

=== OUTPUT STRUCTURE ===
{
  "application_process": {
    "platforms": <from deadlines>,
    "application_deadlines": <from deadlines>,
    "supplemental_requirements": <from supplemental_requirements>,
    "holistic_factors": <from holistic_factors>,
    "essay_prompts": <from essay_prompts>
  }
}

Use ( ) instead of {} in output.""",
    output_key="application_output",
    before_agent_callback=agent_logging_before,
    after_agent_callback=agent_logging_after
)

# ==============================================================================
# MAIN AGENT
# ==============================================================================

application_agent = SequentialAgent(
    name="ApplicationSequential",
    sub_agents=[application_parallel_collector, application_aggregator]
)
