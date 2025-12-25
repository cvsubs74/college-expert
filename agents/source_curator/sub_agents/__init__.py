"""
Sub-agents for Source Curator.

Uses SequentialAgent pattern - each agent has its own tools,
preventing the "tool use with function calling unsupported" error.
"""
from .state_initializer import state_initializer
from .university_name_extractor import university_name_extractor
from .ipeds_lookup_agent import ipeds_lookup_agent
from .url_discovery_agent import url_discovery_agent
from .url_validator_agent import url_validator_agent
from .yaml_generator_agent import yaml_generator_agent

__all__ = [
    'state_initializer',
    'university_name_extractor',
    'ipeds_lookup_agent',
    'url_discovery_agent',
    'url_validator_agent',
    'yaml_generator_agent'
]
