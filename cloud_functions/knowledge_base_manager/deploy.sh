#!/bin/bash

# Deploy Knowledge Base Manager Cloud Function

set -e

PROJECT_ID="college-counselling-478115"
REGION="us-east1"
FUNCTION_NAME="knowledge-base-manager"

echo "Deploying Knowledge Base Manager Cloud Function..."
gcloud functions deploy $FUNCTION_NAME \
    --gen2 \
    --runtime=python312 \
    --region=$REGION \
    --source=. \
    --entry-point=knowledge_base_manager \
    --trigger-http \
    --allow-unauthenticated \
    --env-vars-file=.env.yaml \
    --project=$PROJECT_ID \
    --timeout=540s \
    --memory=512MB

echo ""
echo "✅ Knowledge Base Manager deployed successfully!"
echo ""
echo "Function URL:"
gcloud functions describe $FUNCTION_NAME --region=$REGION --project=$PROJECT_ID --format='value(serviceConfig.uri)'
