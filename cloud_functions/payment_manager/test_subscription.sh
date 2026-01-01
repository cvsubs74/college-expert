#!/bin/bash
# Test script for subscription endpoints
# Run payment_manager locally first: functions-framework --target=payment_manager --port=8081

BASE_URL="http://localhost:8081"
TEST_EMAIL="test@example.com"

echo "=== Testing Subscription Management Endpoints ==="
echo ""

echo "1. Get Subscription Status"
curl -X GET "${BASE_URL}/subscription-status" \
  -H "Content-Type: application/json" \
  -H "X-User-Email: ${TEST_EMAIL}"
echo -e "\n"

echo "2. Cancel Subscription (Downgrade to Free)"
curl -X POST "${BASE_URL}/cancel-subscription" \
  -H "Content-Type: application/json" \
  -H "X-User-Email: ${TEST_EMAIL}" \
  -d '{}'
echo -e "\n"

echo "3. Get Subscription Status Again (should show cancel_at_period_end=true)"
curl -X GET "${BASE_URL}/subscription-status" \
  -H "Content-Type: application/json" \
  -H "X-User-Email: ${TEST_EMAIL}"
echo -e "\n"

echo "4. Reactivate Subscription"
curl -X POST "${BASE_URL}/reactivate-subscription" \
  -H "Content-Type: application/json" \
  -H "X-User-Email: ${TEST_EMAIL}" \
  -d '{}'
echo -e "\n"

echo "5. Get Subscription Status Again (should show cancel_at_period_end=false)"
curl -X GET "${BASE_URL}/subscription-status" \
  -H "Content-Type: application/json" \
  -H "X-User-Email: ${TEST_EMAIL}"
echo -e "\n"

echo "=== Test Complete ==="
