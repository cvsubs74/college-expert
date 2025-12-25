"""
YAML Generator Agent - Converts discovered sources to YAML configuration file.
"""
import json
import yaml
from pathlib import Path
from datetime import datetime
import logging
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool, ToolContext
from .shared_logging import agent_logging_before, agent_logging_after

logger = logging.getLogger(__name__)
MODEL_NAME = "gemini-2.5-flash-lite"

# Get the sources directory relative to this module
SOURCES_DIR = Path(__file__).parent.parent / "sources" / "universities"


def write_yaml_config(
    tool_context: ToolContext,
    university_id: str,
    yaml_content: str
) -> dict:
    """
    Write the YAML configuration file for a university.
    
    Args:
        university_id: Standardized university ID (used for filename)
        yaml_content: Complete YAML content as a string
    
    Returns:
        Dictionary with file path and status
    """
    try:
        # Ensure directory exists
        SOURCES_DIR.mkdir(parents=True, exist_ok=True)
        
        # Create file path
        filename = f"{university_id}.yaml"
        file_path = SOURCES_DIR / filename
        
        # Write the file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(yaml_content)
        
        logger.info(f"[YAML Generator] Wrote config to: {file_path}")
        
        # Store in session state
        tool_context.state["yaml_output_path"] = str(file_path)
        
        return {
            "success": True,
            "file_path": str(file_path),
            "filename": filename,
            "message": f"YAML config saved to {file_path}"
        }
    except Exception as e:
        logger.error(f"[YAML Generator] Error writing file: {e}")
        return {
            "success": False,
            "error": str(e)
        }


# Create tool from function
write_yaml_tool = FunctionTool(func=write_yaml_config)


yaml_generator_agent = LlmAgent(
    name="YAMLGeneratorAgent",
    model=MODEL_NAME,
    description="Converts discovered sources into a YAML configuration file.",
    instruction="""Convert the discovered sources from {discovered_sources} into a properly formatted YAML configuration file.

=== YAML STRUCTURE ===

The YAML file should have this exact structure:

```yaml
university_id: university_of_southern_california
official_name: University of Southern California
ipeds_id: 123961

discovery_metadata:
  discovered_at: "2024-12-23"
  discovery_agent_version: "1.0"
  requires_user_validation: true

sources:
  # Tier 1: API Sources (Deterministic)
  admissions_api:
    primary:
      name: "College Scorecard API"
      source_type: API
      tier: 1
      url: "https://api.data.gov/ed/collegescorecard/v1/schools"
      extraction_method: API_JSON
      extraction_config:
        ipeds_id: 123961
        api_key_env: DATA_GOV_API_KEY
      is_active: true
      notes: "Tier 1 - deterministic API source"
  
  demographics_api:
    primary:
      name: "Urban Institute IPEDS API"
      source_type: API
      tier: 1
      url: "https://educationdata.urban.org/api/v1/college-university/ipeds"
      extraction_method: API_JSON
      extraction_config:
        unitid: 123961
      is_active: true
      notes: "Tier 1 - deterministic API source"
  
  # Tier 2: Curated Web Sources
  common_data_set:
    primary:
      name: "USC Common Data Set 2024-25"
      source_type: WEB_STRUCTURED
      tier: 2
      url: "https://..."
      extraction_method: PDF_SECTION_C
      extraction_config:
        section: C
        fields: [C1, C2, C9, C10]
      is_active: false  # ⚠️ DRAFT - User must validate
      last_validated: null
      notes: "DRAFT - Requires user validation"
    fallback: []
  
  catalog:
    primary:
      name: "USC Undergraduate Catalog"
      source_type: WEB_STRUCTURED
      tier: 2
      url: "https://..."
      extraction_method: CATALOG_SCRAPER
      extraction_config: {}
      is_active: false
      last_validated: null
      notes: "DRAFT - Requires user validation"
  
  admissions_stats:
    primary:
      name: "USC Admissions Statistics"
      source_type: WEB_STRUCTURED
      tier: 2
      url: "https://..."
      extraction_method: HTML_CSS_SELECTOR
      extraction_config:
        selectors: {}
      is_active: false
      last_validated: null
      notes: "DRAFT - Requires user validation"
  
  financial_aid:
    primary:
      name: "USC Cost of Attendance"
      source_type: WEB_STRUCTURED
      tier: 2
      url: "https://..."
      extraction_method: HTML_CSS_SELECTOR
      extraction_config: {}
      is_active: false
      last_validated: null
      notes: "DRAFT - Requires user validation"
  
  majors:
    primary:
      name: "USC Academic Programs"
      source_type: WEB_STRUCTURED
      tier: 2
      url: "https://..."
      extraction_method: HTML_CSS_SELECTOR
      extraction_config: {}
      is_active: false
      last_validated: null
      notes: "DRAFT - Requires user validation"

notes:
  - "Generated by Source Curator Agent on 2024-12-23"
  - "All Tier 2 web sources marked DRAFT - user must validate before activation"
  - "Set is_active: true after manual verification of each URL"
  - "Update last_validated date after verification"
```

=== INSTRUCTIONS ===

1. Extract sources from {discovered_sources}
2. Format as proper YAML with correct indentation (2 spaces)
3. Include ALL discovered sources (both API and web)
4. Mark Tier 1 API sources as is_active: true (they're deterministic)
5. Mark ALL Tier 2 web sources as is_active: false
6. Include helpful notes and comments

7. CALL write_yaml_config with:
   - university_id: the standardized university ID
   - yaml_content: the complete YAML string

8. After successful write, output a summary of what was created.
""",
    tools=[write_yaml_tool],
    output_key="yaml_result",
    before_agent_callback=agent_logging_before,
    after_agent_callback=agent_logging_after
)
