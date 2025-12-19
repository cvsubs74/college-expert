#!/usr/bin/env python3
"""
Consolidated script to collect profiles for Top ~250 US universities.
Runs the agent directly in console (no server needed).
Skips universities that already have data in the research folder.

Features:
- Consolidated List: Combines Top 100 and Next ~150 universities.
- Parallel processing: Run multiple collection tasks in parallel (default 25).
- Self-Correction: Uses the LoopAgent in agent.py to fix validation errors.
- ES Ingestion: Automatically ingests valid profiles.

Usage:
  python run_all_250_universities.py --parallel 25
  python run_all_250_universities.py -u "Specific University"
"""

import os
import sys
import asyncio
import re
import json
import glob
import argparse
import contextlib
import traceback
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

# Add parent directory to path to import agent
sys.path.insert(0, os.path.dirname(__file__))
# Add scripts directory for ingestion
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from dotenv import load_dotenv
load_dotenv()

from google.adk.runners import InMemoryRunner
from google.genai import types
from agent import root_agent

# Import ES ingestion functions
try:
    from elasticsearch import Elasticsearch
    import google.generativeai as genai
    ES_AVAILABLE = True
except ImportError:
    print("⚠️ Elasticsearch/genai not available. Ingestion will be skipped.")
    ES_AVAILABLE = False

RESEARCH_DIR = os.path.join(os.path.dirname(__file__), "research")
LOG_FILE = os.path.join(os.path.dirname(__file__), "run_all_250_log.txt")

# ES Configuration
ES_CLOUD_ID = os.environ.get('ES_CLOUD_ID')
ES_API_KEY = os.environ.get('ES_API_KEY')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
ES_INDEX_NAME = 'knowledgebase_universities'
EMBEDDING_DIM = 768

# =============================================================================
# UNIVERSITY LISTS
# =============================================================================

TOP_100_UNIVERSITIES = [
    "Princeton University", "Massachusetts Institute of Technology", "Harvard University", "Stanford University",
    "Yale University", "Duke University", "California Institute of Technology", "Northwestern University",
    "Johns Hopkins University", "Columbia University", "University of Chicago", "University of Pennsylvania",
    "Cornell University", "Brown University", "Rice University", "Dartmouth College", "Vanderbilt University",
    "Carnegie Mellon University", "Washington University in St. Louis", "Emory University", "University of Notre Dame",
    "Georgetown University", "University of California, Berkeley", "University of California, Los Angeles",
    "University of Virginia", "University of Michigan, Ann Arbor", "University of Southern California",
    "New York University", "University of Florida", "University of North Carolina at Chapel Hill",
    "Wake Forest University", "Tufts University", "University of California, San Diego",
    "University of California, Santa Barbara", "University of Rochester", "Boston College",
    "Georgia Institute of Technology", "University of California, Irvine", "University of California, Davis",
    "University of Texas at Austin", "College of William and Mary", "Boston University", "Tulane University",
    "Brandeis University", "Case Western Reserve University", "University of Wisconsin-Madison",
    "University of Illinois Urbana-Champaign", "Ohio State University", "Purdue University", "Villanova University",
    "University of Georgia", "Lehigh University", "University of Miami", "Pepperdine University",
    "Northeastern University", "Rensselaer Polytechnic Institute", "University of Washington",
    "Santa Clara University", "University of Maryland, College Park", "George Washington University",
    "Syracuse University", "University of Pittsburgh", "Rutgers University-New Brunswick",
    "University of Connecticut", "University of Minnesota Twin Cities", "Virginia Tech", "Texas A&M University",
    "Fordham University", "University of Massachusetts Amherst", "Stevens Institute of Technology",
    "Indiana University Bloomington", "University of California, Merced", "University of Colorado Boulder",
    "North Carolina State University", "Pennsylvania State University", "University of Delaware",
    "Florida State University", "University of Iowa", "Southern Methodist University", "University of South Florida",
    "Clemson University", "Stony Brook University-SUNY", "University of Denver", "University at Buffalo-SUNY",
    "Loyola Marymount University", "Chapman University", "Michigan State University", "American University",
    "Baylor University", "Howard University", "Illinois Institute of Technology", "Marquette University",
    "Auburn University", "Drexel University", "Gonzaga University", "University of Arizona",
    "Creighton University", "University of Oregon", "Temple University", "University of San Diego"
]

