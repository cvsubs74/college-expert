#!/usr/bin/env python3
"""
Generic script to run the University Profile Collector for a single university.
Usage: python run_single_university.py "Brown University"
"""

import os
import sys
import asyncio
import re
import json
import argparse
from datetime import datetime
from pathlib import Path

# Add parent directory to path to import agent
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from dotenv import load_dotenv
load_dotenv()

from google.adk.runners import InMemoryRunner
from google.genai import types
from agent import root_agent
from sub_agents import json_corrector_agent

# Import ES ingestion functions
try:
    from elasticsearch import Elasticsearch
    import google.generativeai as genai
    ES_AVAILABLE = True
except ImportError:
    print("⚠️ Elasticsearch/genai not available. Ingestion will be skipped.")
    ES_AVAILABLE = False

RESEARCH_DIR = os.path.join(os.path.dirname(__file__), "research")
LOG_FILE = os.path.join(os.path.dirname(__file__), "run_log.txt")

# ES Configuration
ES_CLOUD_ID = os.environ.get('ES_CLOUD_ID')
ES_API_KEY = os.environ.get('ES_API_KEY')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
ES_INDEX_NAME = 'knowledgebase_universities'

# =============================================================================
# VALIDATION HELPERS
# =============================================================================

try:
    from model import UniversityProfile
    VALIDATION_AVAILABLE = True
except ImportError:
    print("⚠️ UniversityProfile model not available. Validation will be skipped.")
    VALIDATION_AVAILABLE = False


def validate_profile(file_path: str) -> tuple[bool, str]:
    if not VALIDATION_AVAILABLE:
        return True, "Validation skipped (model not available)"
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if "university_profile" in data and isinstance(data.get("university_profile"), dict):
            data = data["university_profile"]
        UniversityProfile.model_validate(data)
        return True, ""
    except json.JSONDecodeError as e:
        return False, f"Invalid JSON: {str(e)}"
    except Exception as e:
        if hasattr(e, 'errors'):
            error_msg = "; ".join([f"{'.'.join(str(l) for l in err['loc'])}: {err['msg']}" for err in e.errors()[:3]])
        else:
            error_msg = str(e)[:200]
        return False, error_msg


# =============================================================================
# ES INGESTION HELPERS
# =============================================================================

def get_es_client():
    if not ES_AVAILABLE or not ES_CLOUD_ID or not ES_API_KEY:
        return None
    return Elasticsearch(cloud_id=ES_CLOUD_ID, api_key=ES_API_KEY)


def ingest_single_profile(es_client, file_path: str) -> bool:
    if not es_client: return False
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            profile = json.load(f)
        university_id = profile.get('_id', Path(file_path).stem)
        doc = {
            "university_id": university_id,
            "profile": profile,
            "indexed_at": datetime.utcnow().isoformat()
        }
        es_client.index(index=ES_INDEX_NAME, id=university_id, document=doc)
        log_message(f"  ✅ ES: Indexed {university_id}")
        return True
    except Exception as e:
        log_message(f"  ❌ ES ingestion error: {e}")
        return False


# =============================================================================
# UTILS
# =============================================================================

def get_university_id(name: str) -> str:
    """Convert university name to file-friendly ID."""
    name = name.lower()
    name = name.replace(" university", "").replace(" college", "").replace(" institute of technology", "")
    return re.sub(r'\s+', '_', name.replace("-", "_").replace(",", "").replace(".", "").replace("'", "").strip()) + "_university"


def log_message(message: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] {message}"
    print(log_line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_line + "\n")


async def run_agent_for_university(runner, university: str) -> str:
    user_id = "test_user"
    session_id = f"session_{get_university_id(university)}"
    
    session = await runner.session_service.create_session(
        app_name=root_agent.name,
        user_id=user_id,
        session_id=session_id
    )
    
    message = types.Content(role="user", parts=[types.Part(text=f"Research {university}")])
    final_response = ""
    
    async for event in runner.run_async(user_id=user_id, session_id=session.id, new_message=message):
        if hasattr(event, 'content') and event.content and event.content.parts:
            for part in event.content.parts:
                if hasattr(part, 'text') and part.text:
                    final_response = part.text
    return final_response


