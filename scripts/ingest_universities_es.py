#!/usr/bin/env python3
"""
Ingest University Profiles into Elasticsearch with semantic_text Support.

This script:
1. Reads all JSON files from the research directory
2. Indexes documents into Elasticsearch using semantic_text field type
3. Elasticsearch automatically generates embeddings using the built-in ELSER model
"""
import os
import sys
import json
import glob
from pathlib import Path
from datetime import datetime, timezone

# Add parent to path for model import
sys.path.insert(0, str(Path(__file__).parent.parent / "university_profile_collector"))

try:
    from elasticsearch import Elasticsearch
except ImportError as e:
    print(f"❌ Missing dependency: {e}")
    print("Run: pip install elasticsearch")
    sys.exit(1)

try:
    import google.generativeai as genai
except ImportError:
    print("❌ Missing dependency: google-generativeai")
    print("Run: pip install google-generativeai")
    sys.exit(1)

import time


# Configuration
ES_CLOUD_ID = os.environ.get('ES_CLOUD_ID')
ES_API_KEY = os.environ.get('ES_API_KEY')
ES_INDEX_NAME = 'knowledgebase_universities'
RESEARCH_DIR = Path(__file__).parent.parent / "agents" / "university_profile_collector" / "research"
GEMINI_MODEL = "gemini-2.0-flash-lite-preview-02-05"


# --- University Acronym Mappings ---
UNIVERSITY_ACRONYMS = {
    # California Schools
    "ucb": "University of California Berkeley",
    "uc berkeley": "University of California Berkeley",
    "berkeley": "University of California Berkeley",
    "ucla": "University of California Los Angeles",
    "ucsd": "University of California San Diego",
    "uci": "University of California Irvine",
    "ucsb": "University of California Santa Barbara",
    "ucsc": "University of California Santa Cruz",
    "ucr": "University of California Riverside",
    "ucd": "University of California Davis",
    "uc davis": "University of California Davis",
    "usc": "University of Southern California",
    "caltech": "California Institute of Technology",
    "cal tech": "California Institute of Technology",
    "stanford": "Stanford University",
    
    # Ivy League
    "mit": "Massachusetts Institute of Technology",
    "harvard": "Harvard University",
    "yale": "Yale University",
    "princeton": "Princeton University",
    "columbia": "Columbia University",
    "penn": "University of Pennsylvania",
    "upenn": "University of Pennsylvania",
    "brown": "Brown University",
    "dartmouth": "Dartmouth College",
    "cornell": "Cornell University",
    
    # Other Top Schools
    "duke": "Duke University",
    "northwestern": "Northwestern University",
    "nyu": "New York University",
    "stern": "New York University Stern School of Business",
    "nyu stern": "New York University Stern School of Business",
    "umich": "University of Michigan",
    "michigan": "University of Michigan",
    "ut austin": "University of Texas Austin",
    "gtech": "Georgia Institute of Technology",
    "georgia tech": "Georgia Institute of Technology",
    "cmu": "Carnegie Mellon University",
    "carnegie mellon": "Carnegie Mellon University",
}


