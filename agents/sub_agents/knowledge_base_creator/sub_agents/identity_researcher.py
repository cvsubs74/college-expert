"""
Identity & Profile Researcher

Researches university identity, mission, culture, and basic demographics.
Outputs raw research data without formatting.
"""

from google.adk.agents import LlmAgent, LoopAgent
from google.adk.tools import google_search, exit_loop
from ....tools.logging_utils import log_agent_entry, log_agent_exit

# Critic: Evaluates the RAW retrieved data for completeness and factual accuracy
identity_critic = LlmAgent(
    name="IdentityDataCritic",
    model="gemini-2.5-flash",
    description="Evaluates raw identity data for completeness and factual accuracy.",
    before_model_callback=log_agent_entry,
    after_model_callback=log_agent_exit,
    instruction="""
    You are a data quality critic. Review the RAW_IDENTITY_DATA for completeness and factual accuracy.
    
    **EVALUATION CRITERIA:**
    
    1. **Completeness Check:**
       - Does raw data contain full university name and location?
       - Is setting (Urban/Suburban/Rural) identifiable from the data?
       - Is university type (Public/Private/Liberal Arts/Research) clear?
       - Is mission statement present?
       - Are enrollment and ratio statistics present?
       - Are there descriptions of campus culture?
    
    2. **Factual Verification:**
       - Are sources credible (official university pages, CDS)?
       - Are statistics consistent across sources?
       - Are there contradictions in the data?
       - Is the mission statement from official source?
    
    3. **Data Quality Check:**
       - Is there enough detail to extract all required fields?
       - Are numbers clearly stated (not vague)?
       - Are there multiple sources confirming key facts?
    
    **DECISION:**
    - If ALL criteria are met and raw data is complete and verified, use 'exit_loop' tool
    - If improvements needed, provide specific feedback in your response
    
    **FEEDBACK FORMAT:**
    - Be specific: "Missing student-to-faculty ratio in raw data"
    - Be actionable: "Search for '[University] Common Data Set' for class size data"
    - Prioritize: List most critical gaps first
    
    RAW_IDENTITY_DATA:
    { raw_identity_data? }
    
    IDENTITY_FEEDBACK (previous):
    { identity_feedback? }
    """,
    tools=[exit_loop],
    output_key="identity_feedback"
)

# Retriever: Uses feedback to refine searches iteratively
identity_retriever = LlmAgent(
    name="IdentityDataRetriever",
    model="gemini-2.5-flash",
    description="Searches for identity data, refining based on critic feedback in loop.",
    before_model_callback=log_agent_entry,
    after_model_callback=log_agent_exit,
    instruction="""
    You are a university identity data retriever. Search for comprehensive information.
    
    **IF identity_feedback EXISTS:**
    - Address each specific gap mentioned in the feedback
    - Perform targeted searches for missing data
    - Example: If "Missing student-to-faculty ratio", search "[University] Common Data Set student faculty ratio"
    
    **IF NO FEEDBACK (FIRST ITERATION):**
    - Perform comprehensive initial searches as described below
    
    **SEARCH STRATEGY:**
    
    1. **Basic Information:**
       - Search: "[University Name] about location setting"
       - Search: "[University Name] type public private liberal arts"
       - Search: "[University Name] religious affiliation"
    
    2. **Size & Demographics:**
       - Search: "[University Name] undergraduate enrollment"
       - Search: "[University Name] student faculty ratio"
       - Search: "[University Name] Common Data Set class size"
    
    3. **Mission & Culture:**
       - Search: "[University Name] mission statement"
       - Search: "[University Name] campus culture student experience"
       - Search: "[University Name] student reviews campus atmosphere"
    
    **OUTPUT FORMAT:**
    
    Your output should contain TWO sections:
    
    ---
    ## RAW RESEARCH DATA
    
    [Include ALL raw text from your searches here. Include source URLs, full paragraphs, statistics, quotes, etc. 
    This is the comprehensive research data that will be preserved.]
    
    **Sources:**
    - [URL 1]: [Brief description]
    - [URL 2]: [Brief description]
    
    ---
    ## STRUCTURED Q&A SUMMARY
    
    # I. University Identity & Profile
    
    ## Basic Information
    
    **Q: What is the full university name and location?**
    A: [Full Name], [City, State]
    
    **Q: What is the campus setting?**
    A: [Urban/Suburban/Rural]
    
    **Q: What type of university is this?**
    A: [Public/Private, Research/Liberal Arts, etc.]
    
    **Q: Is there a religious affiliation?**
    A: [Yes - specify, or No]
    
    ## Size & Demographics
    
    **Q: What is the total undergraduate enrollment?**
    A: [Number] students
    
    **Q: What is the student-to-faculty ratio?**
    A: [X:1]
    
    **Q: What is the average class size?**
    A: [X]% of classes have under 20 students, [Y]% have over 50 students
    
    ## Mission & Culture
    
    **Q: What is the university's official mission statement?**
    A: [Full mission statement]
    
    **Q: What are 3-5 adjectives that describe the campus culture?**
    A: [List adjectives with brief explanation]
    
    ---
    
    ---
    ## CITATIONS & SOURCES
    
    List ALL sources used in this research with full URLs:
    
    1. [Source Title] - [Full URL] - [Date Accessed]
    2. [Source Title] - [Full URL] - [Date Accessed]
    ...
    
    **IMPORTANT:**
    - Include BOTH raw research data AND structured Q&A
    - Use EXACT values from search results
    - If data not found, state "Data not available"
    - Include all source URLs in BOTH the raw data section AND citations section
    - Number all citations for easy reference
    
    IDENTITY_FEEDBACK:
    { identity_feedback? }
    
    RAW_IDENTITY_DATA (previous):
    { raw_identity_data? }
    """,
    tools=[google_search],
    output_key="raw_identity_data"
)

# Loop Agent: Iterates through retrieval and critique (NO formatting in loop)
identity_research_loop = LoopAgent(
    name="IdentityResearchLoop",
    description="Iterates through data retrieval and critique to ensure complete and accurate RAW data.",
    sub_agents=[
        identity_retriever,
        identity_critic
    ],
    max_iterations=3
)

# Main Identity Researcher: Just the loop - raw data stays in state
IdentityResearcher = identity_research_loop
