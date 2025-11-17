"""
Academics & Majors Researcher

Researches academic programs, majors, internal acceptance rates, and transfer policies.
"""

from google.adk.agents import LlmAgent, LoopAgent
from google.adk.tools import google_search, exit_loop
from ....tools.logging_utils import log_agent_entry, log_agent_exit

# No formatter - raw data is preserved directly from retriever
# Critic ensures quality before exiting loop

# Critic: Evaluates RAW academics data
academics_critic = LlmAgent(
    name="AcademicsDataCritic",
    model="gemini-2.5-flash",
    description="Evaluates raw academics data for completeness and factual accuracy.",
    before_model_callback=log_agent_entry,
    after_model_callback=log_agent_exit,
    instruction="""
    You are a data quality critic. Review the RAW_ACADEMICS_DATA for completeness and factual accuracy.
    
    **EVALUATION CRITERIA:**
    
    1. **Comprehensive Degree Catalog:**
       - Does raw data contain a COMPLETE list of ALL undergraduate majors/degrees?
       - Are majors organized by college/school?
       - Is there a total count of majors offered?
       - Are degree types specified (BA, BS, BFA, etc.)?
    
    2. **Degree Details for Each Major:**
       - Are credit hour requirements listed for majors?
       - Are core course requirements mentioned?
       - Are prerequisites identified?
       - Are special features noted (honors, study abroad, etc.)?
    
    3. **Colleges & Schools:**
       - Are all undergraduate colleges/schools listed?
       - Is the application process clearly explained?
       - Are internal acceptance rates mentioned (if available)?
    
    4. **Major Policies:**
       - Are impacted/capped majors identified?
       - Are popular majors listed with enrollment data?
       - Are transfer policies clearly stated?
       - Are double major/minor policies explained?
    
    5. **Factual Verification:**
       - Are sources credible (official academic catalogs, university websites)?
       - Are policies clearly stated with specific requirements?
       - Are there contradictions in the data?
    
    6. **Data Quality:**
       - Is there enough detail to extract ALL required fields?
       - Are degree requirements specific and actionable?
    
    **DECISION:**
    - If raw data is complete and verified, use 'exit_loop' tool
    - If improvements needed, provide specific feedback in your response
    
    RAW_ACADEMICS_DATA:
    { raw_academics_data? }
    
    ACADEMICS_FEEDBACK (previous):
    { academics_feedback? }
    """,
    tools=[exit_loop],
    output_key="academics_feedback"
)