def get_acronyms_for_university(official_name: str) -> list:
    """Get common acronyms/nicknames for a university based on its official name."""
    name_lower = official_name.lower()
    acronyms = []
    
    # Check for matches in our acronym mapping (reverse lookup)
    for acronym, full_name in UNIVERSITY_ACRONYMS.items():
        if full_name.lower() in name_lower or name_lower in full_name.lower():
            acronyms.append(acronym.upper())
    
    # Also add common patterns
    if "california" in name_lower and "berkeley" in name_lower:
        acronyms.extend(["UCB", "UC Berkeley", "Cal", "Berkeley"])
    elif "california" in name_lower and "los angeles" in name_lower:
        acronyms.extend(["UCLA", "UC Los Angeles"])
    elif "california" in name_lower and "san diego" in name_lower:
        acronyms.extend(["UCSD", "UC San Diego"])
    elif "california" in name_lower and "irvine" in name_lower:
        acronyms.extend(["UCI", "UC Irvine"])
    elif "california" in name_lower and "davis" in name_lower:
        acronyms.extend(["UCD", "UC Davis"])
    elif "california" in name_lower and "santa barbara" in name_lower:
        acronyms.extend(["UCSB", "UC Santa Barbara"])
    elif "massachusetts institute" in name_lower:
        acronyms.extend(["MIT"])
    elif "southern california" in name_lower:
        acronyms.extend(["USC", "Trojans"])
    elif "stanford" in name_lower:
        acronyms.extend(["Stanford", "Cardinal"])
    elif "georgia" in name_lower and "technology" in name_lower:
        acronyms.extend(["Georgia Tech", "GT", "GaTech"])
    elif "carnegie" in name_lower:
        acronyms.extend(["CMU", "Carnegie Mellon"])
    elif "new york university" in name_lower:
        acronyms.extend(["NYU"])
    
    return list(set(acronyms))  # Remove duplicates


def get_elasticsearch_client():
    """Initialize Elasticsearch client with extended timeout for ELSER inference."""
    if not ES_CLOUD_ID or not ES_API_KEY:
        raise ValueError("ES_CLOUD_ID and ES_API_KEY environment variables must be set")
    # Increase timeout to 120s for ELSER inference (default is 10s)
    return Elasticsearch(
        cloud_id=ES_CLOUD_ID, 
        api_key=ES_API_KEY,
        request_timeout=120,
        retry_on_timeout=True,
        max_retries=3
    )


def setup_gemini():
    """Initialize Gemini model."""
    api_key = os.environ.get('GEMINI_API_KEY')
    if not api_key:
        print("⚠️ GEMINI_API_KEY not found. Summaries will be template-based.")
        return None
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(GEMINI_MODEL)


def generate_llm_summary(model, profile: dict) -> str:
    """Generate detailed summary using Gemini."""
    if not model:
        return None

    uni_name = profile.get('metadata', {}).get('official_name', 'University')
    
    # Create a string representation of the profile for the LLM
    profile_str = json.dumps(profile, default=str)
    
    prompt = f"You are an expert college counselor.\n" \
             f"Create a comprehensive, engaging, and detailed sectional summary for **{uni_name}**.\n" \
             f"Use the provided JSON profile data as the complete source. Do not rely on external knowledge not present in the data.\n\n" \
             f"Structure the summary in Markdown with the following sections:\n\n" \
             f"### University Overview\n" \
             f"(A brief intro about location, size, and prestige)\n\n" \
             f"### Academic Excellence\n" \
             f"(Key colleges, majors, and academic reputation)\n\n" \
             f"### Campus Life & Culture\n" \
             f"(Student life, traditions, and atmosphere)\n\n" \
             f"### Admissions & Financials\n" \
             f"(Selectivity, key stats, cost, and aid)\n\n" \
             f"### Why {uni_name} Stands Out\n" \
             f"(Unique value proposition)\n\n" \
             f"Keep the tone professional yet inviting for prospective students.\n" \
             f"Total length should be around 400-500 words. Use bullet points where appropriate for readability.\n\n" \
             f"PROFILE DATA:\n{profile_str}"
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"  ⚠️ Gemini generation error: {e}")
        return None


