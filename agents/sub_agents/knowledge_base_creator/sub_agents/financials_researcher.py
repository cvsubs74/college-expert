"""
Financials Researcher

Researches cost of attendance, financial aid policies, and merit scholarships.
"""

from google.adk.agents import LlmAgent, LoopAgent
from google.adk.tools import google_search, exit_loop
from ....tools.logging_utils import log_agent_entry, log_agent_exit

# No formatter - raw data is preserved directly from retriever
# Critic ensures quality before exiting loop

# Critic: Evaluates RAW financials data
financials_critic = LlmAgent(
    name="FinancialsDataCritic",
    model="gemini-2.5-flash",
    description="Evaluates raw financials data for completeness and factual accuracy.",
    before_model_callback=log_agent_entry,
    after_model_callback=log_agent_exit,
    instruction="""
    You are a data quality critic. Review the RAW_FINANCIALS_DATA for completeness and factual accuracy.
    
    **EVALUATION CRITERIA:**
    1. **Completeness:** Does raw data contain COA breakdown, aid policies, statistics, merit scholarships?
    2. **Factual Verification:** Are sources credible? Are dollar amounts consistent? Are policies clearly stated?
    3. **Data Quality:** Is there enough detail to extract all required fields?
    
    **DECISION:**
    - If raw data is complete and verified, use 'exit_loop' tool
    - If improvements needed, provide specific feedback in your response
    
    RAW_FINANCIALS_DATA:
    { raw_financials_data? }
    
    FINANCIALS_FEEDBACK (previous):
    { financials_feedback? }
    """,
    tools=[exit_loop],
    output_key="financials_feedback"
)

# Retriever: Uses feedback to refine searches iteratively
financials_retriever = LlmAgent(
    name="FinancialsDataRetriever",
    model="gemini-2.5-flash",
    description="Searches for financials data, refining based on critic feedback in loop.",
    before_model_callback=log_agent_entry,
    after_model_callback=log_agent_exit,
    instruction="""
    You are a financial data retriever.
    
    **IF financials_feedback EXISTS:** Address specific gaps
    **IF NO FEEDBACK:** Perform comprehensive searches
    
    **SEARCH STRATEGY:**
    1. "[University] cost of attendance 2024-2025"
    2. "[University] need blind need aware policy"
    3. "[University] Common Data Set financial aid"
    4. "[University] merit scholarships"
    
    **OUTPUT FORMAT:**
    
    Your output should contain TWO sections:
    
    ---
    ## RAW RESEARCH DATA
    
    [Include ALL raw text from your searches here. Include source URLs, full paragraphs, cost breakdowns, scholarship details, etc.]
    
    **Sources:**
    - [URL 1]: [Brief description]
    - [URL 2]: [Brief description]
    
    ---
    ## STRUCTURED Q&A SUMMARY
    
    # IV. Financials: Cost & Affordability
    
    ## Cost of Attendance (COA)
    
    **Q: What is the total estimated cost of attendance for an on-campus student?**
    A: Total COA: $[XX,XXX] per year
    Breakdown:
    - Tuition & Fees: $[XX,XXX]
    - Room & Board: $[XX,XXX]
    - Books & Supplies: $[X,XXX]
    
    ## Financial Aid Policy
    
    **Q: Is the university need-blind or need-aware for admissions?**
    A:
    - Domestic Students: [Need-Blind / Need-Aware]
    - International Students: [Need-Blind / Need-Aware]
    
    **Q: Does the university meet 100% of demonstrated financial need?**
    A: [Yes / No / Partially] - [Explanation]
    
    ## Financial Aid Statistics
    
    **Q: What percentage of students receive financial aid?**
    A: [X]% of students receive some form of financial aid
    
    **Q: What is the average need-based award?**
    A: $[XX,XXX] average need-based grant/scholarship
    
    ## Merit Scholarships
    
    **Q: What are the major non-need-based (merit) scholarships offered?**
    A:
    1. **[Scholarship Name 1]**
       - Amount: $[XX,XXX] per year
       - Requirements: [Criteria]
    
    **Q: Are students automatically considered for merit scholarships, or is a separate application required?**
    A: [Detailed explanation]
    
    ---
    
    ---
    ## CITATIONS & SOURCES
    
    List ALL sources used in this research with full URLs:
    
    1. [Source Title] - [Full URL] - [Date Accessed]
    2. [Source Title] - [Full URL] - [Date Accessed]
    ...
    
    **IMPORTANT:**
    - Include BOTH raw research data AND structured Q&A
    - Use EXACT dollar amounts from search results
    - Include all source URLs in BOTH the raw data section AND citations section
    - Number all citations for easy reference
    - Include academic year in citation (e.g., "2024-2025 Cost of Attendance")
    
    FINANCIALS_FEEDBACK:
    { financials_feedback? }
    """,
    tools=[google_search],
    output_key="raw_financials_data"
)

# Loop Agent: Retrieval and critique only
financials_research_loop = LoopAgent(
    name="FinancialsResearchLoop",
    description="Iterates through data retrieval and critique to ensure complete RAW data.",
    sub_agents=[
        financials_retriever,
        financials_critic
    ],
    max_iterations=3
)

# Main Researcher: Just the loop - raw data stays in state
FinancialsResearcher = financials_research_loop
