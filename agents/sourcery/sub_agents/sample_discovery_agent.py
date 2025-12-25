"""
Sample Discovery Agent - Discovers sample entities using Google Search

Uses SequentialAgent pattern:
1. SampleSearcher - Uses google_search tool, stores results in output_key
2. SampleFormatter - Reads from state, outputs structured schema
"""
from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.tools import google_search
from pydantic import BaseModel, Field
from typing import List, Optional

MODEL_NAME = "gemini-2.5-flash"


# ============================================================================
# Pydantic Schemas for Structured Output
# ============================================================================

class SampleSource(BaseModel):
    """A data source for a sample entity"""
    name: str = Field(description="Descriptive name of the source")
    type: str = Field(description="Source type: PDF, API, or WEB")
    url: str = Field(description="URL of the source")
    fields_covered: List[str] = Field(description="Schema fields this source covers")


class SampleEntity(BaseModel):
    """A sample entity with its data sources"""
    name: str = Field(description="Name of the entity")
    slug: str = Field(description="Lowercase underscore slug")
    domain: Optional[str] = Field(default=None, description="Domain/website if applicable")
    identifier: Optional[str] = Field(default=None, description="Unique identifier if found")
    sources: List[SampleSource] = Field(description="Data sources for this entity")


class SampleDiscoveryOutput(BaseModel):
    """Output from sample discovery"""
    entity_type: str = Field(description="Type of entity (e.g., university, company)")
    entity_type_plural: str = Field(description="Plural form of entity type")
    samples: List[SampleEntity] = Field(description="5 diverse sample entities with sources")


# ============================================================================
# Step 1: Sample Searcher - Uses tools to search for samples
# ============================================================================

sample_searcher_agent = LlmAgent(
    name="SampleSearcher",
    model=MODEL_NAME,
    description="Searches for sample entities and their data sources using Google Search.",
    instruction="""You are a Sample Search Agent. Your job is to find 5 diverse, REAL sample entities and their actual data sources for a research goal.

You will receive in the user's message:
- goal: The data mining research goal
- schema: The JSON schema defining what data fields to collect

=== STEP 1: DETERMINE ENTITY TYPE ===

From the goal text, infer what type of entity is being researched:
- "universities" / "colleges" → entity_type: "university"
- "companies" / "businesses" → entity_type: "company"
- "cities" / "municipalities" → entity_type: "city"
- etc.

=== STEP 2: FIND SAMPLE ENTITIES ===

Use Google Search to find 5 REAL, DIVERSE examples.

Search: "top [entity_type_plural] list" OR "[entity_type_plural] rankings"

From search results, select 5 DIVERSE entities.

=== STEP 3: DISCOVER SOURCES FOR EACH SAMPLE ===

For EACH sample entity, search for data sources:
- "ENTITY_NAME admissions statistics" for admissions fields
- "ENTITY_NAME financial data" for financial fields
- etc.

Identify Source Types:
- URLs ending in .pdf → type: "PDF"
- API endpoints → type: "API"
- Everything else → type: "WEB"

=== OUTPUT FORMAT ===

Output your findings as a JSON object with this structure:
{
  "entity_type": "inferred_type",
  "entity_type_plural": "inferred_plural",
  "samples": [
    {
      "name": "Entity Name",
      "slug": "entity_name",
      "domain": "example.edu",
      "identifier": "ID if found",
      "sources": [
        {"name": "Source Name", "type": "WEB", "url": "https://...", "fields_covered": ["field1"]}
      ]
    }
  ]
}

=== CRITICAL RULES ===

1. Use ONLY google_search tool - every entity and URL must come from search results
2. NO HALLUCINATION - only include URLs you found in search results
3. RETURN EXACTLY 5 SAMPLES
""",
    tools=[google_search],
    output_key="sample_search_results"
)


# ============================================================================
# Step 2: Sample Formatter - Converts search results to structured output
# ============================================================================

sample_formatter_agent = LlmAgent(
    name="SampleFormatter",
    model=MODEL_NAME,
    description="Formats sample search results into structured output.",
    instruction="""You are a Sample Formatter Agent. Your job is to take the raw search results and format them into a clean, structured output.

Read the sample search results from: {sample_search_results}

Parse the JSON data and ensure it matches the required output schema.

If the data is already well-structured, pass it through.
If there are any formatting issues, clean them up.

Output the final structured data with:
- entity_type: string
- entity_type_plural: string  
- samples: array of 5 sample entities, each with name, slug, domain, identifier, and sources array

Do NOT call any tools - just format the existing data.""",
    output_schema=SampleDiscoveryOutput,
    output_key="sample_discovery_result"
)


# ============================================================================
# Combined Sequential Agent
# ============================================================================

sample_discovery_agent = SequentialAgent(
    name="SampleDiscoveryAgent",
    description="Discovers sample entities with sources for any research goal.",
    sub_agents=[sample_searcher_agent, sample_formatter_agent]
)
