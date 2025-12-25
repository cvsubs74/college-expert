"""
Source Curator Agent - Main Orchestrator

Discovers authoritative sources for university data and generates
curated YAML configurations for deterministic data collection.

Uses SequentialAgent pattern with specialized sub-agents, each with its own tools.
This prevents the "tool use with function calling unsupported" error that occurs
when mixing google_search with custom FunctionTools.
"""
import logging
from google.adk.agents import SequentialAgent

from sub_agents import (
    state_initializer,
    ipeds_lookup_agent,
    url_discovery_agent,
    url_validator_agent,
    yaml_generator_agent
)

logger = logging.getLogger(__name__)

# ==============================================================================
# ROOT AGENT: Sequential pipeline of specialized agents
# ==============================================================================
# Each agent has its own tools:
# 1. state_initializer - No tools (BaseAgent)
# 2. ipeds_lookup_agent - FunctionTools: lookup_ipeds_id, get_api_source_config
# 3. url_discovery_agent - google_search ONLY
# 4. url_validator_agent - FunctionTools: validate_url
# 5. yaml_generator_agent - FunctionTools: write_yaml_config

root_agent = SequentialAgent(
    name="SourceCuratorPipeline",
    sub_agents=[
        state_initializer,        # Initialize session state
        ipeds_lookup_agent,       # Step 1: IPEDS lookup + API configs
        url_discovery_agent,      # Step 2: Find URLs via Google Search
        url_validator_agent,      # Step 3: Validate URLs 
        yaml_generator_agent      # Step 4: Generate YAML config file
    ]
)
