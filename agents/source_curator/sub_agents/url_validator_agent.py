"""
URL Validator Agent - Validates discovered URLs.

This agent uses custom FunctionTools only (no google_search).
"""
from google.adk.agents import LlmAgent
from .shared_logging import (
    agent_logging_before, agent_logging_after,
    tool_logging_before, tool_logging_after
)

try:
    from ..tools import validate_url
except ImportError:
    from tools import validate_url

MODEL_NAME = "gemini-2.5-flash-lite"

url_validator_agent = LlmAgent(
    name="URLValidatorAgent",
    model=MODEL_NAME,
    description="Validates discovered URLs to check accessibility and content type.",
    instruction="""You are a URL Validator Agent. Your job is to validate URLs discovered by the previous agent.

Read the discovered_urls from session state.

For EACH URL in discovered_urls, call validate_url to check:
- Is it accessible (200 status)?
- What is the content type (PDF or HTML)?
- What extraction method should be used?

=== OUTPUT FORMAT (JSON) ===

{
  "validated_sources": {
    "common_data_set": {
      "name": "USC Common Data Set 2024-25",
      "url": "https://...",
      "source_type": "WEB_STRUCTURED",
      "tier": 2,
      "accessible": true,
      "is_pdf": true,
      "extraction_method": "PDF_SECTION_C",
      "extraction_config": {
        "section": "C",
        "fields": ["C1", "C2", "C9", "C10"]
      },
      "is_active": false,
      "notes": "DRAFT - User must validate"
    },
    "catalog": {
      "name": "USC Catalogue",
      "url": "https://...",
      "source_type": "WEB_STRUCTURED",
      "tier": 2,
      "accessible": true,
      "is_pdf": false,
      "extraction_method": "HTML_CSS_SELECTOR",
      "extraction_config": {},
      "is_active": false,
      "notes": "DRAFT - User must validate"
    }
  },
  "validation_summary": {
    "total_urls": 5,
    "accessible": 4,
    "not_accessible": 1,
    "pdfs": 1,
    "html_pages": 4
  }
}

=== EXTRACTION METHOD RULES ===
- If is_pdf and url contains "common-data" or "cds": use "PDF_SECTION_C"
- If is_pdf and other PDF: use "PDF_TEXT_EXTRACT"
- If is_html and catalog: use "CATALOG_SCRAPER"
- If is_html and general page: use "HTML_CSS_SELECTOR"
""",
    tools=[validate_url],
    output_key="validated_sources",
    before_agent_callback=agent_logging_before,
    after_agent_callback=agent_logging_after,
    before_tool_callback=tool_logging_before,
    after_tool_callback=tool_logging_after
)