NEXT_UNIVERSITIES = [
    "University of South Carolina", "University of Vermont", "Texas Christian University",
    "SUNY College of Environmental Science and Forestry", "San Diego State University", "University of Dayton",
    "University of Kansas", "University of the Pacific", "University of Alabama", "Yeshiva University",
    "University of Missouri", "Colorado School of Mines", "Clark University", "University of Kentucky",
    "Elon University", "New Jersey Institute of Technology", "University of Oklahoma", "Clarkson University",
    "University of Tennessee", "Worcester Polytechnic Institute", "Arizona State University",
    "University of Cincinnati", "University of St. Thomas (Minnesota)", "University of Tulsa",
    "St. Louis University", "University of Nebraska-Lincoln", "The Catholic University of America",
    "University of San Francisco", "University of New Hampshire", "Seton Hall University",
    "SUNY Binghamton University", "DePaul University", "University of Hawaii at Manoa",
    "University of Rhode Island", "Rochester Institute of Technology", "Iowa State University",
    "Missouri University of Science and Technology", "University of Arkansas", "Oklahoma State University",
    "University of Louisville", "University of La Verne", "Ohio University", "Kansas State University",
    "Adelphi University", "University of Central Florida", "Simmons University", "Loyola University Chicago",
    "Hofstra University", "University of Massachusetts Lowell", "Seattle University", "Illinois State University",
    "Colorado State University", "Duquesne University", "University of Texas at Dallas", "University of Wyoming",
    "Quinnipiac University", "Western Michigan University", "Rowan University", "University of New Mexico",
    "Washington State University", "University of Montana", "University of North Texas", "James Madison University",
    "Belmont University", "Ball State University", "Mercer University", "University of Idaho",
    "University of Mississippi", "Louisiana State University", "University of North Carolina at Charlotte",
    "California State University, Fullerton", "University of Alabama at Birmingham", "Pace University",
    "Portland State University", "University of Nevada, Reno", "Samford University", "Florida International University",
    "George Mason University", "Wayne State University", "Kent State University", "University of Maine",
    "Tennessee Tech University", "University of North Dakota", "Appalachian State University",
    "Old Dominion University", "Georgia State University", "California State University, Long Beach",
    "Bowling Green State University", "East Carolina University", "Montclair State University",
    "San Jose State University", "Morgan State University", "Texas Tech University",
    "University of Maryland, Baltimore County", "University of Akron", "Northern Illinois University",
    "University of Memphis", "Utah State University", "West Virginia University", "Wichita State University",
    # Additional Universities to reach ~250
    "University of Nevada, Las Vegas", "Florida Atlantic University", "Boise State University",
    "University of Toledo", "Western Kentucky University", "Middle Tennessee State University",
    "Northern Arizona University", "University of South Alabama", "Texas State University",
    "University of Texas at San Antonio", "University of Wisconsin-Milwaukee", "Virginia Commonwealth University",
    "University of North Carolina at Greensboro", "University of Texas at Arlington", "New Mexico State University",
    "University of New Orleans", "Oakland University", "University of Massachusetts Boston",
    "University of Missouri-Kansas City", "Portland State University", "Cleveland State University",
    "University of Colorado Denver", "University of Alaska Fairbanks", "University of Alabama in Huntsville",
    "University of Maryland Eastern Shore", "San Francisco State University", "California State University, Northridge",
    "California State University, Los Angeles", "Florida A&M University", "Jackson State University",
    "North Carolina A&T State University", "Prairie View A&M University", "Tennessee State University",
    "Texas Southern University", "University of Houston", "University of North Florida",
    "West Chester University of Pennsylvania", "Kennesaw State University", "Grand Valley State University"
]

ALL_UNIVERSITIES = TOP_100_UNIVERSITIES + NEXT_UNIVERSITIES

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
    """Validate a university profile against the Pydantic model."""
    if not VALIDATION_AVAILABLE:
        return True, "Validation skipped (model not available)"
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        UniversityProfile.model_validate(data)
        return True, ""
        
    except json.JSONDecodeError as e:
        return False, f"Invalid JSON: {str(e)}"
    except Exception as e:
        # Pydantic validation error
        details = []
        if hasattr(e, 'errors'):
            for err in e.errors()[:3]:  # First 3 errors
                loc = ".".join(str(l) for l in err['loc'])
                msg = err['msg']
                details.append(f"{loc}: {msg}")
        error_msg = "; ".join(details) if details else str(e)[:200]
        return False, error_msg


# =============================================================================
# ES INGESTION HELPERS
# =============================================================================

def get_es_client():
    if not ES_AVAILABLE or not ES_CLOUD_ID or not ES_API_KEY:
        return None
    return Elasticsearch(cloud_id=ES_CLOUD_ID, api_key=ES_API_KEY)


def init_gemini_embeddings():
    if not ES_AVAILABLE or not GEMINI_API_KEY:
        return False
    genai.configure(api_key=GEMINI_API_KEY)
    return True


