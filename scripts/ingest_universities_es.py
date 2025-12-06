#!/usr/bin/env python3
"""
Ingest University Profiles into Elasticsearch with Hybrid Search Support.

This script:
1. Reads all JSON files from the research directory
2. Generates embeddings for searchable text using Gemini
3. Indexes documents into Elasticsearch with vector fields for hybrid search
"""
import os
import sys
import json
import glob
from pathlib import Path
from datetime import datetime

# Add parent to path for model import
sys.path.insert(0, str(Path(__file__).parent.parent / "university_profile_collector"))

try:
    from elasticsearch import Elasticsearch
    import google.generativeai as genai
except ImportError as e:
    print(f"❌ Missing dependency: {e}")
    print("Run: pip install elasticsearch google-generativeai")
    sys.exit(1)

# Configuration
ES_CLOUD_ID = os.environ.get('ES_CLOUD_ID')
ES_API_KEY = os.environ.get('ES_API_KEY')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
ES_INDEX_NAME = 'knowledgebase_universities'
RESEARCH_DIR = Path(__file__).parent.parent / "agents" / "university_profile_collector" / "research"

# Embedding dimension for Gemini text-embedding-004
EMBEDDING_DIM = 768


def get_elasticsearch_client():
    """Initialize Elasticsearch client."""
    if not ES_CLOUD_ID or not ES_API_KEY:
        raise ValueError("ES_CLOUD_ID and ES_API_KEY environment variables must be set")
    return Elasticsearch(cloud_id=ES_CLOUD_ID, api_key=ES_API_KEY)


def init_gemini():
    """Initialize Gemini API for embeddings."""
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY environment variable must be set")
    genai.configure(api_key=GEMINI_API_KEY)


def generate_embedding(text: str) -> list:
    """Generate embedding vector using Gemini text-embedding-004."""
    try:
        # Truncate text if too long (Gemini has token limits)
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
        print(f"  ⚠️ Embedding failed: {e}")
        return [0.0] * EMBEDDING_DIM  # Return zero vector on failure


def create_searchable_text(profile: dict) -> str:
    """Create a rich text representation of the profile for embedding."""
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
    
    # Admissions data highlights
    if 'admissions_data' in profile:
        ad = profile['admissions_data']
        if 'current_status' in ad:
            cs = ad['current_status']
            parts.append(f"Acceptance Rate: {cs.get('overall_acceptance_rate', 'N/A')}%")
            parts.append(f"Test Policy: {cs.get('test_policy_details', 'N/A')}")
    
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
                parts.append(f"Majors: {', '.join(all_majors[:20])}")
    
    # Application strategy
    if 'application_strategy' in profile:
        strat = profile['application_strategy']
        if strat.get('alternate_major_strategy'):
            parts.append(f"Strategy: {strat['alternate_major_strategy']}")
    
    # Student insights
    if 'student_insights' in profile:
        si = profile['student_insights']
        if si.get('what_it_takes'):
            parts.append(f"What It Takes: {'; '.join(si['what_it_takes'][:5])}")
    
    # Outcomes
    if 'outcomes' in profile:
        out = profile['outcomes']
        if out.get('median_earnings_10yr'):
            parts.append(f"Median Earnings (10yr): ${out['median_earnings_10yr']:,}")
        if out.get('top_employers'):
            parts.append(f"Top Employers: {', '.join(out['top_employers'][:5])}")
    
    return "\n".join(parts)


