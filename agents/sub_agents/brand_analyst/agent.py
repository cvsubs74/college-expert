from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.tools import google_search
from ...schemas import OfficialNarrative

# 1. Retriever Agent: Finds the raw data.
retriever_agent = LlmAgent(
    name="NarrativeRetrieverAgent",
    model="gemini-2.5-flash",
    description="Finds the official narrative text from a college's website and blogs.",
    instruction="""
    You are a research assistant. Your only job is to use the `google_search` tool to perform a targeted crawl of the college's official website and admissions blog.
    - Your search queries should prioritize the `/admissions/` path and look for pages titled 'What We Look For' or 'How We Review Your Application'.
    - Also search for `"[College Name] admissions blog"`.
    - The `google_search` tool will provide the content of the search results directly. Output the raw, combined text from the most relevant pages.
    """,
    tools=[google_search],
    output_key="raw_narrative_text"
)

# 2. Formatter Agent: Structures the raw data.
formatter_agent = LlmAgent(
    name="NarrativeFormatterAgent",
    model="gemini-2.5-flash",
    description="Analyzes and structures raw narrative text into the OfficialNarrative schema.",
    instruction="""
    You are a qualitative researcher and brand strategist. You will be given the raw text from a college's admissions website and blogs. Your task is to perform a thematic analysis and structure the output into the `OfficialNarrative` JSON schema.

    **CRITICAL WORKFLOW:**

    **Step 1: Thematic Analysis**
    - Analyze the provided raw text to identify the core themes, values, and 'buzzwords' the college uses to describe its ideal student (e.g., 'holistic review', 'impact & initiative', 'community').
    - Extract and list these key attributes.

    **Step 2: Synthesize the 'Ideal Student' Profile**
    - Based on your thematic analysis, write a 3-paragraph summary describing the 'Official Admissions Rubric' or the 'ideal student' profile as promoted by the college.

    **FINAL OUTPUT:**
    - Your final output MUST be a single, valid JSON object that conforms perfectly to the `OfficialNarrative` schema, containing the `key_attributes` and the `ideal_student_summary`.
    """,
    output_schema=OfficialNarrative,
    output_key="official_narrative"
)

# 3. Sequential Agent: Chains the retriever and formatter.
BrandAnalyst = SequentialAgent(
    name="BrandAnalyst",
    description="A sequential agent that first retrieves a college's official narrative and then formats it into a structured analysis.",
    sub_agents=[
        retriever_agent,
        formatter_agent
    ]
)