def create_template_summary(profile: dict) -> str:
    """Create a concise summary of the university for display in details view."""
    parts = []
    
    # Basic info
    meta = profile.get('metadata', {})
    official_name = meta.get('official_name', 'This university')
    location = meta.get('location', {})
    city = location.get('city', '')
    state = location.get('state', '')
    uni_type = location.get('type', 'university')
    
    # Admissions data
    admissions = profile.get('admissions_data', {})
    current_status = admissions.get('current_status', {})
    acceptance_rate = current_status.get('overall_acceptance_rate')
    test_policy = current_status.get('test_policy_details', 'standard testing')
    
    # Rankings
    strategic = profile.get('strategic_profile', {})
    market_position = strategic.get('market_position', '')
    us_news_rank = None
    for ranking in strategic.get('rankings', []):
        if ranking.get('source') == 'US News' and ranking.get('rank_category') == 'National Universities':
            us_news_rank = ranking.get('rank_in_category') or ranking.get('rank_overall')
            break
    
    # Build overview paragraph
    overview = f"**{official_name}** is a {uni_type.lower()} university"
    if city and state:
        overview += f" located in {city}, {state}"
    if us_news_rank:
        overview += f", ranked #{us_news_rank} in US News National Universities"
    if acceptance_rate:
        overview += f" with a {acceptance_rate}% acceptance rate"
    if test_policy:
        overview += f" and a {test_policy.lower()} testing policy"
    overview += "."
    parts.append(overview)
    
    # Admissions paragraph
    admitted = admissions.get('admitted_student_profile', {})
    testing = admitted.get('testing', {})
    gpa_data = admitted.get('gpa', {})
    
    admissions_parts = []
    if testing.get('sat_composite_middle_50'):
        admissions_parts.append(f"SAT middle 50%: {testing['sat_composite_middle_50']}")
    if testing.get('act_composite_middle_50'):
        admissions_parts.append(f"ACT middle 50%: {testing['act_composite_middle_50']}")
    if gpa_data.get('weighted_middle_50'):
        admissions_parts.append(f"GPA middle 50%: {gpa_data['weighted_middle_50']}")
    
    early = current_status.get('early_admission_stats', [])
    if early:
        early_info = early[0]
        admissions_parts.append(f"{early_info.get('plan_type', 'Early')} acceptance rate: {early_info.get('acceptance_rate')}%")
    
    if admissions_parts:
        parts.append("**Admissions:** " + ". ".join(admissions_parts) + ".")
    
    # Academics paragraph
    academic = profile.get('academic_structure', {})
    colleges = academic.get('colleges', [])
    if colleges:
        college_names = [c.get('name', '') for c in colleges[:4] if c.get('name')]
        if college_names:
            academics_text = f"**Academics:** The university comprises {len(colleges)} colleges/schools"
            if college_names:
                academics_text += f" including {', '.join(college_names)}"
            if market_position:
                academics_text += f". {market_position}"
            parts.append(academics_text + ".")
    
    # Outcomes paragraph  
    outcomes = profile.get('outcomes', {})
    outcomes_parts = []
    if outcomes.get('median_earnings_10yr'):
        outcomes_parts.append(f"median earnings of ${outcomes['median_earnings_10yr']:,} ten years after graduation")
    if outcomes.get('employment_rate_2yr'):
        outcomes_parts.append(f"{outcomes['employment_rate_2yr']}% employment rate within 2 years")
    if outcomes.get('grad_school_rate'):
        outcomes_parts.append(f"{outcomes['grad_school_rate']}% pursue graduate studies")
    if outcomes.get('top_employers'):
        employers = outcomes['top_employers'][:3]
        outcomes_parts.append(f"top employers include {', '.join(employers)}")
    
    if outcomes_parts:
        parts.append("**Outcomes:** Graduates have " + ", ".join(outcomes_parts) + ".")
    
    # Executive summary if available
    exec_summary = strategic.get('executive_summary')
    if exec_summary and len(exec_summary) < 300:
        parts.append(f"**Profile:** {exec_summary}")
    
    return "\n\n".join(parts)