def create_index_mapping(es_client):
    """Create the Elasticsearch index with hybrid search mapping."""
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
                
                # Searchable text for BM25
                "searchable_text": {
                    "type": "text",
                    "analyzer": "university_analyzer"
                },
                
                # Vector field for semantic search
                "embedding": {
                    "type": "dense_vector",
                    "dims": EMBEDDING_DIM,
                    "index": True,
                    "similarity": "cosine"
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
    
    # Delete if exists
    if es_client.indices.exists(index=ES_INDEX_NAME):
        print(f"🗑️  Deleting existing index '{ES_INDEX_NAME}'...")
        es_client.indices.delete(index=ES_INDEX_NAME)
    
    # Create index
    print(f"📦 Creating index '{ES_INDEX_NAME}'...")
    es_client.indices.create(index=ES_INDEX_NAME, body=mapping)
    print(f"✅ Index created with hybrid search mapping")


def ingest_profiles(es_client):
    """Ingest all university profiles into Elasticsearch."""
    json_files = list(RESEARCH_DIR.glob("*.json"))
    
    if not json_files:
        print(f"❌ No JSON files found in {RESEARCH_DIR}")
        return
    
    print(f"\n📁 Found {len(json_files)} university profiles to ingest\n")
    
    success_count = 0
    error_count = 0
    
    for json_file in json_files:
        try:
            print(f"📄 Processing {json_file.name}...")
            
            # Load profile
            with open(json_file, 'r', encoding='utf-8') as f:
                profile = json.load(f)
            
            # Extract key fields
            university_id = profile.get('_id', json_file.stem)
            official_name = profile.get('metadata', {}).get('official_name', university_id)
            location = profile.get('metadata', {}).get('location', {})
            
            # Create searchable text and generate embedding
            searchable_text = create_searchable_text(profile)
            print(f"  📝 Generated searchable text ({len(searchable_text)} chars)")
            
            embedding = generate_embedding(searchable_text)
            print(f"  🧮 Generated embedding ({len(embedding)} dims)")
            
            # Extract metrics for filtering
            current_status = profile.get('admissions_data', {}).get('current_status', {})
            acceptance_rate = current_status.get('overall_acceptance_rate')
            test_policy = current_status.get('test_policy_details', '')
            market_position = profile.get('strategic_profile', {}).get('market_position', '')
            median_earnings = profile.get('outcomes', {}).get('median_earnings_10yr')
            last_updated = profile.get('metadata', {}).get('last_updated')
            
            # Build document
            doc = {
                "university_id": university_id,
                "official_name": official_name,
                "location": location,
                "searchable_text": searchable_text,
                "embedding": embedding,
                "acceptance_rate": acceptance_rate,
                "test_policy": test_policy,
                "market_position": market_position,
                "median_earnings_10yr": median_earnings,
                "profile": profile,
                "indexed_at": datetime.utcnow().isoformat(),
                "last_updated": last_updated
            }
            
            # Index document
            es_client.index(index=ES_INDEX_NAME, id=university_id, document=doc)
            print(f"  ✅ Indexed: {official_name}")
            success_count += 1
            
        except Exception as e:
            print(f"  ❌ Error processing {json_file.name}: {e}")
            error_count += 1
    
    print(f"\n{'='*50}")
    print(f"✅ Successfully indexed: {success_count}")
    print(f"❌ Errors: {error_count}")
    print(f"📊 Total in index: {es_client.count(index=ES_INDEX_NAME)['count']}")


def main():
    print("="*60)
    print("🎓 University Profile Elasticsearch Ingestion")
    print("="*60)
    
    # Check environment
    missing_vars = []
    if not ES_CLOUD_ID:
        missing_vars.append("ES_CLOUD_ID")
    if not ES_API_KEY:
        missing_vars.append("ES_API_KEY")
    if not GEMINI_API_KEY:
        missing_vars.append("GEMINI_API_KEY")
    
    if missing_vars:
        print(f"❌ Missing environment variables: {', '.join(missing_vars)}")
        print("\nSet them with:")
        print("  export ES_CLOUD_ID='your-cloud-id'")
        print("  export ES_API_KEY='your-api-key'")
        print("  export GEMINI_API_KEY='your-gemini-key'")
        sys.exit(1)
    
    # Initialize clients
    print("\n🔌 Connecting to Elasticsearch...")
    es_client = get_elasticsearch_client()
    print("✅ Connected to Elasticsearch")
    
    print("\n🔌 Initializing Gemini for embeddings...")
    init_gemini()
    print("✅ Gemini initialized")
    
    # Create index
    create_index_mapping(es_client)
    
    # Ingest profiles
    ingest_profiles(es_client)
    
    print("\n🎉 Ingestion complete!")


if __name__ == "__main__":
    main()
