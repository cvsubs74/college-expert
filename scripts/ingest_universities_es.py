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

# Configuration
ES_CLOUD_ID = os.environ.get('ES_CLOUD_ID')
ES_API_KEY = os.environ.get('ES_API_KEY')
ES_INDEX_NAME = 'knowledgebase_universities'
RESEARCH_DIR = Path(__file__).parent.parent / "agents" / "university_profile_collector" / "research"


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


def create_searchable_text(profile: dict) -> str:
    """Create a rich text representation of the profile for semantic search."""
    parts = []
    
    # University name and basic info
    if 'metadata' in profile:
        meta = profile['metadata']
        parts.append(f"University: {meta.get('official_name', '')}")
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


def ingest_profiles(es_client, skip_existing=True):
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
            
            # Build document - semantic_content will be auto-embedded by ELSER
            doc = {
                "university_id": university_id,
                "official_name": official_name,
                "location": location,
                "semantic_content": searchable_text,  # ELSER will embed this automatically
                "searchable_text": searchable_text,   # Keep for BM25 fallback
                "acceptance_rate": acceptance_rate,
                "test_policy": test_policy,
                "market_position": market_position,
                "median_earnings_10yr": median_earnings,
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
    es_client = get_elasticsearch_client()
    print("✅ Connected to Elasticsearch")
    
    # Create index with semantic_text mapping
    create_index_mapping(es_client, force_recreate=args.force)
    
    # Ingest profiles (skip_existing=False when force mode is on)
    ingest_profiles(es_client, skip_existing=not args.force)
    
    print("\n🎉 Ingestion complete!")
    print("\n📝 Note: semantic_text fields use Elasticsearch's built-in ELSER model.")
    print("   Queries can use simple 'match' queries for semantic search.")


if __name__ == "__main__":
    main()