def generate_embedding(text: str) -> list:
    try:
        max_chars = 25000
        if len(text) > max_chars:
            text = text[:max_chars]
        result = genai.embed_content(
            model='models/text-embedding-004',
            content=text,
            task_type="retrieval_document"
        )
        return result['embedding']
    except Exception as e:
        log_message(f"  ⚠️ Embedding failed: {e}")
        return [0.0] * EMBEDDING_DIM


def create_searchable_text(profile: dict) -> str:
    parts = []
    
    if 'metadata' in profile:
        meta = profile['metadata']
        parts.append(f"University: {meta.get('official_name', '')}")
        if 'location' in meta:
            loc = meta['location']
            parts.append(f"Location: {loc.get('city', '')}, {loc.get('state', '')}")
    
    if 'strategic_profile' in profile:
        sp = profile['strategic_profile']
        if sp.get('executive_summary'):
            parts.append(f"Summary: {sp['executive_summary']}")
        if sp.get('admissions_philosophy'):
            parts.append(f"Admissions Philosophy: {sp['admissions_philosophy']}")
    
    if 'admissions_data' in profile:
        ad = profile['admissions_data']
        if 'current_status' in ad:
            cs = ad['current_status']
            parts.append(f"Acceptance Rate: {cs.get('overall_acceptance_rate', 'N/A')}%")
    
    if 'academic_structure' in profile:
        acs = profile['academic_structure']
        if 'colleges' in acs:
            college_names = [c.get('name', '') for c in acs['colleges'] if c.get('name')]
            if college_names:
                parts.append(f"Colleges: {', '.join(college_names[:10])}")
    
    if 'outcomes' in profile:
        out = profile['outcomes']
        if out.get('median_earnings_10yr'):
            parts.append(f"Median Earnings (10yr): ${out['median_earnings_10yr']:,}")
        if out.get('top_employers'):
            parts.append(f"Top Employers: {', '.join(out['top_employers'][:5])}")
    
    return "\n".join(parts)


def ingest_single_profile(es_client, file_path: str) -> bool:
    if not es_client:
        return False
        
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            profile = json.load(f)
        
        university_id = profile.get('_id', Path(file_path).stem)
        official_name = profile.get('metadata', {}).get('official_name', university_id)
        location = profile.get('metadata', {}).get('location', {})
        
        searchable_text = create_searchable_text(profile)
        log_message(f"  📝 ES: Generated searchable text ({len(searchable_text)} chars)")
        
        embedding = generate_embedding(searchable_text)
        log_message(f"  🧮 ES: Generated embedding ({len(embedding)} dims)")
        
        current_status = profile.get('admissions_data', {}).get('current_status', {})
        
        doc = {
            "university_id": university_id,
            "official_name": official_name,
            "location": location,
            "searchable_text": searchable_text,
            "embedding": embedding,
            "acceptance_rate": current_status.get('overall_acceptance_rate'),
            "test_policy": current_status.get('test_policy_details', ''),
            "market_position": profile.get('strategic_profile', {}).get('market_position', ''),
            "median_earnings_10yr": profile.get('outcomes', {}).get('median_earnings_10yr'),
            "profile": profile,
            "indexed_at": datetime.utcnow().isoformat(),
            "last_updated": profile.get('metadata', {}).get('last_updated')
        }
        
        es_client.index(index=ES_INDEX_NAME, id=university_id, document=doc)
        log_message(f"  ✅ ES: Indexed {official_name}")
        return True
        
    except Exception as e:
        log_message(f"  ❌ ES ingestion error: {e}")
        return False


# =============================================================================
# UTILS
# =============================================================================

def get_university_id(name: str) -> str:
    name = name.lower()
    name = name.replace(" university", "").replace(" college", "")
    name = name.replace(" institute of technology", "").replace("-", "_")
    name = name.replace(",", "").replace(".", "").replace("'", "")
    name = re.sub(r'\s+', '_', name.strip())
    return name


def get_existing_universities() -> set:
    existing = set()
    if os.path.exists(RESEARCH_DIR):
        for fname in os.listdir(RESEARCH_DIR):
            if fname.endswith('.json'):
                file_id = fname.replace('.json', '').lower()
                existing.add(file_id)
                try:
                    with open(os.path.join(RESEARCH_DIR, fname), 'r') as f:
                        data = json.load(f)
                        if '_id' in data:
                            existing.add(data['_id'].lower())
                except:
                    pass
    return existing


