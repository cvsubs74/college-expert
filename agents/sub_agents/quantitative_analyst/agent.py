from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.tools import google_search
from ...schemas import CDSTrends

# 1. Retriever Agent: Finds the raw data.
retriever_agent = LlmAgent(
    name="CDSRetrieverAgent",
    model="gemini-2.5-flash",
    description="Finds the Common Data Set files for a college.",
    instruction="""
    You are a research assistant. Your only job is to use the `google_search` tool to find the Common Data Set (CDS) files for the given college for the last 5 years.
    Your search query should be specific, like `"[College Name] Common Data Set 2023-2024"`, `"[College Name] Common Data Set 2022-2023"`, etc., performing multiple searches if necessary to find all 5 years.
    The `google_search` tool will provide the content of the search results directly. Output the raw, combined text from all 5 years.
    """,
    tools=[google_search],
    output_key="raw_cds_text"
)

# 2. Formatter Agent: Structures the raw data.
formatter_agent = LlmAgent(
    name="CDSFormatterAgent",
    model="gemini-2.5-flash",
    description="Analyzes and structures raw CDS text into the CDSTrends schema.",
    instruction="""
    You are a quantitative analyst. You will be given the raw text from 5 years of a college's Common Data Set (CDS). Your task is to perform a detailed time-series analysis and structure the output into the `CDSTrends` JSON schema.

    **CRITICAL WORKFLOW (Chain-of-Thought):**
    You MUST perform the following steps in order.

    **Step 1: Time-Series Data Extraction**
    - Scan the provided raw text.
    - From Section C, extract the following data points for each year: Total Applied, Total Admitted, the full 'Basis for Selection' table (C7), 25th/75th percentile SAT/ACT scores (C9), and Average GPA (C11).
    - Structure this data as a time-series JSON object and then serialize it into a JSON string. This string will be the value for the `time_series_data` field.

    **Step 2: Trend and Acceleration Analysis**
    - Using the time-series data from Step 1, perform the following calculations:
        1. Calculate the Admission Rate for all 5 years.
        2. Calculate the 5-year 'velocity' (total percentage change) for: Admission Rate, 75th percentile SAT, and Average GPA.
        3. Calculate the 'acceleration' (the year-over-year rate of change in velocity) for the same metrics.

    **Step 3: Final Report Synthesis**
    - Based on your calculations, provide a `trend_summary` answering: What is the 5-year trajectory for this college's selectivity?
    - Provide an `acceleration_analysis` answering: Is the pace of this change increasing, decreasing, or static?
    - Based only on the most recent CDS C7 table, create a `c7_priorities` ranked list of the college's admission priorities.

    **FINAL OUTPUT:**
    - Your final output MUST be a single, valid JSON object that conforms perfectly to the `CDSTrends` schema.
    """,
    output_schema=CDSTrends,
    output_key="cds_trends"
)

# 3. Sequential Agent: Chains the retriever and formatter.
QuantitativeAnalyst = SequentialAgent(
    name="QuantitativeAnalyst",
    description="A sequential agent that first retrieves raw CDS data and then formats it into a structured analysis.",
    sub_agents=[
        retriever_agent,
        formatter_agent
    ]
)