def create_searchable_text(profile: dict) -> str:
    """Create a rich text representation of the profile for semantic search."""
    parts = []
    
    # University name and basic info
    if 'metadata' in profile:
        meta = profile['metadata']
        official_name = meta.get('official_name', '')
        parts.append(f"University: {official_name}")
        
        # Add known acronyms/nicknames for better searchability
        acronyms = get_acronyms_for_university(official_name)
        if acronyms:
            parts.append(f"Also known as: {', '.join(acronyms)}")
        
        if 'location' in meta:
            loc = meta['location']
            parts.append(f"Location: {loc.get('city', '')}, {loc.get('state', '')} ({loc.get('type', '')})")
    
    # Strategic profile - executive summary and philosophy
    if 'strategic_profile' in profile:
        sp = profile['strategic_profile']
        if sp.get('executive_summary'):
            parts.append(f"Summary: {sp['executive_summary']}")
        if sp.get('admissions_philosophy'):
            parts.append(f"Admissions Philosophy: {sp['admissions_philosophy']}")
        if sp.get('market_position'):
            parts.append(f"Market Position: {sp['market_position']}")
    
    # Admissions data - comprehensive natural language
    if 'admissions_data' in profile:
        ad = profile['admissions_data']
        
        # Current status
        if 'current_status' in ad:
            cs = ad['current_status']
            if cs.get('overall_acceptance_rate'):
                parts.append(f"Acceptance Rate: {cs['overall_acceptance_rate']}% overall")
            if cs.get('transfer_acceptance_rate'):
                parts.append(f"Transfer Acceptance Rate: {cs['transfer_acceptance_rate']}%")
            if cs.get('test_policy_details'):
                parts.append(f"Test Policy: {cs['test_policy_details']}")
            if cs.get('is_test_optional'):
                parts.append("This university is test-optional.")
        
        # Admitted student profile - SAT, ACT, GPA
        if 'admitted_student_profile' in ad:
            asp = ad['admitted_student_profile']
            
            # Testing - SAT and ACT scores
            if 'testing' in asp:
                testing = asp['testing']
                if testing.get('sat_composite_middle_50'):
                    parts.append(f"SAT Score Middle 50%: {testing['sat_composite_middle_50']}")
                    parts.append(f"Admitted students typically score between {testing['sat_composite_middle_50']} on the SAT.")
                if testing.get('sat_math_middle_50'):
                    parts.append(f"SAT Math Middle 50%: {testing['sat_math_middle_50']}")
                if testing.get('sat_reading_middle_50'):
                    parts.append(f"SAT Reading Middle 50%: {testing['sat_reading_middle_50']}")
                if testing.get('act_composite_middle_50'):
                    parts.append(f"ACT Score Middle 50%: {testing['act_composite_middle_50']}")
                    parts.append(f"Admitted students typically score between {testing['act_composite_middle_50']} on the ACT.")
                if testing.get('submission_rate'):
                    parts.append(f"Test Submission Rate: {testing['submission_rate']}% of admitted students submitted test scores.")
                if testing.get('policy_note'):
                    parts.append(f"Testing Policy Note: {testing['policy_note']}")
            
            # GPA
            if 'gpa' in asp:
                gpa = asp['gpa']
                if gpa.get('weighted_middle_50'):
                    parts.append(f"Weighted GPA Middle 50%: {gpa['weighted_middle_50']}")
                    parts.append(f"Admitted students typically have a weighted GPA between {gpa['weighted_middle_50']}.")
                if gpa.get('unweighted_middle_50'):
                    parts.append(f"Unweighted GPA Middle 50%: {gpa['unweighted_middle_50']}")
                if gpa.get('average_weighted'):
                    parts.append(f"Average Weighted GPA: {gpa['average_weighted']}")
                if gpa.get('notes'):
                    parts.append(f"GPA Notes: {gpa['notes']}")
            
            # Demographics
            if 'demographics' in asp:
                demo = asp['demographics']
                if demo.get('first_gen_percentage'):
                    parts.append(f"First-Generation Students: {demo['first_gen_percentage']}%")
                if demo.get('legacy_percentage'):
                    parts.append(f"Legacy Students: {demo['legacy_percentage']}%")
                if demo.get('international_percentage'):
                    parts.append(f"International Students: {demo['international_percentage']}%")
    
    # Academic structure - colleges and majors
    if 'academic_structure' in profile:
        acs = profile['academic_structure']
        if 'colleges' in acs:
            college_names = [c.get('name', '') for c in acs['colleges'] if c.get('name')]
            if college_names:
                parts.append(f"Colleges: {', '.join(college_names[:10])}")
            
            # Extract major names
            all_majors = []
            for college in acs['colleges']:
                for major in college.get('majors', []):
                    if major.get('name'):
                        all_majors.append(major['name'])
            if all_majors:
                parts.append(f"Majors offered: {', '.join(all_majors[:20])}")
    
    # Application strategy
    if 'application_strategy' in profile:
        strat = profile['application_strategy']
        if strat.get('alternate_major_strategy'):
            parts.append(f"Application Strategy: {strat['alternate_major_strategy']}")
    
    # Student insights
    if 'student_insights' in profile:
        si = profile['student_insights']
        if si.get('what_it_takes'):
            parts.append(f"What It Takes to Get In: {'; '.join(si['what_it_takes'][:5])}")
        if si.get('essay_tips'):
            parts.append(f"Essay Tips: {'; '.join(si['essay_tips'][:3])}")
    
    # Outcomes - earnings and career
    if 'outcomes' in profile:
        out = profile['outcomes']
        if out.get('median_earnings_10yr'):
            parts.append(f"Median Earnings 10 Years After Graduation: ${out['median_earnings_10yr']:,}")
            parts.append(f"Graduates earn a median of ${out['median_earnings_10yr']:,} ten years after completing their degree.")
        if out.get('employment_rate_2yr'):
            parts.append(f"Employment Rate 2 Years After Graduation: {out['employment_rate_2yr']}%")
        if out.get('grad_school_rate'):
            parts.append(f"Graduate School Rate: {out['grad_school_rate']}% of graduates attend graduate school.")
        if out.get('top_employers'):
            employers = out['top_employers'][:5]
            parts.append(f"Top Employers: {', '.join(employers)}")
            parts.append(f"Graduates commonly work at {', '.join(employers)}.")
        if out.get('loan_default_rate'):
            parts.append(f"Loan Default Rate: {out['loan_default_rate']}%")
    
    # Financials
    if 'financials' in profile:
        fin = profile['financials']
        if fin.get('aid_philosophy'):
            parts.append(f"Financial Aid Philosophy: {fin['aid_philosophy']}")
        if fin.get('average_need_based_aid'):
            parts.append(f"Average Need-Based Aid: ${fin['average_need_based_aid']:,}")
        if fin.get('percent_receiving_aid'):
            parts.append(f"Percent Receiving Aid: {fin['percent_receiving_aid']}%")
    
    return "\n".join(parts)


