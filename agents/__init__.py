"""
College Counselor Agent

An AI-powered college admissions analysis system using Google GenAI.
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
print(f"Initializing College Counselor Agent")
print(f"  Project: {PROJECT_ID}")
print(f"  Location: {LOCATION}")
print(f"  Data Store: {DATA_STORE}")
print(f"  API Key: {'Set' if GEMINI_API_KEY else 'Not Set'}")

if not GEMINI_API_KEY:
    print("WARNING: GEMINI_API_KEY not set. Agent may not function properly.")

# Import agent after initialization is complete
from .agent import root_agent

__all__ = ['root_agent', 'PROJECT_ID', 'LOCATION', 'GEMINI_API_KEY', 'DATA_STORE']
