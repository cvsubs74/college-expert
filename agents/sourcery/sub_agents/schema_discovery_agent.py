"""
Schema Discovery Agent - Analyzes research goal and generates JSON Schema

Works for ANY goal - completely generic with zero hardcoding.
Does NOT use Google Search - pure schema design based on goal analysis.
"""
from google.adk.agents import LlmAgent
from pydantic import BaseModel, Field
from typing import List

MODEL_NAME = "gemini-2.5-flash"

class SchemaGenerationOutput(BaseModel):
    """Output from schema generation"""
    goal: str = Field(description="The research goal")
    entity_type: str = Field(description="Type of entity inferred from goal")
    entity_type_plural: str = Field(description="Plural form of entity type")
    schema_json: str = Field(description="Generated JSON Schema as a MINIFIED single-line string with no newlines")
    categories: List[str] = Field(description="Data category names identified")

schema_discovery_agent = LlmAgent(
    name="SchemaDiscoveryAgent",
    model=MODEL_NAME,
    description="Analyzes research goal and generates appropriate JSON Schema for data collection.",
    instruction="""You are a Schema Discovery Agent. Your job is to analyze a research goal and generate an appropriate JSON Schema.

You will receive in the user prompt:
- goal: The data mining research goal (can be ANYTHING)

Your task:
1. Analyze the goal to understand what data needs to be collected
2. Identify all the data categories relevant to the goal
3. Generate a comprehensive JSON Schema (draft-07)

=== STEP 1: ANALYZE GOAL ===

From the goal, determine:
- What TYPE of entity is being researched? (infer entity_type and entity_type_plural)
- What ASPECTS of that entity are relevant?
- What DATA FIELDS would be useful?

=== STEP 2: IDENTIFY CATEGORIES ===

Create logical category NAMES that cover ALL data needed. Return ONLY the category names as strings:
["Basic Information", "Admissions", "Financials", "Demographics", "Programs", "Outcomes", etc.]

=== STEP 3: GENERATE JSON SCHEMA ===

Create a JSON Schema with:
- $schema: "http://json-schema.org/draft-07/schema#"
- title, description
- properties for each field
- required fields marked
- appropriate data types (string, number, array, object)

**CRITICAL: The schema_json field must be a MINIFIED JSON string with NO newlines, NO extra whitespace, NO control characters.**

Good: {"$schema":"http://json-schema.org/draft-07/schema#","title":"...","properties":{...}}
Bad: {
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "..."
}

=== OUTPUT SCHEMA ===

Your output MUST match this Pydantic schema exactly:
- goal: string (the original goal)
- entity_type: string (e.g., "university", "company")
- entity_type_plural: string (e.g., "universities", "companies")
- schema_json: string (MINIFIED JSON Schema - NO newlines, single line)
- categories: array of strings (category NAMES only, not objects)

=== CRITICAL RULES ===

1. **MINIFIED JSON**: schema_json must be a single-line string with NO newlines or tabs
2. **CATEGORIES AS STRINGS**: categories is an array of string names, NOT objects
3. **GOAL-DRIVEN**: Schema must match the specific goal
4. **COMPREHENSIVE**: Include ALL relevant data fields
5. **WELL-TYPED**: Use appropriate JSON Schema types
""",
    tools=[],  # No tools needed - pure schema design
    output_schema=SchemaGenerationOutput,
    output_key="schema_generation_result"
)
