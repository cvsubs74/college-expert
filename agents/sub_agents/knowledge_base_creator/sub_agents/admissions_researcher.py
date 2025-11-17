"""
Admissions Data Researcher

Researches comprehensive admissions statistics, deadlines, and holistic review factors.
"""

from google.adk.agents import LlmAgent, LoopAgent
from google.adk.tools import google_search, exit_loop
from ....tools.logging_utils import log_agent_entry, log_agent_exit

# No formatter - raw data is preserved directly from retriever
# Critic ensures quality before exiting loop

# Critic: Evaluates RAW admissions data for completeness and factual accuracy
admissions_critic = LlmAgent(
    name="AdmissionsDataCritic",
    model="gemini-2.5-flash",
    description="Evaluates raw admissions data for completeness and factual accuracy.",
    before_model_callback=log_agent_entry,
    after_model_callback=log_agent_exit,
    instruction="""
    You are a data quality critic. Review the RAW_ADMISSIONS_DATA for completeness and factual accuracy.
    
    **EVALUATION CRITERIA:**
    
    1. **Completeness Check:**
       - Does raw data contain acceptance rate and application numbers?
       - Are GPA, SAT, and ACT ranges present in the data?
       - Are application deadlines (ED/EA/RD) mentioned?
       - Is CDS C7 table or holistic factors information present?
    
    2. **Factual Verification:**
       - Are sources credible (CDS, official admissions pages)?
       - Are statistics consistent across sources?
       - Are there contradictions in the data?
       - Is test policy clearly stated?
    
    3. **Data Quality Check:**
       - Is there enough detail to extract all required fields?
       - Are numbers clearly stated (not vague)?
       - Are percentile ranges complete (25th-75th)?
    
    **DECISION:**
    - If ALL criteria are met and raw data is complete and verified, use 'exit_loop' tool
    - If improvements needed, provide specific feedback in your response
    
    **FEEDBACK FORMAT:**
    - Be specific: "Missing SAT range in raw data"
    - Be actionable: "Search for '[University] Common Data Set Section C9' for test scores"
    - Prioritize: List most critical gaps first
    
    RAW_ADMISSIONS_DATA:
    { raw_admissions_data? }
    
    ADMISSIONS_FEEDBACK (previous):
    { admissions_feedback? }
    """,
    tools=[exit_loop],
    output_key="admissions_feedback"
)

