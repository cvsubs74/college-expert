#!/usr/bin/env python3
"""
Fix university IDs in student_college_list to use normalized format.
This ensures IDs match between college_list and college_fits indices.
"""

import os
import hashlib
from elasticsearch import Elasticsearch
from google.cloud import secretmanager

# Get credentials from Secret Manager
client = secretmanager.SecretManagerServiceClient()
project_id = 'college-counselling-478115'

def get_secret(name):
    response = client.access_secret_version(
        request={'name': f'projects/{project_id}/secrets/{name}/versions/latest'}
    )
    return response.payload.data.decode('UTF-8').strip()

ES_CLOUD_ID = get_secret('ES_CLOUD_ID')
ES_API_KEY = get_secret('ES_API_KEY')

# Connect to Elasticsearch
es = Elasticsearch(cloud_id=ES_CLOUD_ID, api_key=ES_API_KEY)

def normalize_university_id(university_id):
    """Normalize university ID for consistent matching."""
    if not university_id:
        return ''
    
    normalized = university_id.lower().strip()
    
    # Remove leading 'the_'
    if normalized.startswith('the_'):
        normalized = normalized[4:]
    
    # Remove trailing '_slug'
    if normalized.endswith('_slug'):
        normalized = normalized[:-5]
    
    # Replace hyphens with underscores
    normalized = normalized.replace('-', '_')
    
    # Remove any double underscores
    while '__' in normalized:
        normalized = normalized.replace('__', '_')
    
    return normalized

def generate_doc_id(user_email, university_id):
    """Generate document ID."""
    email_hash = hashlib.md5(user_email.encode()).hexdigest()[:8]
    return f"{email_hash}_{university_id}"

# Fetch all documents from student_college_list
print("Fetching all documents from student_college_list...")
response = es.search(
    index='student_college_list',
    body={'size': 1000, 'query': {'match_all': {}}},
    scroll='2m'
)

docs_to_update = []
docs_to_delete = []

for hit in response['hits']['hits']:
    doc_id = hit['_id']
    source = hit['_source']
    
    old_uni_id = source.get('university_id')
    normalized_uni_id = normalize_university_id(old_uni_id)
    
    if old_uni_id != normalized_uni_id:
        user_email = source.get('user_email')
        new_doc_id = generate_doc_id(user_email, normalized_uni_id)
        
        print(f"\n{old_uni_id} -> {normalized_uni_id}")
        print(f"  Old doc ID: {doc_id}")
        print(f"  New doc ID: {new_doc_id}")
        
        # Create new document with normalized ID
        new_doc = {
            **source,
            'university_id': normalized_uni_id
        }
        
        docs_to_update.append((new_doc_id, new_doc))
        docs_to_delete.append(doc_id)

print(f"\n{len(docs_to_update)} documents need normalization")

if docs_to_update:
    print("\nCreating normalized documents...")
    for doc_id, doc in docs_to_update:
        es.index(index='student_college_list', id=doc_id, body=doc, refresh=False)
    
    print("Deleting old documents...")
    for doc_id in docs_to_delete:
        es.delete(index='student_college_list', id=doc_id, ignore=[404], refresh=False)
    
    # Refresh index
    es.indices.refresh(index='student_college_list')
    print("\n✅ Normalization complete!")
else:
    print("\n✅ All IDs are already normalized!")
