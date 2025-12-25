"""
Entity Discovery Agent - Discovers comprehensive entity list using Google Search

Uses SequentialAgent pattern:
1. EntitySearcher - Uses google_search tool, stores results in output_key
2. EntityFormatter - Reads from state, outputs structured schema
"""
from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.tools import google_search
from pydantic import BaseModel, Field
from typing import List

MODEL_NAME = "gemini-2.5-flash"


# ============================================================================
# Pydantic Schemas for Structured Output
# ============================================================================

class EntityItem(BaseModel):
    """An entity to mine data for"""
    name: str = Field(description="Name of the entity")
    slug: str = Field(description="Lowercase underscore slug")
    priority: str = Field(description="Priority: high, medium, or low")


class EntityCategory(BaseModel):
    """A category of entities"""
    name: str = Field(description="Category name")
    description: str = Field(description="Category description")
    entities: List[EntityItem] = Field(description="Entities in this category")


class EntityDiscoveryOutput(BaseModel):
    """Output from entity discovery"""
    total_count: int = Field(description="Total number of entities discovered")
    categories: List[EntityCategory] = Field(description="Entities grouped by category")


# ============================================================================
# Step 1: Entity Searcher - Uses tools to search for entities
# ============================================================================

entity_searcher_agent = LlmAgent(
    name="EntitySearcher",
    model=MODEL_NAME,
    description="Searches for comprehensive entity lists using Google Search.",
    instruction="""You are an Entity Search Agent. Your job is to build a comprehensive, REAL list of entities to mine data for ANY research goal.

You will receive:
- goal: The research goal
- entity_type: Type of entity (e.g., "university", "company", "hospital")

=== YOUR TASK ===

Use Google Search to find REAL, AUTHORITATIVE lists of entities.

=== STEP 1: CONSTRUCT SEARCH QUERIES ===

Based on entity_type, construct search queries:
- "top [entity_type_plural] list [region]"
- "[entity_type_plural] rankings [year]"
- "comprehensive list [entity_type_plural]"

=== STEP 2: EXTRACT ENTITIES ===

From search results, extract 30-50 REAL entity names.
Only include entities that appear in search results - NO FABRICATION.

=== STEP 3: CATEGORIZE ===

Create 4-6 logical categories based on entity characteristics:
- By size/prominence: "Major", "Mid-Tier", "Regional"
- By type: "Public", "Private", "Nonprofit"
- By region: "East Coast", "West Coast", etc.

=== STEP 4: ASSIGN PRIORITY ===

- high: Top-ranked entities (10-15)
- medium: Well-known (15-20)
- low: Less prominent (remaining)

=== OUTPUT FORMAT ===

Output JSON:
{
  "total_count": 35,
  "categories": [
    {
      "name": "Category Name",
      "description": "Description",
      "entities": [
        {"name": "Entity Name", "slug": "entity_name", "priority": "high"}
      ]
    }
  ]
}

=== CRITICAL ===

1. GOOGLE SEARCH ONLY - every entity must come from search results
2. NO HALLUCINATION - only include real entities found in search
3. 30-50 ENTITIES total
""",
    tools=[google_search],
    output_key="entity_search_results"
)


# ============================================================================
# Step 2: Entity Formatter - Converts search results to structured output
# ============================================================================

entity_formatter_agent = LlmAgent(
    name="EntityFormatter",
    model=MODEL_NAME,
    description="Formats entity search results into structured output.",
    instruction="""You are an Entity Formatter Agent. Your job is to take the raw search results and format them into a clean, structured output.

Read the entity search results from: {entity_search_results}

Parse the JSON data and ensure it matches the required output schema.

Output the final structured data with:
- total_count: integer count of all entities
- categories: array of category objects, each with name, description, and entities array

Each entity must have: name, slug, and priority (high/medium/low)

Do NOT call any tools - just format the existing data.""",
    output_schema=EntityDiscoveryOutput,
    output_key="entity_discovery_result"
)


# ============================================================================
# Combined Sequential Agent
# ============================================================================

entity_discovery_agent = SequentialAgent(
    name="EntityDiscoveryAgent",
    description="Discovers comprehensive entity lists for any research goal.",
    sub_agents=[entity_searcher_agent, entity_formatter_agent]
)
