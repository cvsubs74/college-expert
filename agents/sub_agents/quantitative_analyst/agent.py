from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.tools import google_search
from ...schemas import CDSTrends

# 1. Retriever Agent: Finds the raw data.
retriever_agent = LlmAgent(
    name="AdmissionsStatsRetriever",
    model="gemini-2.5-flash",
    description="Searches for comprehensive admissions statistics from CDS and university sources.",
    instruction="""
    You are a research assistant. Your job is to find comprehensive admissions statistics for the given university.
    
    **SEARCH STRATEGY (perform multiple searches):**
    
    1. **Common Data Set (CDS) - Last 5 Years:**
       - Search: "[University Name] Common Data Set 2024-2025"
       - Search: "[University Name] Common Data Set 2023-2024"
       - Search: "[University Name] Common Data Set 2022-2023"
       - Search: "[University Name] Common Data Set 2021-2022"
       - Search: "[University Name] Common Data Set 2020-2021"
       - Extract: Acceptance rates, test scores, GPA data from Section C
    
    2. **GPA Statistics (if not in CDS):**
       - Search: "[University Name] average GPA admitted students"
       - Search: "[University Name] admissions statistics GPA"
       - For UC schools specifically, also search:
         * "[UC School] UC weighted GPA admitted students"
         * "[UC School] UC capped GPA admitted students"
         * "[UC School] freshman profile GPA"
    
    3. **Official University Sources:**
       - Search: "[University Name] freshman profile admitted students"
       - Search: "[University Name] class profile statistics"
       - Look for official admissions pages with detailed statistics
    
    **OUTPUT:**
    Combine all raw text from all searches. Include source URLs when available.
    """,
    tools=[google_search],
    output_key="raw_admissions_data"
)

# 2. Formatter Agent: Structures the raw data.
formatter_agent = LlmAgent(
    name="AdmissionsStatsFormatter",
    model="gemini-2.5-flash",
    description="Analyzes and structures admissions statistics into the CDSTrends schema.",
    instruction="""
    You are a quantitative analyst. You will be given raw admissions data from CDS files and university sources.
    Your task is to extract and structure comprehensive admissions statistics.

    **CRITICAL WORKFLOW:**

    **Step 1: Time-Series Data Extraction (from CDS)**
    - Scan the CDS data for the last 5 years
    - Extract for each year:
      * Total Applied
      * Total Admitted
      * Admission Rate (calculate if not stated)
      * 25th/75th percentile SAT/ACT scores (Section C9)
      * Average GPA if available (Section C11)
      * Basis for Selection table (Section C7)
    - Structure as time-series JSON and serialize to string for `time_series_data` field

    **Step 2: GPA Statistics Extraction**
    - Extract GPA data from all sources:
      * `average_unweighted_gpa`: Look for "average unweighted GPA" or "mean unweighted GPA"
      * `average_weighted_gpa`: Look for "average weighted GPA" or "mean weighted GPA"
      * `uc_weighted_gpa`: For UC schools, look for "UC weighted GPA" or "UC GPA"
      * `uc_capped_gpa`: For UC schools, look for "UC capped weighted GPA" or "capped GPA"
      * `gpa_ranges`: Look for GPA ranges like "middle 50%: 3.7-4.0" or "25th-75th percentile"
    - If data not found, set to None
    - Use EXACT values from sources, do not calculate

    **Step 3: Trend Analysis**
    - Calculate 5-year trends:
      * Admission rate change
      * Test score changes (75th percentile)
      * GPA changes if available
    - Provide `trend_summary`: What is the 5-year trajectory for selectivity?
    - Provide `acceleration_analysis`: Is the pace of change increasing, decreasing, or static?

    **Step 4: Priorities and Sources**
    - From most recent CDS C7 table, create `c7_priorities`: ranked list of admission priorities
    - List all `data_sources` used (e.g., "CDS 2024-2025, UC Berkeley Freshman Profile, etc.")

    **IMPORTANT:**
    - Use EXACT GPA values from sources - do not calculate or estimate
    - If GPA data is not available, set those fields to None
    - For UC schools, prioritize finding UC-specific GPA metrics
    - Include source information for credibility

    **FINAL OUTPUT:**
    - Your output MUST be a valid JSON object conforming to the `CDSTrends` schema
    """,
    output_schema=CDSTrends,
    output_key="admissions_stats"
)

# 3. Sequential Agent: Chains the retriever and formatter.
QuantitativeAnalyst = SequentialAgent(
    name="QuantitativeAnalyst",
    description="Retrieves comprehensive admissions statistics from CDS and university sources, including various GPA metrics, test scores, and acceptance rates.",
    sub_agents=[
        retriever_agent,
        formatter_agent
    ]
)
