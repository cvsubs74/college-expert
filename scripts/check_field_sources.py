#!/usr/bin/env python3
"""
Check Elasticsearch profile for field_sources tracking
"""
import sys
import hashlib

# Add cloud function path
sys.path.insert(0, '/Users/cvsubramanian/CascadeProjects/graphrag/agents/college_counselor/cloud_functions/profile_manager_es')

from main import get_elasticsearch_client, ES_INDEX_NAME
import json

def check_profile(user_email):
    """Check profile and display field_sources information"""
    try:
        es_client = get_elasticsearch_client()
        
        # Calculate document ID
        document_id = hashlib.sha256(user_email.encode()).hexdigest()
        
        # Get profile
        doc = es_client.get(index=ES_INDEX_NAME, id=document_id)
        profile = doc['_source']
        
        print(f"\n{'='*60}")
        print(f"Profile Check for: {user_email}")
        print(f"{'='*60}\n")
        
        # Uploaded files
        uploaded_files = profile.get('uploaded_files', [])
        print(f"📄 Uploaded Files ({len(uploaded_files)}):")
        for i, file in enumerate(uploaded_files, 1):
            print(f"   {i}. {file}")
        
        # Field sources
        field_sources = profile.get('field_sources', {})
        print(f"\n🔍 Field Sources ({len(field_sources)} fields tracked):")
        
        if field_sources:
            for field, sources in sorted(field_sources.items()):
                print(f"   • {field}:")
                for source in sources:
                    print(f"      └─ {source}")
        else:
            print("   ⚠️  No field_sources found (profile created before tracking was implemented)")
        
        # Sample profile data
        print(f"\n📊 Sample Profile Data:")
        sample_fields = {
            'name': profile.get('name'),
            'gpa_weighted': profile.get('gpa_weighted'),
            'sat_total': profile.get('sat_total'),
            'extracurriculars': len(profile.get('extracurriculars', [])),
            'courses': len(profile.get('courses', []))
        }
        
        for key, value in sample_fields.items():
            if value:
                print(f"   • {key}: {value}")
        
        # Verification
        print(f"\n✅ Verification:")
        if field_sources:
            print(f"   ✓ Field tracking is ACTIVE")
            print(f"   ✓ {len(field_sources)} fields are being tracked")
            print(f"   ✓ Ready to test automatic cleanup on delete")
        else:
            print(f"   ⚠️ Field tracking NOT found (old profile or upload before deployment)")
            print(f"   ℹ️  Upload a new document to see tracking in action")
        
        print(f"\n{'='*60}\n")
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    
    return 0

if __name__ == '__main__':
    user_email = sys.argv[1] if len(sys.argv) > 1 else 'kaaimd@gmail.com'
    sys.exit(check_profile(user_email))
