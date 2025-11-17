"""
Student Life & Outcomes Researcher

Researches student life, housing, diversity, and career outcomes.
"""

from google.adk.agents import LlmAgent, LoopAgent
from google.adk.tools import google_search, exit_loop
from ....tools.logging_utils import log_agent_entry, log_agent_exit

# No formatter - raw data is preserved directly from retriever
# Critic ensures quality before exiting loop

# Critic: Evaluates RAW student life data
student_life_critic = LlmAgent(
    name="StudentLifeDataCritic",
    model="gemini-2.5-flash",
    description="Evaluates raw student life data for completeness and factual accuracy.",
    before_model_callback=log_agent_entry,
    after_model_callback=log_agent_exit,
    instruction="""
    You are a data quality critic. Review the RAW_STUDENT_LIFE_DATA for completeness and factual accuracy.
    
    **EVALUATION CRITERIA:**
    1. **Completeness:** Does raw data contain housing policy, diversity stats, career outcomes?
    2. **Factual Verification:** Are sources credible? Are statistics consistent? Are salary figures from official sources?
    3. **Data Quality:** Is there enough detail to extract all required fields?
    
    **DECISION:**
    - If raw data is complete and verified, use 'exit_loop' tool
    - If improvements needed, provide specific feedback in your response
    
    RAW_STUDENT_LIFE_DATA:
    { raw_student_life_data? }
    
    STUDENT_LIFE_FEEDBACK (previous):
    { student_life_feedback? }
    """,
    tools=[exit_loop],
    output_key="student_life_feedback"
)

# Retriever: Uses feedback to refine searches iteratively
student_life_retriever = LlmAgent(
    name="StudentLifeDataRetriever",
    model="gemini-2.5-flash",
    description="Searches for student life data, refining based on critic feedback in loop.",
    before_model_callback=log_agent_entry,
    after_model_callback=log_agent_exit,
    instruction="""
    You are a student life data retriever.
    
    **IF student_life_feedback EXISTS:** Address specific gaps
    **IF NO FEEDBACK:** Perform comprehensive searches
    
    **SEARCH STRATEGY:**
    1. "[University] housing policy guaranteed years"
    2. "[University] diversity statistics demographics"
    3. "[University] career outcomes employment rate"
    4. "[University] average starting salary graduates"
    5. "[University] top employers hiring"
    6. "[University] graduate school placement"
    
    **OUTPUT FORMAT:**
    
    Your output should contain TWO sections:
    
    ---
    ## RAW RESEARCH DATA
    
    [Include ALL raw text from your searches here. Include source URLs, full paragraphs, housing details, diversity stats, career outcomes, etc.]
    
    **Sources:**
    - [URL 1]: [Brief description]
    - [URL 2]: [Brief description]
    
    ---
    ## STRUCTURED Q&A SUMMARY
    
    # V. Student Life, Culture & Outcomes
    
    ## Student Life
    
    **Q: What is the on-campus housing policy?**
    A: [Detailed explanation]
    
    **Q: Is housing guaranteed? If so, for how many years?**
    A: [Yes/No] - [Explanation]
    
    **Q: What percentage of students live on campus?**
    A: [X]% of students live in university housing
    
    ## Diversity
    
    **Q: What are the key diversity statistics?**
    A:
    **Geographic Diversity:**
    - In-State: [X]%
    - Out-of-State: [X]%
    - International: [X]% from [X] countries
    
    **Racial/Ethnic Diversity:**
    - Asian: [X]%
    - Hispanic/Latino: [X]%
    - Black/African American: [X]%
    - White: [X]%
    
    ## Career Outcomes
    
    **Q: What is the job placement rate for graduates?**
    A: [X]% of graduates are employed or continuing education within [timeframe]
    
    **Q: What is the average starting salary for graduates?**
    A: $[XX,XXX] average starting salary
    
    **Q: What are the top companies hiring graduates?**
    A: Top 5-10 employers include:
    1. [Company 1]
    2. [Company 2]
    ...
    
    **Q: What are the top graduate schools that graduates attend?**
    A: Top 5 graduate schools include:
    1. [University 1]
    2. [University 2]
    ...
    
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
    - Include report year for career outcomes (e.g., "Class of 2024 Career Outcomes")
    
    STUDENT_LIFE_FEEDBACK:
    { student_life_feedback? }
    """,
    tools=[google_search],
    output_key="raw_student_life_data"
)

# Loop Agent: Retrieval and critique only
student_life_research_loop = LoopAgent(
    name="StudentLifeResearchLoop",
    description="Iterates through data retrieval and critique to ensure complete RAW data.",
    sub_agents=[
        student_life_retriever,
        student_life_critic
    ],
    max_iterations=3
)

# Main Researcher: Just the loop - raw data stays in state
StudentLifeResearcher = student_life_research_loop