def create_index_mapping(es_client, force_recreate=False):
    """Create the Elasticsearch index with semantic_text mapping."""
    
    # Define index mapping with semantic_text field
    mapping = {
        "settings": {
            "number_of_shards": 1,
            "number_of_replicas": 1,
            "analysis": {
                "analyzer": {
                    "university_analyzer": {
                        "type": "custom",
                        "tokenizer": "standard",
                        "filter": ["lowercase", "asciifolding"]
                    }
                }
            }
        },
        "mappings": {
            "properties": {
                # Document ID and metadata
                "university_id": {"type": "keyword"},
                "official_name": {
                    "type": "text",
                    "analyzer": "university_analyzer",
                    "fields": {"keyword": {"type": "keyword"}}
                },
                "location": {
                    "properties": {
                        "city": {"type": "keyword"},
                        "state": {"type": "keyword"},
                        "type": {"type": "keyword"}
                    }
                },
                
                # Semantic text field - Elasticsearch auto-generates embeddings
                # Uses the built-in ELSER inference endpoint
                "semantic_content": {
                    "type": "semantic_text",
                    "inference_id": ".elser-2-elasticsearch"
                },
                
                # Keep searchable_text for BM25 fallback and debugging
                "searchable_text": {
                    "type": "text",
                    "analyzer": "university_analyzer"
                },
                
                # Key metrics for filtering
                "acceptance_rate": {"type": "float"},
                "test_policy": {"type": "keyword"},
                "market_position": {"type": "keyword"},
                "median_earnings_10yr": {"type": "float"},
                "us_news_rank": {"type": "integer"},  # For sorting by ranking
                
                # Pre-computed summary for details view
                "summary": {"type": "text"},
                
                # Full profile stored as nested object
                "profile": {"type": "object", "enabled": False},
                
                # Timestamps
                "indexed_at": {"type": "date"},
                "last_updated": {"type": "date"}
            }
        }
    }
    
    if es_client.indices.exists(index=ES_INDEX_NAME):
        if force_recreate:
            print(f"🗑️  Deleting existing index '{ES_INDEX_NAME}'...")
            es_client.indices.delete(index=ES_INDEX_NAME)
        else:
            print(f"✅ Index '{ES_INDEX_NAME}' already exists, keeping existing data")
            return
    
    # Create index
    print(f"📦 Creating index '{ES_INDEX_NAME}' with semantic_text mapping...")
    es_client.indices.create(index=ES_INDEX_NAME, body=mapping)
    print(f"✅ Index created with semantic_text field (uses ELSER for embeddings)")