# Retriever: Uses feedback to refine searches iteratively
academics_retriever = LlmAgent(
    name="AcademicsDataRetriever",
    model="gemini-2.5-flash",
    description="Searches for academics data, refining based on critic feedback in loop.",
    before_model_callback=log_agent_entry,
    after_model_callback=log_agent_exit,
    instruction="""
    You are an academics data retriever.
    
    **IF academics_feedback EXISTS:** Address specific gaps
    **IF NO FEEDBACK:** Perform comprehensive searches
    
    **SEARCH STRATEGY:**
    
    1. **Comprehensive Degree Catalog:**
       - Search: "[University] undergraduate majors complete list catalog"
       - Search: "[University] all undergraduate degrees programs offered"
       - Search: "[University] academic catalog undergraduate programs"
       - Search: "[University] bachelor's degree programs full list"
    
    2. **Degree Details & Requirements:**
       - Search: "[University] [Major Name] degree requirements curriculum"
       - Search: "[University] [Major Name] course requirements prerequisites"
       - Search: "[University] [Major Name] program description"
       - For EACH major found, search for specific details
    
    3. **Colleges & Schools:**
       - Search: "[University] undergraduate colleges schools"
       - Search: "[University] college of engineering majors"
       - Search: "[University] school of business majors"
       - Search for each college/school's specific programs
    
    4. **Major Policies:**
       - Search: "[University] impacted majors capped enrollment"
       - Search: "[University] most popular majors enrollment statistics"
       - Search: "[University] change major policy"
       - Search: "[University] internal transfer between colleges"
       - Search: "[University] double major minor requirements"
    
    **OUTPUT FORMAT:**
    
    Your output should contain TWO sections:
    
    ---
    ## RAW RESEARCH DATA
    
    [Include ALL raw text from your searches here. Include source URLs, full paragraphs, major lists, policy descriptions, etc.]
    
    **Sources:**
    - [URL 1]: [Brief description]
    - [URL 2]: [Brief description]
    
    ---
    ## STRUCTURED Q&A SUMMARY
    
    # III. Academics & Major-Specific Data
    
    ## Colleges & Schools
    
    **Q: What are the different undergraduate colleges or schools within the university?**
    A: [List all colleges/schools with number of majors in each]
    
    ## Complete Undergraduate Degree Catalog
    
    **Q: What are ALL undergraduate degrees/majors offered by the university?**
    A: [Comprehensive list organized by college/school]
    
    **College of Engineering:**
    1. [Major 1] - [Brief description, key requirements, credit hours]
    2. [Major 2] - [Brief description, key requirements, credit hours]
    ...
    
    **School of Business:**
    1. [Major 1] - [Brief description, key requirements, credit hours]
    2. [Major 2] - [Brief description, key requirements, credit hours]
    ...
    
    **College of Arts & Sciences:**
    1. [Major 1] - [Brief description, key requirements, credit hours]
    2. [Major 2] - [Brief description, key requirements, credit hours]
    ...
    
    [Continue for ALL colleges/schools and ALL majors]
    
    **Total Undergraduate Majors Offered:** [Number]
    
    ## Degree Details (For Each Major)
    
    **For each major, include:**
    - **Degree Type:** BA/BS/BFA/etc.
    - **Credit Hours Required:** [Number]
    - **Core Requirements:** [List key courses]
    - **Prerequisites:** [List prerequisites]
    - **Special Features:** [Honors programs, study abroad, internships, etc.]
    - **Career Paths:** [Common career outcomes]
    
    ## Major-Specific Admissions
    
    **Q: Do students apply directly to a specific school/major, or to the university as a whole?**
    A: [Explain the application process]
    
    **Q: What are the internal acceptance rates for each college/school (if published)?**
    A: [List rates or state "Data not publicly available"]
    
    **Q: Which majors are designated as 'impacted' or 'capped' (limited enrollment)?**
    A: [List impacted majors with specific enrollment caps]
    
    ## Popular Majors & Enrollment
    
    **Q: What are the top 10 most popular majors by enrollment?**
    A:
    1. [Major 1] - [X students enrolled]
    2. [Major 2] - [X students enrolled]
    ...
    
    **Q: What are alternative majors for competitive programs?**
    A:
    **For Computer Science:**
    - [List alternatives with brief descriptions]
    
    **For Business:**
    - [List alternatives with brief descriptions]
    
    **For Engineering:**
    - [List alternatives with brief descriptions]
    
    ## Academic Flexibility
    
    **Q: How easy or difficult is it to change majors once enrolled?**
    A: [Detailed explanation with GPA requirements and deadlines]
    
    **Q: What is the process to internally transfer between different colleges?**
    A: [Explain process, requirements, and competitiveness]
    
    **Q: Can students pursue double majors or minors?**
    A: [Explain policies, requirements, and popular combinations]
    
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
    - Include academic catalog year in citation
    
    ACADEMICS_FEEDBACK:
    { academics_feedback? }
    """,
    tools=[google_search],
    output_key="raw_academics_data"
)

# Loop Agent: Retrieval and critique only
academics_research_loop = LoopAgent(
    name="AcademicsResearchLoop",
    description="Iterates through data retrieval and critique to ensure complete RAW data.",
    sub_agents=[
        academics_retriever,
        academics_critic
    ],
    max_iterations=3
)

# Main Researcher: Just the loop - raw data stays in state
AcademicsResearcher = academics_research_loop