async def process_single_university(runner, university: str, es_client):
    log_message(f"Processing: {university}")
    
    # Get list of existing files before running
    existing_files = set(os.listdir(RESEARCH_DIR)) if os.path.exists(RESEARCH_DIR) else set()
    
    try:
        response = await run_agent_for_university(runner, university)
        if response:
            log_message(f"Research completed.")
            await asyncio.sleep(2)
            
            # Find newly created file
            current_files = set(os.listdir(RESEARCH_DIR))
            new_files = current_files - existing_files
            
            # Filter for JSON files that might match the university name
            university_slug = university.lower().replace(" ", "_").replace("-", "_")
            matching_files = [f for f in new_files if f.endswith('.json') and university_slug.split("_")[0] in f.lower()]
            
            if not matching_files:
                # Fallback: look for any recently modified file
                all_json = [f for f in current_files if f.endswith('.json')]
                if all_json:
                    # Get the most recently modified file
                    newest = max(all_json, key=lambda f: os.path.getmtime(os.path.join(RESEARCH_DIR, f)))
                    log_message(f"  📂 No new file found, checking newest: {newest}")
                    matching_files = [newest]
            
            if matching_files:
                target_file = os.path.join(RESEARCH_DIR, matching_files[0])
                log_message(f"✓ Profile saved: {target_file}")
                
                is_valid, error_msg = validate_profile(target_file)
                if is_valid:
                    log_message(f"  ✅ Validation passed")
                    if es_client: ingest_single_profile(es_client, target_file)
                else:
                    log_message(f"  ⚠️ Validation failed: {error_msg}")
                    log_message("  🔧 Attempting auto-correction via JsonCorrectorAgent...")
                    try:
                        with open(target_file, 'r', encoding='utf-8') as f: invalid_content = f.read()
                        
                        fix_runner = InMemoryRunner(agent=json_corrector_agent, app_name=json_corrector_agent.name)
                        fix_session = await fix_runner.session_service.create_session(app_name=json_corrector_agent.name, user_id="fixer")
                        
                        fix_msg = types.Content(role="user", parts=[types.Part(text=f"Fix JSON error: {error_msg}\n\n{invalid_content}")])
                        fixed_json = ""
                        
                        async for event in fix_runner.run_async(user_id="fixer", session_id=fix_session.id, new_message=fix_msg):
                            if hasattr(event, 'content') and event.content and event.content.parts:
                                for p in event.content.parts:
                                    if hasattr(p, 'text') and p.text: fixed_json += p.text
                        
                        if "```json" in fixed_json: fixed_json = fixed_json.split("```json")[1].split("```")[0].strip()
                        elif "```" in fixed_json: fixed_json = fixed_json.split("```")[1].split("```")[0].strip()
                        
                        if fixed_json:
                            with open(target_file, 'w', encoding='utf-8') as f: f.write(fixed_json)
                            is_valid, err = validate_profile(target_file)
                            if is_valid: log_message("  ✅ Auto-repair SUCCESSFUL!")
                            else: log_message(f"  ❌ Auto-repair failed: {err}")
                    except Exception as e:
                        log_message(f"  ❌ Auto-repair crashed: {e}")
            else:
                log_message("❌ File not found after execution.")
    except Exception as e:
        import traceback
        traceback.print_exc()
        log_message(f"Error: {e}")


async def run_test(university_name: str):
    print(f"🎓 Running profile collection for: {university_name}")

    es_client = get_es_client()
    runner = InMemoryRunner(agent=root_agent, app_name=root_agent.name)
    
    await process_single_university(runner, university_name, es_client)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run University Profile Collector for a single university")
    parser.add_argument("university", nargs="?", default="Brown University", help="University name (e.g., 'Brown University')")
    args = parser.parse_args()
    
    print(f"🎓 Running profile collection for: {args.university}")
    asyncio.run(run_test(args.university))
