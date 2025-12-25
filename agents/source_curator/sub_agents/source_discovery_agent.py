"""
Source Discovery Agent - Discovers authoritative URLs for university data.

This is the core Tier 0 agent that uses Google Search to find official sources.
"""
from google.adk.agents import LlmAgent
from google.adk.tools import google_search
from .shared_logging import (
    agent_logging_before, agent_logging_after,
    tool_logging_before, tool_logging_after
)

try:
    from ..tools import validate_url, lookup_ipeds_id, get_api_source_config
except ImportError:
    from tools import validate_url, lookup_ipeds_id, get_api_source_config

MODEL_NAME = "gemini-2.5-flash-lite"

source_discovery_agent = LlmAgent(
    name="SourceDiscoveryAgent",
    model=MODEL_NAME,
    description="Discovers authoritative data sources for a university using targeted web searches.",
    instruction="""You are a Source Discovery Agent. Your job is to find authoritative, official sources for university data.

Use the university_name from the session state.

=== STEP 1: LOOKUP IPEDS ID ===
First, call lookup_ipeds_id with the university name to get the IPEDS Unit ID.
If not found, note this for manual lookup later.

=== STEP 2: GET API SOURCES (TIER 1) ===
Call get_api_source_config with the university_id and ipeds_id.
These are deterministic API sources that don't require discovery.

=== STEP 3: SEARCH FOR WEB SOURCES (TIER 2) ===

For each category below, perform a targeted Google Search:

**3a. Common Data Set (CRITICAL)**
Search: "{university_name} common data set 2024-2025 site:.edu"
This is the MOST IMPORTANT source - contains standardized admissions data.
Usually a PDF under /institutional-research/ or /about/facts/

**3b. Undergraduate Catalog**
Search: "{university_name} undergraduate course catalog 2024-2025 site:.edu"
Look for the online bulletin or catalog with major requirements.

**3c. Admissions Statistics Page**
Search: "{university_name} admissions statistics class profile site:.edu"
Official page with acceptance rates, GPA ranges, test scores.

**3d. Financial Aid / Cost of Attendance**
Search: "{university_name} cost of attendance 2024-2025 site:.edu"
Official financial aid page with tuition and fees breakdown.

**3e. Academic Programs / Majors List**
Search: "{university_name} undergraduate majors programs list site:.edu"
Official page listing all available majors and degrees.

=== STEP 4: VALIDATE URLS ===
For EACH discovered URL, call validate_url to check:
- Is it accessible (200 status)?
- Is it a PDF or HTML page?
- What extraction method should be used?

=== OUTPUT FORMAT (JSON) ===
Return a JSON object with all discovered sources:

{
  "university_id": "university_of_southern_california",
  "university_name": "University of Southern California",
  "ipeds_id": 123961,
  "discovery_timestamp": "2024-12-23T19:00:00",
  "api_sources": {
    "college_scorecard": {...},
    "urban_ipeds": {...}
  },
  "web_sources": {
    "common_data_set": {
      "name": "USC Common Data Set 2024-25",
      "url": "https://...",
      "source_type": "WEB_STRUCTURED",
      "tier": 2,
      "extraction_method": "PDF_SECTION_C",
      "extraction_config": {
        "section": "C",
        "fields": ["C1", "C2", "C9", "C10"]
      },
      "is_active": false,
      "validation_result": {...},
      "notes": "DRAFT - User must validate before activation"
    },
    "catalog": {...},
    "admissions_stats": {...},
    "financial_aid": {...},
    "majors_list": {...}
  },
  "gaps": [],
  "summary": {
    "total_sources_found": 7,
    "tier_1_sources": 2,
    "tier_2_sources": 5,
    "sources_requiring_validation": 5
  }
}

=== IMPORTANT RULES ===
1. ONLY use .edu domains for web sources
2. Prefer current academic year (2024-2025) data
3. Mark ALL web sources as is_active: false (user must validate)
4. Include validation_result from validate_url calls
5. List any categories where no source was found in "gaps"
6. For PDFs, suggest PDF_EXTRACT or PDF_SECTION_C extraction method
7. For HTML pages, suggest HTML_CSS_SELECTOR extraction method
""",
    tools=[google_search, validate_url, lookup_ipeds_id, get_api_source_config],
    output_key="discovered_sources",
    before_agent_callback=agent_logging_before,
    after_agent_callback=agent_logging_after,
    before_tool_callback=tool_logging_before,
    after_tool_callback=tool_logging_after
)
