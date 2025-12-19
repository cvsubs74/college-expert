#!/usr/bin/env python3
"""
Batch script to collect profiles for universities ranked 101-200.
Runs the agent directly in console (no server needed).
Skips universities that already have data in the research folder.
After saving, ingests into Elasticsearch knowledge base.

This is a continuation of run_top100_universities.py for the next tier.

Features:
- Parallel processing: Run multiple university research tasks simultaneously
- Smart exclusion: Skip universities that already have research files
- Validation: Validate each profile against the Pydantic schema
- ES Ingestion: Automatically ingest valid profiles to Elasticsearch

Usage:
  python run_next100_universities.py                    # Sequential (1 at a time)
  python run_next100_universities.py --parallel 3       # 3 universities in parallel
  python run_next100_universities.py --parallel 5       # 5 universities in parallel
"""

import os
import sys
import asyncio
import re
import json
import glob
import argparse
import contextlib
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
LOG_FILE = os.path.join(os.path.dirname(__file__), "batch_run_next100_log.txt")

# ES Configuration
ES_CLOUD_ID = os.environ.get('ES_CLOUD_ID')
ES_API_KEY = os.environ.get('ES_API_KEY')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
ES_INDEX_NAME = 'knowledgebase_universities'
EMBEDDING_DIM = 768

# Universities already in run_top100_universities.py (to exclude)
TOP_100_ALREADY_COVERED = {
    "princeton university",
    "massachusetts institute of technology",
    "harvard university",
    "stanford university",
    "yale university",
    "duke university",
    "california institute of technology",
    "northwestern university",
    "johns hopkins university",
    "columbia university",
    "university of chicago",
    "university of pennsylvania",
    "cornell university",
    "brown university",
    "rice university",
    "dartmouth college",
    "vanderbilt university",
    "carnegie mellon university",
    "washington university in st. louis",
    "emory university",
    "university of notre dame",
    "georgetown university",
    "university of california, berkeley",
    "university of california, los angeles",
    "university of virginia",
    "university of michigan, ann arbor",
    "university of southern california",
    "new york university",
    "university of florida",
    "university of north carolina at chapel hill",
    "wake forest university",
    "tufts university",
    "university of california, san diego",
    "university of california, santa barbara",
    "university of rochester",
    "boston college",
    "georgia institute of technology",
    "university of california, irvine",
    "university of california, davis",
    "university of texas at austin",
    "college of william and mary",
    "boston university",
    "tulane university",
    "brandeis university",
    "case western reserve university",
    "university of wisconsin-madison",
    "university of illinois urbana-champaign",
    "ohio state university",
    "purdue university",
    "villanova university",
    "university of georgia",
    "lehigh university",
    "university of miami",
    "pepperdine university",
    "northeastern university",
    "rensselaer polytechnic institute",
    "university of washington",
    "santa clara university",
    "university of maryland, college park",
    "george washington university",
    "syracuse university",
    "university of pittsburgh",
    "rutgers university-new brunswick",
    "university of connecticut",
    "university of minnesota twin cities",
    "virginia tech",
    "texas a&m university",
    "fordham university",
    "university of massachusetts amherst",
    "stevens institute of technology",
    "indiana university bloomington",
    "university of california, merced",
    "university of colorado boulder",
    "north carolina state university",
    "pennsylvania state university",
    "university of delaware",
    "florida state university",
    "university of iowa",
    "southern methodist university",
    "university of south florida",
    "clemson university",
    "stony brook university-suny",
    "university of denver",
    "university at buffalo-suny",
    "loyola marymount university",
    "chapman university",
    "michigan state university",
    "american university",
    "baylor university",
    "howard university",
    "illinois institute of technology",
    "marquette university",
    "auburn university",
    "drexel university",
    "gonzaga university",
    "university of arizona",
    "creighton university",
    "university of oregon",
    "temple university",
    "university of san diego",
}

