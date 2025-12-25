"""
DataMine Agent Package

Exports the root_agent for ADK deployment.
The frontend can invoke the deployed Cloud Run endpoint directly.
"""

from .agent import root_agent

__all__ = ["root_agent"]