def is_university_already_researched(university_name: str, existing_ids: set) -> bool:
    name_lower = university_name.lower()
    variations = [
        get_university_id(university_name),
        name_lower.replace(' ', '_').replace(',', '').replace('-', '_'),
        name_lower.replace('university of ', '').replace(' ', '_').replace(',', ''),
        name_lower.replace(', ', '_').replace(' ', '_'),
    ]
    for var in variations:
        if var in existing_ids:
            return True
    return False


def log_message(message: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] {message}"
    print(log_line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_line + "\n")


async def run_agent_for_university(runner: InMemoryRunner, university: str) -> str:
    user_id = "batch_user"
    session_id = f"session_{get_university_id(university)}"
    
    session = await runner.session_service.create_session(
        app_name=root_agent.name,
        user_id=user_id,
        session_id=session_id
    )
    
    # CRITICAL FIX: Pre-set university_name in session state before running
    # This prevents KeyError when sub-agents reference {university_name}
    session.state["university_name"] = university
    
    message = types.Content(
        role="user",
        parts=[types.Part(text=f"Research {university}")]
    )
    
    final_response = ""
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session.id,
        new_message=message
    ):
        if hasattr(event, 'content') and event.content and event.content.parts:
            for part in event.content.parts:
                if hasattr(part, 'text') and part.text:
                    final_response = part.text
    
    return final_response


async def process_single_university(runner, university: str, existing: set, es_client, semaphore: asyncio.Semaphore = None):
    async with semaphore if semaphore else contextlib.nullcontext():
        log_message(f"\n====================\nProcessing: {university}\n====================")
        try:
            response = await run_agent_for_university(runner, university)
            
            if response:
                log_message(f"Research completed for {university}")
                await asyncio.sleep(1)
                
                # Verify file creation
                uni_slug = get_university_id(university)
                # Simple check for any new file or file matching slug
                # Just checking if file exists with approximate name
                found_file = None
                for fname in os.listdir(RESEARCH_DIR):
                     if fname.endswith(".json") and uni_slug[:10] in fname.lower():
                         if os.path.getmtime(os.path.join(RESEARCH_DIR, fname)) > datetime.now().timestamp() - 300:
                             found_file = os.path.join(RESEARCH_DIR, fname)
                             break
                
                if found_file:
                    log_message(f"✓ Profile saved: {os.path.basename(found_file)}")
                    is_valid, error_msg = validate_profile(found_file)
                    if is_valid:
                        log_message("  ✅ Validation passed")
                        if es_client:
                            ingest_single_profile(es_client, found_file)
                    else:
                        log_message(f"  ⚠️ Validation failed: {error_msg}")
                    return True
                else:
                    log_message(f"⚠ Output file not found for {university}")
                    return False
            else:
                log_message(f"No response for {university}")
                return False
                
        except Exception as e:
            log_message(f"Error researching {university}: {str(e)}")
            log_message(traceback.format_exc())
            return False


async def run_batch(parallel_count: int = 25, specific_university: str = None):
    existing = get_existing_universities()
    
    if specific_university:
        to_collect = [specific_university]
        log_message(f"Running single university: {specific_university}")
    else:
        to_collect = [u for u in ALL_UNIVERSITIES if not is_university_already_researched(u, existing)]
        log_message(f"Full list: {len(ALL_UNIVERSITIES)}. To Collect: {len(to_collect)}")
    
    if not to_collect:
        log_message("🎉 All done!")
        return

    # ES Init
    es_client = None
    if ES_AVAILABLE and ES_CLOUD_ID and ES_API_KEY:
        es_client = get_es_client()
        init_gemini_embeddings()
    
    runner = InMemoryRunner(agent=root_agent, app_name=root_agent.name)
    
    if parallel_count > 1:
        semaphore = asyncio.Semaphore(parallel_count)
        log_message(f"Starting parallel execution with {parallel_count} workers...")
        
        # Determine strict batching or just bounded concurrency
        # With asyncio.gather on all tasks it will start all but semaphore limits active ones
        # Use chunks to avoid creating too many task objects at once if list is huge, 
        # but for 250 it's fine.
        
        tasks = [
            process_single_university(runner, uni, existing, es_client, semaphore)
            for uni in to_collect
        ]
        await asyncio.gather(*tasks)
    else:
        for uni in to_collect:
            await process_single_university(runner, uni, existing, es_client, None)


def main():
    parser = argparse.ArgumentParser(description="Collect Top 250 University Profiles")
    parser.add_argument('--parallel', '-p', type=int, default=5, help='Parallel workers (default 5, max recommended 10)')
    parser.add_argument('--university', '-u', type=str, help='Run specific university')
    args = parser.parse_args()
    
    asyncio.run(run_batch(parallel_count=args.parallel, specific_university=args.university))

if __name__ == "__main__":
    main()
