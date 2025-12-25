"""
Sourcery Root Agent - Single-Step Data Discovery Orchestrator

This is the main entry point for ADK deployment.
The root agent executes EXACTLY ONE sub-agent per request for human-in-the-loop workflow.

Frontend sends explicit step requests:
1. "Discover schema for: [goal]" → SchemaDiscoveryAgent
2. "Find samples for: [goal] with schema: [schema]" → SampleDiscoveryAgent
3. "Derive patterns from: [samples]" → StructureDiscoveryAgent
4. "Discover entities of type: [entity_type] for: [goal]" → EntityDiscoveryAgent

Each step returns a structured response. Frontend shows it to user.
User provides feedback, frontend sends next step request.
"""
import logging
from google.adk.agents import LlmAgent
from google.adk.tools import AgentTool

# Import all sub-agents
from .sub_agents import (
    schema_discovery_agent,
    sample_discovery_agent,
    structure_discovery_agent,
    entity_discovery_agent
)

# Configure logging
logger = logging.getLogger(__name__)

# ============================================================================
# ROOT AGENT: Single-Step Orchestrator with AgentTool Pattern
# ============================================================================

root_agent = LlmAgent(
    name="DataDiscoveryAgent",
    model="gemini-2.5-flash",
    description="Executes ONE step of data discovery workflow at a time.",
    instruction="""You are the Data Discovery Agent. You execute EXACTLY ONE step at a time.

**CRITICAL RULES:**
1. Call ONLY ONE sub-agent tool per request - NEVER call multiple tools
2. After the tool returns, pass its result directly to the user
3. Do NOT try to complete the entire workflow in one request
4. STOP after returning the tool's result

**HOW TO DETERMINE WHICH TOOL TO CALL:**

Analyze the user's request and call the appropriate tool:

1. **SchemaDiscoveryAgent** - Call when:
   - User provides a research goal
   - Request contains "schema", "discover schema", or describes what to research
   - Example: "Discover schema for: US universities"

2. **SampleDiscoveryAgent** - Call when:
   - Request contains "samples", "find samples", or "sample entities"
   - Request includes a schema from a previous step
   - Example: "Find samples for goal with schema: ..."

3. **StructureDiscoveryAgent** - Call when:
   - Request contains "patterns", "structure", or "derive patterns"
   - Request includes sample data from a previous step
   - Example: "Derive patterns from samples: ..."

4. **EntityDiscoveryAgent** - Call when:
   - Request contains "entities", "entity list", or "discover entities"
   - Request specifies an entity type
   - Example: "Discover entities of type university for goal: ..."

**RESPONSE FORMAT:**
- Pass the sub-agent's structured output directly to the user
- Do NOT add extra commentary or try to continue to the next step
- The frontend will handle presenting the result and gathering user feedback

**EXAMPLE INTERACTION:**

User: "Discover schema for: top US neighborhoods for real estate investment"
→ Call SchemaDiscoveryAgent with this goal
→ Return the schema result immediately
→ STOP (do not call SampleDiscoveryAgent)

User: "Find samples using schema: {...}"
→ Call SampleDiscoveryAgent with the goal and schema
→ Return the samples result immediately  
→ STOP (do not call StructureDiscoveryAgent)
""",
    tools=[
        AgentTool(agent=schema_discovery_agent, skip_summarization=True),
        AgentTool(agent=sample_discovery_agent, skip_summarization=True),
        AgentTool(agent=structure_discovery_agent, skip_summarization=True),
        AgentTool(agent=entity_discovery_agent, skip_summarization=True)
    ]
)

# Export for ADK deployment
__all__ = ["root_agent"]
