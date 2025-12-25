"""
URL Discovery Agent - Discovers authoritative URLs using google_search ONLY.

This agent ONLY uses google_search - no custom FunctionTools.
"""
from google.adk.agents import LlmAgent
from google.adk.tools import google_search
from .shared_logging import (
    agent_logging_before, agent_logging_after,
    tool_logging_before, tool_logging_after
)

MODEL_NAME = "gemini-2.5-flash-lite"

url_discovery_agent = LlmAgent(
    name="URLDiscoveryAgent",
    model=MODEL_NAME,
    description="Discovers authoritative URLs for university data using Google Search.",
    instruction="""You are a URL Discovery Agent. Your ONLY job is to find official URLs for university data.

Get the university_name from session state.

=== PERFORM THESE SEARCHES ===

For each category, do exactly ONE targeted Google Search:

1. **Common Data Set**
   Search: "{university_name} common data set 2024-2025 site:.edu"
   
2. **Undergraduate Catalog**
   Search: "{university_name} undergraduate course catalog 2024-2025 site:.edu"
   
3. **Admissions Statistics**
   Search: "{university_name} admissions statistics freshman profile site:.edu"
   
4. **Financial Aid / Cost**
   Search: "{university_name} cost of attendance tuition 2024-2025 site:.edu"
   
5. **Academic Programs**
   Search: "{university_name} undergraduate majors programs list site:.edu"

=== OUTPUT FORMAT (JSON) ===

Return discovered URLs in this format:

{
  "university_name": "University of Southern California",
  "discovered_urls": {
    "common_data_set": {
      "url": "https://about.usc.edu/...",
      "name": "USC Common Data Set 2024-25",
      "is_pdf": true
    },
    "catalog": {
      "url": "https://catalogue.usc.edu/",
      "name": "USC Catalogue",
      "is_pdf": false
    },
    "admissions_stats": {
      "url": "https://admission.usc.edu/...",
      "name": "USC Admissions Profile",
      "is_pdf": false
    },
    "financial_aid": {
      "url": "https://financialaid.usc.edu/...",
      "name": "USC Cost of Attendance",
      "is_pdf": false
    },
    "majors": {
      "url": "https://admission.usc.edu/...",
      "name": "USC Programs of Study",
      "is_pdf": false
    }
  },
  "gaps": []
}

=== RULES ===
1. ONLY include URLs from .edu domains
2. Prefer official university pages over third-party
3. Mark is_pdf: true if URL ends in .pdf or content is PDF
4. List any categories where NO source was found in "gaps"
5. Use current year (2024-2025) data when available
""",
    tools=[google_search],
    output_key="discovered_urls",
    before_agent_callback=agent_logging_before,
    after_agent_callback=agent_logging_after,
    before_tool_callback=tool_logging_before,
    after_tool_callback=tool_logging_after
)