# Next 100 US Universities (US News 2025 rankings, approximately ranks 101-200)
NEXT_100_UNIVERSITIES = [
    "University of South Carolina",
    "University of Vermont",
    "Texas Christian University",
    "SUNY College of Environmental Science and Forestry",
    "San Diego State University",
    "University of Dayton",
    "University of Kansas",
    "University of the Pacific",
    "University of Alabama",
    "Yeshiva University",
    "University of Missouri",
    "Colorado School of Mines",
    "Clark University",
    "University of Kentucky",
    "Elon University",
    "New Jersey Institute of Technology",
    "University of Oklahoma",
    "Clarkson University",
    "University of Tennessee",
    "Worcester Polytechnic Institute",
    "Arizona State University",
    "University of Cincinnati",
    "University of St. Thomas (Minnesota)",
    "University of Tulsa",
    "St. Louis University",
    "University of Nebraska-Lincoln",
    "The Catholic University of America",
    "University of San Francisco",
    "University of New Hampshire",
    "Seton Hall University",
    "SUNY Binghamton University",
    "DePaul University",
    "University of Hawaii at Manoa",
    "University of Rhode Island",
    "Rochester Institute of Technology",
    "Iowa State University",
    "Missouri University of Science and Technology",
    "University of Arkansas",
    "Oklahoma State University",
    "University of Louisville",
    "University of La Verne",
    "Ohio University",
    "Kansas State University",
    "Adelphi University",
    "University of Central Florida",
    "Simmons University",
    "Loyola University Chicago",
    "Hofstra University",
    "University of Massachusetts Lowell",
    "Seattle University",
    "Illinois State University",
    "Colorado State University",
    "Duquesne University",
    "University of Texas at Dallas",
    "University of Wyoming",
    "Quinnipiac University",
    "Western Michigan University",
    "Rowan University",
    "University of New Mexico",
    "Washington State University",
    "University of Montana",
    "University of North Texas",
    "James Madison University",
    "Belmont University",
    "Ball State University",
    "Mercer University",
    "University of Idaho",
    "University of Mississippi",
    "Louisiana State University",
    "University of North Carolina at Charlotte",
    "California State University, Fullerton",
    "University of Alabama at Birmingham",
    "Pace University",
    "Portland State University",
    "University of Nevada, Reno",
    "Samford University",
    "Florida International University",
    "George Mason University",
    "Wayne State University",
    "Kent State University",
    "University of Maine",
    "Tennessee Tech University",
    "University of North Dakota",
    "Appalachian State University",
    "Old Dominion University",
    "Georgia State University",
    "California State University, Long Beach",
    "Bowling Green State University",
    "East Carolina University",
    "Montclair State University",
    "San Jose State University",
    "Morgan State University",
    "Texas Tech University",
    "University of Maryland, Baltimore County",
    "University of Akron",
    "Northern Illinois University",
    "University of Memphis",
    "Utah State University",
    "West Virginia University",
    "Wichita State University",
]


# =============================================================================
# VALIDATION HELPERS (from validate_research.py)
# =============================================================================

try:
    from model import UniversityProfile
    VALIDATION_AVAILABLE = True
except ImportError:
    print("⚠️ UniversityProfile model not available. Validation will be skipped.")
    VALIDATION_AVAILABLE = False


def validate_profile(file_path: str) -> tuple[bool, str]:
    """Validate a university profile against the Pydantic model.
    
    Returns:
        tuple: (is_valid, error_message)
    """
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
# ES INGESTION HELPERS (from scripts/ingest_universities_es.py)
# =============================================================================

def get_es_client():
    """Initialize Elasticsearch client."""
    if not ES_AVAILABLE or not ES_CLOUD_ID or not ES_API_KEY:
        return None
    return Elasticsearch(cloud_id=ES_CLOUD_ID, api_key=ES_API_KEY)


def init_gemini_embeddings():
    """Initialize Gemini for embeddings."""
    if not ES_AVAILABLE or not GEMINI_API_KEY:
        return False
    genai.configure(api_key=GEMINI_API_KEY)
    return True


def generate_embedding(text: str) -> list:
    """Generate embedding vector using Gemini text-embedding-004."""
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
    """Create a rich text representation of the profile for embedding."""
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
    """Ingest a single university profile into Elasticsearch."""
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
# UNIVERSITY LIST AND HELPERS
# =============================================================================

def get_university_id(name: str) -> str:
    """Convert university name to a file-safe ID."""
    name = name.lower()
    name = name.replace(" university", "")
    name = name.replace(" college", "")
    name = name.replace(" institute of technology", "")
    name = name.replace("-", "_")
    name = name.replace(",", "")
    name = name.replace(".", "")
    name = name.replace("'", "")
    name = re.sub(r'\s+', '_', name.strip())
    return name


