"""
Source Curator Agent - Discovers and curates authoritative data sources for universities.

This agent automates Tier 0 of the deterministic source curation architecture:
1. Discovers authoritative URLs for each data category
2. Validates URL accessibility
3. Generates draft YAML configuration files for user review

Usage:
    from source_curator import root_agent
    
    # Run with ADK
    python -m google.adk.cli run source_curator "University of Southern California"
"""

from .agent import root_agent

__all__ = ['root_agent']
