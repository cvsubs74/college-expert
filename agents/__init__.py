"""
College Counselor Agents

An AI-powered college admissions analysis system using Google GenAI.
Supports both RAG and Elasticsearch knowledge base approaches.
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get configuration from environment
PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "college-counselling-478115")
LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-east1")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
DATA_STORE = os.environ.get("DATA_STORE", "college_admissions_kb")

# Log configuration
print(f"Initializing College Counselor Agents")
print(f"  Project: {PROJECT_ID}")
print(f"  Location: {LOCATION}")
print(f"  Data Store: {DATA_STORE}")
print(f"  API Key: {'Set' if GEMINI_API_KEY else 'Not Set'}")

if not GEMINI_API_KEY:
    print("WARNING: GEMINI_API_KEY not set. Agents may not function properly.")

# Import both specialized agents
from .college_expert_rag import college_expert_rag
from .college_expert_es import college_expert_es

# Set RAG as the default agent for ADK web server
root_agent = college_expert_rag

# Export agents and configuration
__all__ = [
    'college_expert_rag',  # RAG-based college expert
    'college_expert_es',   # Elasticsearch-based college expert
    'root_agent',          # Default agent (used by ADK web server)
    'PROJECT_ID', 
    'LOCATION', 
    'GEMINI_API_KEY', 
    'DATA_STORE'
]

print(f"  Available agents: college_expert_rag, college_expert_es")
print(f"  Default agent: college_expert_rag")
