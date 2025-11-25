#!/usr/bin/env python3
"""
Script to delete all documents from the university_documents Elasticsearch index.
"""
import os
from elasticsearch import Elasticsearch

# Configuration
ES_CLOUD_ID = os.environ.get('ES_CLOUD_ID')
ES_API_KEY = os.environ.get('ES_API_KEY')
ES_INDEX_NAME = 'university_documents'

def clear_index():
    """Delete all documents from the index."""
    if not ES_CLOUD_ID or not ES_API_KEY:
        print("❌ Error: ES_CLOUD_ID and ES_API_KEY environment variables must be set")
        return
    
    # Connect to Elasticsearch
    print(f"🔌 Connecting to Elasticsearch...")
    es_client = Elasticsearch(
        cloud_id=ES_CLOUD_ID,
        api_key=ES_API_KEY
    )
    
    # Check if index exists
    if not es_client.indices.exists(index=ES_INDEX_NAME):
        print(f"⚠️  Index '{ES_INDEX_NAME}' does not exist")
        return
    
    # Get current document count
    count_response = es_client.count(index=ES_INDEX_NAME)
    doc_count = count_response['count']
    print(f"📊 Current document count: {doc_count}")
    
    if doc_count == 0:
        print(f"✅ Index '{ES_INDEX_NAME}' is already empty")
        return
    
    # Delete all documents
    print(f"🗑️  Deleting all documents from '{ES_INDEX_NAME}'...")
    delete_response = es_client.delete_by_query(
        index=ES_INDEX_NAME,
        body={
            "query": {
                "match_all": {}
            }
        }
    )
    
    deleted_count = delete_response.get('deleted', 0)
    print(f"✅ Successfully deleted {deleted_count} documents")
    
    # Verify
    final_count = es_client.count(index=ES_INDEX_NAME)['count']
    print(f"📊 Final document count: {final_count}")

if __name__ == "__main__":
    clear_index()
