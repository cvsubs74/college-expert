"""
Configuration settings for the College Counselor Agent.

These settings are used by the various tools and sub-agents.
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# GCP settings
PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "college-counselling-478115")
LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-east1")

# Gemini API settings
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
USE_VERTEXAI = os.environ.get("GOOGLE_GENAI_USE_VERTEXAI", "0") == "1"

# Data Store settings
DATA_STORE = os.environ.get("DATA_STORE", "college_admissions_kb")
STUDENT_PROFILE_STORE = "student_profile"

# Agent settings
DEFAULT_MODEL = "gemini-2.5-flash"
DEFAULT_TEMPERATURE = 0.7
