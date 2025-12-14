#!/bin/bash
# Script to compute fits for all universities using batched API endpoint
# Uses the new compute-all-fits with batch_size and offset parameters

USER_EMAIL="cvsubs@gmail.com"
API_BASE="https://profile-manager-es-pfnwjfp26a-ue.a.run.app"
BATCH_SIZE=10

echo "=== Batched Fit Computation Script ==="
echo "User: $USER_EMAIL"
echo "Batch Size: $BATCH_SIZE"
echo ""

OFFSET=0
TOTAL=0
TOTAL_COMPUTED=0
BATCH_NUM=0

while true; do
    BATCH_NUM=$((BATCH_NUM + 1))
    
    echo -n "Batch $BATCH_NUM (offset $OFFSET)... "
    
    # Call the batched API endpoint
    RESPONSE=$(curl -s -X POST "${API_BASE}/compute-all-fits" \
        -H "Content-Type: application/json" \
        -d "{\"user_email\": \"${USER_EMAIL}\", \"batch_size\": ${BATCH_SIZE}, \"offset\": ${OFFSET}}" \
        --max-time 300)
    
    # Parse response
    SUCCESS=$(echo "$RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('success', False))" 2>/dev/null)
    COMPUTED=$(echo "$RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('computed', 0))" 2>/dev/null)
    HAS_MORE=$(echo "$RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('has_more', False))" 2>/dev/null)
    NEXT_OFFSET=$(echo "$RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('next_offset', 0))" 2>/dev/null)
    TOTAL_UNI=$(echo "$RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('total_universities', 0))" 2>/dev/null)
    TOTAL_COMP=$(echo "$RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('total_computed', 0))" 2>/dev/null)
    
    if [ "$SUCCESS" != "True" ]; then
        ERROR=$(echo "$RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('error', 'Unknown error'))" 2>/dev/null)
        echo "❌ Error: $ERROR"
        exit 1
    fi
    
    TOTAL_COMPUTED=$TOTAL_COMP
    TOTAL=$TOTAL_UNI
    
    echo "✅ Computed $COMPUTED (Total: $TOTAL_COMPUTED/$TOTAL)"
    
    if [ "$HAS_MORE" != "True" ]; then
        break
    fi
    
    OFFSET=$NEXT_OFFSET
    
    # Small delay between batches
    sleep 1
done

echo ""
echo "========================================"
echo "Processing complete!"
echo "Total universities: $TOTAL"
echo "Total computed: $TOTAL_COMPUTED"