def get_existing_universities() -> set:
    """Get list of universities already in research folder.
    
    Returns a set of normalized university IDs from:
    1. The filename (without .json)
    2. The _id field inside the JSON
    """
    existing = set()
    if os.path.exists(RESEARCH_DIR):
        for fname in os.listdir(RESEARCH_DIR):
            if fname.endswith('.json'):
                # Add filename-based ID
                file_id = fname.replace('.json', '').lower()
                existing.add(file_id)
                
                # Also try to read the _id from inside the file
                try:
                    with open(os.path.join(RESEARCH_DIR, fname), 'r') as f:
                        data = json.load(f)
                        if '_id' in data:
                            existing.add(data['_id'].lower())
                        # Also add official_name variations
                        if 'metadata' in data and 'official_name' in data['metadata']:
                            official = data['metadata']['official_name'].lower()
                            existing.add(official.replace(' ', '_').replace(',', '').replace('-', '_'))
                except:
                    pass
    return existing


def is_university_already_researched(university_name: str, existing_ids: set) -> bool:
    """Check if a university has already been researched using fuzzy matching."""
    # Check if this university is in the top 100 list
    if university_name.lower() in TOP_100_ALREADY_COVERED:
        return True
    
    # Generate multiple possible IDs for this university
    name_lower = university_name.lower()
    
    # Common variations
    variations = [
        get_university_id(university_name),
        name_lower.replace(' ', '_').replace(',', '').replace('-', '_'),
        name_lower.replace('university of ', '').replace(' ', '_').replace(',', ''),
        name_lower.replace(', ', '_').replace(' ', '_'),
    ]
    
    # Check if any variation matches
    for var in variations:
        if var in existing_ids:
            return True
    
    return False


