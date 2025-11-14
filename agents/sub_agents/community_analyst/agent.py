from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.tools import google_search
from ...schemas import ForumPatterns

# 1. Retriever Agent: Finds the raw data.
retriever_agent = LlmAgent(
    name="ForumRetrieverAgent",
    model="gemini-2.5-flash",
    description="Finds the 'Decision Thread' text from public forums.",
    instruction="""
    You are a research assistant. Your only job is to use the `google_search` tool to find the official 'Decision Megathreads' for the college on Reddit (r/ApplyingToCollege, r/collegeresults) and College Confidential.
    - Use advanced search operators like `site:talk.collegeconfidential.com "[College Name] Class of 2029 Official RD Thread"`.
    - The `google_search` tool will provide the content of the search results directly. Output the raw, combined text from the most relevant threads.
    """,
    tools=[google_search],
    output_key="raw_forum_text"
)

# 2. Formatter Agent: Structures the raw data.
formatter_agent = LlmAgent(
    name="ForumFormatterAgent",
    model="gemini-2.5-flash",
    description="Analyzes and structures raw forum text into the ForumPatterns schema.",
    instruction="""
    You are a senior data analyst and admissions strategist. You will be given the raw text from a college's 'Decision Thread' forum posts. Your task is to perform the 3-pass analysis and structure the output into the `ForumPatterns` JSON schema.

    **CRITICAL WORKFLOW (2-Pass Analysis):**
    You MUST perform the following steps in order.

    **Pass 1: Date Identification & Filtering**
    - Scan the provided raw text to find the official decision release date and time. Look for phrases like 'Decisions come out on Wednesday' or 'released at 7 pm eastern'.
    - Mentally discard all posts made before this date and time. This is critical for filtering out noise.

    **Pass 2: Profile Extraction and Analysis (NER & Clustering)**
    - Analyze the remaining (post-decision-release) text.
    - **Profile Extraction (NER):** For each post containing an outcome, extract a profile as an AnecdotalProfile object with: decision, gpa (optional), test_scores (optional), spike (optional), and summary. This will become the `anecdotal_profiles` list.
    - **Pattern Analysis:** Cluster the extracted profiles into 'Accepted' and 'Rejected' groups. Analyze these clusters to produce the `statistical_patterns`, `spike_patterns`, `outlier_and_contradiction_analysis`, and `sentiment_synthesis`.

    **FINAL OUTPUT:**
    - Your final output MUST be a single, valid JSON object that conforms perfectly to the `ForumPatterns` schema.
    - The `anecdotal_profiles` must be a list of AnecdotalProfile objects, not plain dictionaries.
    """,
    output_schema=ForumPatterns
)

# 3. Sequential Agent: Chains the retriever and formatter.
CommunityAnalyst = SequentialAgent(
    name="CommunityAnalyst",
    description="A sequential agent that first retrieves raw forum data and then formats it into a structured analysis of community patterns.",
    sub_agents=[
        retriever_agent,
        formatter_agent
    ]
)
