"""
Career Outcomes Analyst Agent

This agent searches the knowledge base for career outcomes data including:
- Employment rates and salary data
- Top employers and industries
- Common job titles
- Graduate school placement
- Career services and support
"""

from google.adk.agents import LlmAgent, SequentialAgent
from google.genai import types
from ...schemas.schemas import CareerOutcomesData
from ...tools.file_search_tools import search_knowledge_base


# 1. Retriever Agent: Searches knowledge base for career outcomes data
retriever_agent = LlmAgent(
    name="career_outcomes_retriever",
    model="gemini-2.5-flash",
    description="Searches the knowledge base for career outcomes, employment statistics, and career services information.",
    generate_content_config=types.GenerateContentConfig(
        temperature=0.1
    ),
    instruction="""
    You are a career outcomes data retriever. Your job is to search the knowledge base for career-related information.
    
    **SEARCH STRATEGY:**
    1. Search for: "[university name] career outcomes"
    2. Search for: "[university name] [program/major] employment statistics"
    3. Search for: "[university name] career services"
    4. Search for: "[university name] salary data graduates"
    5. Search for: "[university name] top employers"
    
    **WHAT TO LOOK FOR:**
    - Employment rates (e.g., "95% employed within 6 months")
    - Salary data (median, average, ranges)
    - Top employers hiring graduates
    - Common industries and job titles
    - Graduate school placement rates
    - Career center services and resources
    - Notable alumni outcomes
    - Internship and co-op programs
    
    **OUTPUT:**
    Return all relevant information you find. If data is limited, explicitly state what's missing.
    Store your findings in the output_key for the formatter to process.
    """,
    tools=[search_knowledge_base],
    output_key="raw_career_data"
)


# 2. Formatter Agent: Structures the raw data into CareerOutcomesData schema
formatter_agent = LlmAgent(
    name="career_outcomes_formatter",
    model="gemini-2.5-flash",
    description="Formats raw career outcomes data into a structured analysis.",
    generate_content_config=types.GenerateContentConfig(
        temperature=0.2
    ),
    instruction="""
    You are a career outcomes data formatter. You receive raw career data and structure it.
    
    **YOUR TASK:**
    1. Extract employment rates (e.g., "95% within 6 months")
    2. Extract median/average salaries (e.g., "$85,000")
    3. List top employers (companies that hire graduates)
    4. List common industries (tech, finance, consulting, etc.)
    5. List common job titles (Software Engineer, Analyst, etc.)
    6. Extract graduate school rates if mentioned
    7. Summarize career services available
    8. Note any notable outcomes or achievements
    9. Assess data availability: "Comprehensive", "Partial", or "Limited"
    10. Write an overall summary
    
    **DATA AVAILABILITY ASSESSMENT:**
    - "Comprehensive": Has employment rate, salary data, employers, and industries
    - "Partial": Has some data but missing key metrics
    - "Limited": Very little or no specific career data available
    
    **IF DATA IS LIMITED:**
    - Set data_availability to "Limited"
    - In summary, explicitly state: "Career outcomes data is not available in the knowledge base for this program."
    - Leave optional fields as None or empty lists
    - Do NOT make up data
    
    **FINAL OUTPUT:**
    Your output MUST be a valid JSON object conforming to the CareerOutcomesData schema.
    """,
    output_schema=CareerOutcomesData,
    output_key="career_outcomes"
)


# 3. Sequential Agent: Chains retriever and formatter
CareerOutcomesAnalyst = SequentialAgent(
    name="CareerOutcomesAnalyst",
    description="Analyzes career outcomes, employment statistics, and career services for university programs.",
    sub_agents=[
        retriever_agent,
        formatter_agent
    ]
)