# Retriever: Uses feedback to refine searches iteratively
admissions_retriever = LlmAgent(
    name="AdmissionsDataRetriever",
    model="gemini-2.5-flash",
    description="Searches for admissions data, refining based on critic feedback in loop.",
    before_model_callback=log_agent_entry,
    after_model_callback=log_agent_exit,
    instruction="""
    You are an admissions data retriever. Search for comprehensive admissions statistics.
    
    **IF admissions_feedback EXISTS:**
    - Address each specific gap mentioned in the feedback
    - Perform targeted searches for missing data
    - Example: If "Missing SAT range", search "[University] Common Data Set Section C9 SAT scores"
    
    **IF NO FEEDBACK (FIRST ITERATION):**
    - Perform comprehensive initial searches as described below
    
    **SEARCH STRATEGY:**
    
    1. **CDS & Overall Statistics (Last 5 Years for Trend Analysis):**
       - Search: "[University Name] Common Data Set 2024-2025"
       - Search: "[University Name] Common Data Set 2023-2024"
       - Search: "[University Name] Common Data Set 2022-2023"
       - Search: "[University Name] Common Data Set 2021-2022"
       - Search: "[University Name] Common Data Set 2020-2021"
       - Search: "[University Name] acceptance rate trends 2020-2024"
       - Search: "[University Name] admissions statistics historical data"
    
    2. **Application Plans:**
       - Search: "[University Name] Early Decision deadline acceptance rate"
       - Search: "[University Name] Early Action Regular Decision deadlines"
    
    3. **Admitted Student Profile:**
       - Search: "[University Name] freshman profile admitted students"
       - Search: "[University Name] GPA SAT ACT ranges admitted"
       - Search: "[University Name] test optional policy"
    
    4. **Holistic Factors:**
       - Search: "[University Name] holistic admissions factors"
       - Search: "[University Name] Common Data Set Section C7"
    
    **OUTPUT FORMAT:**
    
    Your output should contain TWO sections:
    
    ---
    ## RAW RESEARCH DATA
    
    [Include ALL raw text from your searches here. Include source URLs, full paragraphs, CDS data, statistics, quotes, etc. 
    This is the comprehensive research data that will be preserved.]
    
    **Sources:**
    - [URL 1]: [Brief description]
    - [URL 2]: [Brief description]
    
    ---
    ## STRUCTURED Q&A SUMMARY
    
    # II. Admissions Data & Holistic Review
    
    ## Overall Statistics (Current Year + 5-Year Trends)
    
    **Q: How many total applications were received (last 5 years)?**
    A: 
    - 2024-2025: [Number] applications
    - 2023-2024: [Number] applications
    - 2022-2023: [Number] applications
    - 2021-2022: [Number] applications
    - 2020-2021: [Number] applications
    **Trend:** [Increasing/Decreasing/Stable by X%]
    
    **Q: What is the overall acceptance rate (last 5 years)?**
    A:
    - 2024-2025: [X]%
    - 2023-2024: [X]%
    - 2022-2023: [X]%
    - 2021-2022: [X]%
    - 2020-2021: [X]%
    **Trend:** [More/Less selective - changed from X% to Y%]
    
    **Q: What is the yield rate (enrolled/admitted)?**
    A: [X]% (most recent year)
    
    ## Application Types & Deadlines
    
    **Q: What are the application deadlines?**
    A: 
    - Early Decision (ED): [Date or N/A]
    - Early Action (EA): [Date or N/A]
    - Regular Decision (RD): [Date]
    
    **Q: What are the acceptance rates by application plan?**
    A:
    - ED: [X]% (or N/A)
    - EA: [X]% (or N/A)
    - RD: [X]%
    
    ## Admitted Student Academic Profile
    
    **Q: What is the GPA range for admitted students?**
    A: 25th-75th percentile: [X.X - X.X] (unweighted)
    
    **Q: What are the SAT score ranges for admitted students?**
    A: Total: 25th-75th percentile: [XXXX - XXXX]
    
    **Q: What are the ACT score ranges for admitted students?**
    A: Composite: 25th-75th percentile: [XX - XX]
    
    **Q: What is the university's standardized test policy?**
    A: [Test-Required / Test-Optional / Test-Blind]
    
    **Q: What percentage of admitted students were in the top 10% of their high school class?**
    A: [X]%
    
    ## Holistic Review Factors (CDS Section C7)
    
    **Q: How does the university rank the importance of various admissions factors?**
    A:
    
    **Very Important:**
    - [List factors]
    
    **Important:**
    - [List factors]
    
    **Considered:**
    - [List factors]
    
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
    - Include all source URLs in BOTH the raw data section AND citations section
    - Number all citations for easy reference
    - Include CDS year in citation (e.g., "Common Data Set 2024-2025")
    
    ADMISSIONS_FEEDBACK:
    { admissions_feedback? }
    
    RAW_ADMISSIONS_DATA (previous):
    { raw_admissions_data? }
    """,
    tools=[google_search],
    output_key="raw_admissions_data"
)

# Loop Agent: Iterates through retrieval and critique (NO formatting in loop)
admissions_research_loop = LoopAgent(
    name="AdmissionsResearchLoop",
    description="Iterates through data retrieval and critique to ensure complete and accurate RAW data.",
    sub_agents=[
        admissions_retriever,
        admissions_critic
    ],
    max_iterations=3
)

# Main Admissions Researcher: Just the loop - raw data stays in state
AdmissionsResearcher = admissions_research_loop