def get_existing_ids(es_client):
    """Get list of university IDs already in the index."""
    if not es_client.indices.exists(index=ES_INDEX_NAME):
        return set()
    
    try:
        result = es_client.search(
            index=ES_INDEX_NAME,
            body={"query": {"match_all": {}}, "_source": False, "size": 1000}
        )
        return {hit['_id'] for hit in result['hits']['hits']}
    except Exception as e:
        print(f"⚠️ Could not get existing IDs: {e}")
        return set()


def ingest_profiles(es_client, model=None, skip_existing=True):
    """Ingest all university profiles into Elasticsearch."""
    json_files = list(RESEARCH_DIR.glob("*.json"))
    
    if not json_files:
        print(f"❌ No JSON files found in {RESEARCH_DIR}")
        return
    
    # Get existing IDs if skipping
    existing_ids = get_existing_ids(es_client) if skip_existing else set()
    if existing_ids:
        print(f"📋 Found {len(existing_ids)} existing universities in index")
    
    print(f"\n📁 Found {len(json_files)} university profiles to process\n")
    
    success_count = 0
    skipped_count = 0
    error_count = 0
    
    for json_file in json_files:
        try:
            # Load profile to get ID
            with open(json_file, 'r', encoding='utf-8') as f:
                profile = json.load(f)
            
            university_id = profile.get('_id', json_file.stem)
            
            # Skip if already exists
            if skip_existing and university_id in existing_ids:
                print(f"⏭️  Skipping {json_file.name} (already indexed)")
                skipped_count += 1
                continue
            
            print(f"📄 Processing {json_file.name}...")
            
            # Extract key fields
            official_name = profile.get('metadata', {}).get('official_name', university_id)
            location = profile.get('metadata', {}).get('location', {})
            
            # Create searchable text - this goes into semantic_content for ELSER processing
            searchable_text = create_searchable_text(profile)
            print(f"  📝 Generated searchable text ({len(searchable_text)} chars)")
            
            # Extract metrics for filtering
            current_status = profile.get('admissions_data', {}).get('current_status', {})
            acceptance_rate = current_status.get('overall_acceptance_rate')
            test_policy = current_status.get('test_policy_details', '')
            market_position = profile.get('strategic_profile', {}).get('market_position', '')
            median_earnings = profile.get('outcomes', {}).get('median_earnings_10yr')
            last_updated = profile.get('metadata', {}).get('last_updated')
            
            # Extract US News National Universities rank for sorting
            us_news_rank = None
            rankings = profile.get('strategic_profile', {}).get('rankings', [])
            for ranking in rankings:
                if ranking.get('source') == 'US News' and ranking.get('rank_category') == 'National Universities':
                    # Use rank_in_category as primary (most profiles have this), fall back to rank_overall
                    us_news_rank = ranking.get('rank_in_category') or ranking.get('rank_overall')
                    break
            
            if us_news_rank:
                print(f"  📊 US News Rank: #{us_news_rank}")
            
            # Generate summary (try LLM first, fall back to template)
            university_summary = generate_llm_summary(model, profile) if model else None
            
            if university_summary:
                print(f"  ✨ Generated AI summary ({len(university_summary)} chars)")
                # Rate limiting for LLM
                time.sleep(1)
            else:
                university_summary = create_template_summary(profile)
                print(f"  📄 Generated template summary ({len(university_summary)} chars)")
            
            # Build document - semantic_content will be auto-embedded by ELSER
            doc = {
                "university_id": university_id,
                "official_name": official_name,
                "location": location,
                "semantic_content": searchable_text,  # ELSER will embed this automatically
                "searchable_text": searchable_text,   # Keep for BM25 fallback
                "summary": university_summary,        # Pre-computed summary for details
                "acceptance_rate": acceptance_rate,
                "test_policy": test_policy,
                "market_position": market_position,
                "median_earnings_10yr": median_earnings,
                "us_news_rank": us_news_rank,  # For sorting by rank
                "profile": profile,
                "indexed_at": datetime.now(timezone.utc).isoformat(),
                "last_updated": last_updated
            }
            
            # Index document - Elasticsearch will automatically generate embeddings
            print(f"  🧮 Indexing with ELSER semantic embeddings...")
            es_client.index(index=ES_INDEX_NAME, id=university_id, document=doc)
            print(f"  ✅ Indexed: {official_name}")
            success_count += 1
            
        except Exception as e:
            print(f"  ❌ Error processing {json_file.name}: {e}")
            error_count += 1
    
    print(f"\n{'='*50}")
    print(f"✅ Successfully indexed: {success_count}")
    print(f"⏭️  Skipped (already indexed): {skipped_count}")
    print(f"❌ Errors: {error_count}")
    print(f"📊 Total in index: {es_client.count(index=ES_INDEX_NAME)['count']}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Ingest university profiles into Elasticsearch with semantic_text")
    parser.add_argument("--force", action="store_true", help="Force re-create index and re-ingest all documents")
    args = parser.parse_args()
    
    print("="*60)
    print("🎓 University Profile Elasticsearch Ingestion (semantic_text)")
    print("="*60)
    
    if args.force:
        print("⚠️  Force mode enabled - will DELETE and RECREATE the index")
    
    # Check environment
    missing_vars = []
    if not ES_CLOUD_ID:
        missing_vars.append("ES_CLOUD_ID")
    if not ES_API_KEY:
        missing_vars.append("ES_API_KEY")
    
    if missing_vars:
        print(f"❌ Missing environment variables: {', '.join(missing_vars)}")
        print("\nSet them with:")
        print("  export ES_CLOUD_ID='your-cloud-id'")
        print("  export ES_API_KEY='your-api-key'")
        sys.exit(1)
    
    # Initialize client
    print("\n🔌 Connecting to Elasticsearch...")
    # Initialize clients
    print("\n🔌 Connecting to Elasticsearch...")
    es_client = get_elasticsearch_client()
    print("✅ Connected to Elasticsearch")

    print("\n🤖 Initializing Gemini...")
    model = setup_gemini()
    if model:
        print(f"✅ Gemini model ready: {GEMINI_MODEL}")
    else:
        print("⚠️ Gemini not configured (missing key). Will use templates.")
    print("✅ Connected to Elasticsearch")
    
    # Create index with semantic_text mapping
    create_index_mapping(es_client, force_recreate=args.force)
    
    # Ingest profiles
    ingest_profiles(es_client, model=model, skip_existing=not args.force)
    
    print("\n🎉 Ingestion complete!")
    print("\n📝 Note: semantic_text fields use Elasticsearch's built-in ELSER model.")
    print("   Queries can use simple 'match' queries for semantic search.")


if __name__ == "__main__":
    main()
