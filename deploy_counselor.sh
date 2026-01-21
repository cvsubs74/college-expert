#!/bin/bash
set -e

PROJECT_ID=${GCP_PROJECT_ID:-"college-counselling-478115"}
REGION="us-east1"
FUNCTION_NAME="counselor-agent"

echo "Deploying $FUNCTION_NAME to $REGION..."

gcloud functions deploy $FUNCTION_NAME \
  --gen2 \
  --runtime=python312 \
  --region=$REGION \
  --source=cloud_functions/counselor_agent \
  --entry-point=counselor_agent_http \
  --trigger-http \
  --allow-unauthenticated \
  --set-env-vars PROFILE_MANAGER_URL="https://$REGION-$PROJECT_ID.cloudfunctions.net/profile-manager-v2",KNOWLEDGE_BASE_UNIVERSITIES_URL="https://$REGION-$PROJECT_ID.cloudfunctions.net/knowledge-base-manager-universities-v2"

echo "Deployment complete."
