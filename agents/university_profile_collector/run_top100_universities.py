#!/usr/bin/env python3
"""
Batch script to collect profiles for Top 100 US universities.
Runs the agent directly in console (no server needed).
Skips universities that already have data in the research folder.
After saving, ingests into Elasticsearch knowledge base.

Features:
- Parallel processing: Run multiple university research tasks simultaneously
- Smart exclusion: Skip universities that already have research files
- Validation: Validate each profile against the Pydantic schema
- ES Ingestion: Automatically ingest valid profiles to Elasticsearch

Usage:
  python run_top100_universities.py                    # Sequential (1 at a time)
  python run_top100_universities.py --parallel 3       # 3 universities in parallel
  python run_top100_universities.py --parallel 5       # 5 universities in parallel
"""

import os
import sys
import asyncio
import re
import json
import glob
import argparse
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
LOG_FILE = os.path.join(os.path.dirname(__file__), "batch_run_log.txt")

# ES Configuration
ES_CLOUD_ID = os.environ.get('ES_CLOUD_ID')
ES_API_KEY = os.environ.get('ES_API_KEY')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
ES_INDEX_NAME = 'knowledgebase_universities'
EMBEDDING_DIM = 768

# Top 100 US Universities (US News 2025 National Universities Rankings)
TOP_100_UNIVERSITIES = [
    "Princeton University",
    "Massachusetts Institute of Technology",
    "Harvard University",
    "Stanford University",
    "Yale University",
    "Duke University",
    "California Institute of Technology",
    "Northwestern University",
    "Johns Hopkins University",
    "Columbia University",
    "University of Chicago",
    "University of Pennsylvania",
    "Cornell University",
    "Brown University",
    "Rice University",
    "Dartmouth College",
    "Vanderbilt University",
    "Carnegie Mellon University",
    "Washington University in St. Louis",
    "Emory University",
    "University of Notre Dame",
    "Georgetown University",
    "University of California, Berkeley",
    "University of California, Los Angeles",
    "University of Virginia",
    "University of Michigan, Ann Arbor",
    "University of Southern California",
    "New York University",
    "University of Florida",
    "University of North Carolina at Chapel Hill",
    "Wake Forest University",
    "Tufts University",
    "University of California, San Diego",
    "University of California, Santa Barbara",
    "University of Rochester",
    "Boston College",
    "Georgia Institute of Technology",
    "University of California, Irvine",
    "University of California, Davis",
    "University of Texas at Austin",
    "College of William and Mary",
    "Boston University",
    "Tulane University",
    "Brandeis University",
    "Case Western Reserve University",
    "University of Wisconsin-Madison",
    "University of Illinois Urbana-Champaign",
    "Ohio State University",
    "Purdue University",
    "Villanova University",
    "University of Georgia",
    "Lehigh University",
    "University of Miami",
    "Pepperdine University",
    "Northeastern University",
    "Rensselaer Polytechnic Institute",
    "University of Washington",
    "Santa Clara University",
    "University of Maryland, College Park",
    "George Washington University",
    "Syracuse University",
    "University of Pittsburgh",
    "Rutgers University-New Brunswick",
    "University of Connecticut",
    "University of Minnesota Twin Cities",
    "Virginia Tech",
    "Texas A&M University",
    "Fordham University",
    "University of Massachusetts Amherst",
    "Stevens Institute of Technology",
    "Indiana University Bloomington",
    "University of California, Merced",
    "University of Colorado Boulder",
    "North Carolina State University",
    "Pennsylvania State University",
    "University of Delaware",
    "Florida State University",
    "University of Iowa",
    "Southern Methodist University",
    "University of South Florida",
    "Clemson University",
    "Stony Brook University-SUNY",
    "University of Denver",
    "University at Buffalo-SUNY",
    "Loyola Marymount University",
    "Chapman University",
    "Michigan State University",
    "American University",
    "Baylor University",
    "Howard University",
    "Illinois Institute of Technology",
    "Marquette University",
    "Auburn University",
    "Drexel University",
    "Gonzaga University",
    "University of Arizona",
    "Creighton University",
    "University of Oregon",
    "Temple University",
    "University of San Diego"
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
    # Generate multiple possible IDs for this university
    name_lower = university_name.lower()
    
    # Common variations
    variations = [
        get_university_id(university_name),
        name_lower.replace(' ', '_').replace(',', '').replace('-', '_'),
        name_lower.replace('university of ', '').replace(' ', '_').replace(',', ''),
        name_lower.replace(', ', '_').replace(' ', '_'),
    ]
    
    # Special case handling for common abbreviations
    abbreviations = {
        'university of california, berkeley': ['ucb', 'uc_berkeley', 'university_of_california_berkeley'],
        'university of california, los angeles': ['ucla', 'uc_los_angeles', 'university_of_california_los_angeles'],
        'university of california, san diego': ['ucsd', 'uc_san_diego', 'university_of_california_san_diego'],
        'university of california, santa barbara': ['ucsb', 'uc_santa_barbara', 'university_of_california_santa_barbara'],
        'university of california, irvine': ['uci', 'uc_irvine', 'university_of_california_irvine'],
        'university of california, davis': ['ucd', 'uc_davis', 'university_of_california_davis'],
        'university of illinois urbana-champaign': ['uiuc', 'university_of_illinois_urbana_champaign'],
        'university of southern california': ['usc', 'university_of_southern_california'],
        'massachusetts institute of technology': ['mit', 'massachusetts_institute_of_technology'],
        'california institute of technology': ['caltech', 'california_institute_of_technology'],
        'georgia institute of technology': ['georgia_tech', 'georgia_institute_of_technology'],
        'new york university': ['nyu', 'new_york_university'],
        'university of michigan, ann arbor': ['umich', 'university_of_michigan', 'university_of_michigan_ann_arbor'],
        'washington university in st. louis': ['washu', 'washington_university_in_st_louis', 'washington_university_st_louis'],
    }
    
    for key, abbrevs in abbreviations.items():
        if key in name_lower or name_lower in key:
            variations.extend(abbrevs)
    
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
    async with semaphore if semaphore else asyncio.nullcontext():
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
            log_message(f"Error researching {university}: {str(e)}")
            return False, university


async def run_batch(parallel_count: int = 1):
    """Run the batch collection for top 100 universities.
    
    Args:
        parallel_count: Number of universities to process in parallel (default: 1)
    """
    existing = get_existing_universities()
    log_message(f"Found {len(existing)} existing university profiles in research folder.")
    
    # Filter out already collected universities using improved matching
    to_collect = []
    for uni in TOP_100_UNIVERSITIES:
        if is_university_already_researched(uni, existing):
            log_message(f"Skip: {uni} (already researched)")
        else:
            to_collect.append(uni)
    
    log_message(f"\n📊 Summary: {len(TOP_100_UNIVERSITIES) - len(to_collect)} already done, {len(to_collect)} remaining\n")
    
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
        description="Batch collect university profiles for top 100 US universities.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_top100_universities.py                    # Sequential (1 at a time)
  python run_top100_universities.py --parallel 3       # 3 universities in parallel
  python run_top100_universities.py --parallel 5       # 5 universities in parallel (recommended max)
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
    
    args = parser.parse_args()
    
    log_message("\n" + "="*60)
    log_message("Starting Top 100 Universities Collection")
    log_message(f"Parallel workers: {args.parallel}")
    log_message("="*60)
    
    if args.list:
        existing = get_existing_universities()
        log_message(f"\nExisting profiles: {len(existing)}")
        to_collect = [uni for uni in TOP_100_UNIVERSITIES if not is_university_already_researched(uni, existing)]
        log_message(f"Universities to research ({len(to_collect)}):")
        for i, uni in enumerate(to_collect, 1):
            log_message(f"  {i}. {uni}")
        return
    
    asyncio.run(run_batch(parallel_count=args.parallel))


if __name__ == "__main__":
    main()

