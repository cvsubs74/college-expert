"""
Structure Discovery Agent - Analyzes sample sources to derive patterns

Analyzes the 5 sample entities and their sources to derive:
- Universal sources (same for all entities)
- Parametric sources (URL patterns)
- Entity-specific discovery (no pattern)
"""
from google.adk.agents import LlmAgent
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

MODEL_NAME = "gemini-2.5-flash"

class SourcePattern(BaseModel):
    name: str
    type: str  # API, PDF, WEB
    base_url: Optional[str] = None
    url_pattern: Optional[str] = None
    entity_lookup_param: Optional[str] = None
    required_variables: Optional[List[str]] = None
    discovery_query: Optional[str] = None
    api_key_required: bool = False
    fields_covered: List[str]

class EntitySpecificDiscovery(BaseModel):
    method: str = "web_search"
    queries: List[str]

class SourcePatterns(BaseModel):
    universal: List[Dict[str, Any]] = Field(default_factory=list)
    parametric: List[Dict[str, Any]] = Field(default_factory=list)
    entity_specific_discovery: Optional[Dict[str, Any]] = None

class StructureDiscoveryOutput(BaseModel):
    entity_type: str
    source_patterns_json: str = Field(description="Source patterns as JSON string")
    required_identifiers: List[str]
    pattern_confidence: str  # high, medium, low

structure_discovery_agent = LlmAgent(
    name="StructureDiscoveryAgent",
    model=MODEL_NAME,
    description="Analyzes sample source mappings to derive generalized YAML patterns.",
    instruction="""You are a Structure Discovery Agent. Your job is to analyze 5 sample entities and their sources to derive generalizable patterns.

You will receive in the user prompt:
- samples: 5 sample entities with their discovered sources
- entity_type: Type of entity
- goal: The research goal

Your task:
Analyze the sources across all 5 samples and categorize them into:

**1. UNIVERSAL SOURCES**: Same URL/API works for all entities
   - Example: Government API that accepts entity ID as parameter
   - Base URL + lookup parameter pattern

**2. PARAMETRIC SOURCES**: URL follows a pattern with entity-specific parts
   - Example: DOMAIN/data/report_YEAR.pdf
   - URL template with variable substitution

**3. ENTITY-SPECIFIC DISCOVERY**: No pattern, must discover per entity
   - Example: Unique research centers, special reports
   - Requires web search per entity

=== ANALYSIS PROCESS ===

1. Examine all source URLs across the 5 samples
2. Look for:
   - Exact same base URLs (→ universal)
   - Similar URL structures with only specific parts changing (→ parametric)
   - Completely unique URLs with no pattern (→ entity-specific)

3. For universal sources:
   - Extract base URL
   - Identify lookup parameter
   - Note API key requirements

4. For parametric sources:
   - Create URL pattern with VARIABLE placeholders
   - Identify required variables (domain, year, id, etc.)
   - Note discovery query if pattern isn't obvious

5. For entity-specific:
   - Define search query templates
   - Note that these require per-entity discovery

=== OUTPUT FORMAT (JSON) ===

{
  "entity_type": "<type>",
  "source_patterns": {
    "universal": [
      {
        "name": "...",
        "type": "API|PDF|WEB",
        "base_url": "https://...",
        "entity_lookup_param": "...",
        "api_key_required": true|false,
        "fields_covered": ["field1", "field2"]
      }
    ],
    "parametric": [
      {
        "name": "...",
        "type": "API|PDF|WEB",
        "url_pattern": "https://DOMAIN/path/VARIABLE",
        "required_variables": ["domain", "variable"],
        "discovery_query": "search query to find the URL",
        "fields_covered": ["field1", "field2"]
      }
    ],
    "entity_specific_discovery": {
      "method": "web_search",
      "queries": [
        "ENTITY_NAME specific data",
        "ENTITY_NAME unique resource"
      ]
    }
  },
  "required_identifiers": ["domain", "id", ...],
  "pattern_confidence": "high|medium|low"
}

=== CRITICAL RULES ===

1. **PATTERN RECOGNITION**: Only create patterns if they actually exist across samples
2. **HONEST ASSESSMENT**: If no pattern exists, mark as entity-specific
3. **COMPLETE COVERAGE**: Account for all source types from samples
4. **CONFIDENCE RATING**: Rate how confident you are in the patterns
""",
    tools=[],  # Analyzes provided data, doesn't search
    output_schema=StructureDiscoveryOutput,
    output_key="structure_discovery_result"
)
