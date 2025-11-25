#!/bin/bash
# Script to delete all documents from the university_documents Elasticsearch index

# Check if ES credentials are set
if [ -z "$ES_CLOUD_ID" ] || [ -z "$ES_API_KEY" ]; then
    echo "❌ Error: ES_CLOUD_ID and ES_API_KEY must be set"
    exit 1
fi

# Parse ES_CLOUD_ID to get the endpoint
# Format: deployment_name:base64_encoded_data
CLOUD_ID_DATA=$(echo "$ES_CLOUD_ID" | cut -d: -f2)
DECODED=$(echo "$CLOUD_ID_DATA" | base64 -d)
ENDPOINT=$(echo "$DECODED" | cut -d$ -f1)

ES_URL="https://$ENDPOINT"
INDEX_NAME="university_documents"

echo "🔌 Connecting to Elasticsearch at: $ES_URL"
echo "📋 Index: $INDEX_NAME"

# Get current document count
echo ""
echo "📊 Getting current document count..."
COUNT_RESPONSE=$(curl -s -X GET "$ES_URL/$INDEX_NAME/_count" \
  -H "Authorization: ApiKey $ES_API_KEY" \
  -H "Content-Type: application/json")

echo "Current index stats: $COUNT_RESPONSE"

# Delete all documents
echo ""
echo "🗑️  Deleting all documents from '$INDEX_NAME'..."
DELETE_RESPONSE=$(curl -s -X POST "$ES_URL/$INDEX_NAME/_delete_by_query?conflicts=proceed" \
  -H "Authorization: ApiKey $ES_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "match_all": {}
    }
  }')

echo "Delete response: $DELETE_RESPONSE"

# Verify deletion
echo ""
echo "✅ Verifying deletion..."
FINAL_COUNT=$(curl -s -X GET "$ES_URL/$INDEX_NAME/_count" \
  -H "Authorization: ApiKey $ES_API_KEY" \
  -H "Content-Type: application/json")

echo "Final index stats: $FINAL_COUNT"