def log_message(message: str):
    """Log a message to both console and log file."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] {message}"
    print(log_line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_line + "\n")


async def run_agent_for_university(runner: InMemoryRunner, university: str) -> str:
    """Run the agent to collect data for a single university."""
    user_id = "batch_user"
    session_id = f"session_{get_university_id(university)}"
    
    session = await runner.session_service.create_session(
        app_name=root_agent.name,
        user_id=user_id,
        session_id=session_id
    )
    
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
    """Process a single university - research, validate, and ingest."""
    async with semaphore if semaphore else contextlib.nullcontext():
        log_message(f"\n{'='*60}")
        log_message(f"Processing: {university}")
        log_message(f"{'='*60}")
        
        try:
            response = await run_agent_for_university(runner, university)
            
            if response:
                log_message(f"Research completed for {university}")
                log_message(f"Response: {response[:200]}...")
                
                # Wait a moment for file to be written
                await asyncio.sleep(1)
                
                # Find the created file (agent may use different naming)
                new_files = [f for f in os.listdir(RESEARCH_DIR) if f.endswith('.json')]
                uni_lower = university.lower().replace(" ", "_").replace(",", "").replace("-", "_")
                
                created_file = None
                for f in new_files:
                    file_id = f.replace(".json", "").lower()
                    if uni_lower[:15] in f.lower() or file_id not in existing:
                        file_path = os.path.join(RESEARCH_DIR, f)
                        if os.path.getmtime(file_path) > datetime.now().timestamp() - 300:
                            created_file = file_path
                            existing.add(file_id)  # Mark as processed
                            break
                
                if created_file:
                    log_message(f"✓ Profile saved: {os.path.basename(created_file)}")
                    
                    # Validate the profile
                    is_valid, error_msg = validate_profile(created_file)
                    if is_valid:
                        log_message(f"  ✅ Validation passed")
                    else:
                        log_message(f"  ⚠️ Validation failed: {error_msg}")
                    
                    # Ingest into Elasticsearch (only if valid)
                    if es_client and is_valid:
                        ingest_single_profile(es_client, created_file)
                    
                    return True, university
                else:
                    log_message(f"⚠ Could not find newly created profile file for {university}")
                    return False, university
            else:
                log_message(f"No response received for {university}")
                return False, university
                
        except Exception as e:
            import traceback
            log_message(f"Error researching {university}: {str(e)}")
            log_message(traceback.format_exc())
            return False, university



async def run_batch(parallel_count: int = 1, specific_university: str = None):
    """Run the batch collection.
    
    Args:
        parallel_count: Number of universities to process in parallel
        specific_university: If set, only runs for this specific university
    """
    existing = get_existing_universities()
    
    if specific_university:
        log_message(f"Targeting single university: {specific_university}")
        to_collect = [specific_university]
    else:
        log_message(f"Found {len(existing)} existing university profiles in research folder.")
        # Filter out already collected universities using improved matching
        to_collect = []
        for uni in NEXT_100_UNIVERSITIES:
            if is_university_already_researched(uni, existing):
                log_message(f"Skip: {uni} (already researched)")
            else:
                to_collect.append(uni)
        
        log_message(f"\n📊 Summary: {len(NEXT_100_UNIVERSITIES) - len(to_collect)} already done, {len(to_collect)} remaining\n")
    
    if not to_collect:
        log_message("🎉 All universities already collected!")
        return
    
    # Initialize ES client if available
    es_client = None
    if ES_AVAILABLE and ES_CLOUD_ID and ES_API_KEY:
        log_message("🔌 Connecting to Elasticsearch...")
        es_client = get_es_client()
        if es_client:
            log_message("✅ Elasticsearch connected")
            init_gemini_embeddings()
            log_message("✅ Gemini embeddings initialized")
    else:
        log_message("⚠️ ES not configured - profiles will NOT be ingested to knowledge base")
    
    # Create the runner
    runner = InMemoryRunner(
        agent=root_agent,
        app_name=root_agent.name
    )
    
    log_message(f"\n🚀 Starting research with parallelism={parallel_count}\n")
    
    if parallel_count > 1:
        # Parallel processing with semaphore to control concurrency
        semaphore = asyncio.Semaphore(parallel_count)
        
        # Process in batches
        batch_size = parallel_count
        results = []
        
        for i in range(0, len(to_collect), batch_size):
            batch = to_collect[i:i + batch_size]
            log_message(f"\n🔄 Processing batch {i//batch_size + 1}: {', '.join(batch)}")
            
            tasks = [
                process_single_university(runner, uni, existing, es_client, semaphore)
                for uni in batch
            ]
            
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            results.extend(batch_results)
            
            # Brief delay between batches
            if i + batch_size < len(to_collect):
                log_message("Waiting 5 seconds before next batch...")
                await asyncio.sleep(5)
    else:
        # Sequential processing
        results = []
        for i, uni in enumerate(to_collect):
            log_message(f"\n[{i+1}/{len(to_collect)}]")
            result = await process_single_university(runner, uni, existing, es_client, None)
            results.append(result)
            
            # Small delay between universities
            if i < len(to_collect) - 1:
                log_message("Waiting 2 seconds before next university...")
                await asyncio.sleep(2)
    
    # Summary
    successful = sum(1 for r in results if isinstance(r, tuple) and r[0])
    failed = len(results) - successful
    
    log_message("\n" + "="*60)
    log_message(f"🏁 Batch collection complete!")
    log_message(f"   ✅ Successful: {successful}")
    log_message(f"   ❌ Failed: {failed}")
    log_message("="*60)


def main():
    """Main entry point with argument parsing."""
    parser = argparse.ArgumentParser(
        description="Batch collect university profiles for ranks 101-200.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_next100_universities.py                    # Sequential (1 at a time)
  python run_next100_universities.py --parallel 3       # 3 universities in parallel
  python run_next100_universities.py -u "San Diego State University"  # Single university
        """
    )
    parser.add_argument(
        '--parallel', '-p',
        type=int,
        default=1,
        help='Number of universities to research in parallel (default: 1, recommended max: 5)'
    )
    parser.add_argument(
        '--list', '-l',
        action='store_true',
        help='Just list universities that need to be researched, without running'
    )
    parser.add_argument(
        '--university', '-u',
        type=str,
        help='Run for a specific university only (overrides list)'
    )
    
    args = parser.parse_args()
    
    log_message("\n" + "="*60)
    log_message("Starting Next 100 Universities Collection (Ranks 101-200)")
    log_message(f"Parallel workers: {args.parallel}")
    log_message("="*60)
    
    if args.list:
        existing = get_existing_universities()
        log_message(f"\nExisting profiles: {len(existing)}")
        to_collect = [uni for uni in NEXT_100_UNIVERSITIES if not is_university_already_researched(uni, existing)]
        log_message(f"Universities to research ({len(to_collect)}):")
        for i, uni in enumerate(to_collect, 1):
            log_message(f"  {i}. {uni}")
        return
    
    asyncio.run(run_batch(parallel_count=args.parallel, specific_university=args.university))


if __name__ == "__main__":
    main()
