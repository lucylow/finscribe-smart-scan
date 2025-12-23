#!/bin/bash
# Demo script to process a sample invoice

set -e

API_URL="${API_URL:-http://localhost:8000}"
SAMPLE_INVOICE="${1:-examples/sample_invoice_1.png}"

if [ ! -f "$SAMPLE_INVOICE" ]; then
    echo "Error: Sample invoice not found: $SAMPLE_INVOICE"
    echo "Usage: $0 [path_to_invoice]"
    exit 1
fi

echo "Processing invoice: $SAMPLE_INVOICE"
echo "API URL: $API_URL"
echo ""

# Check if API is running
if ! curl -s "$API_URL/health" > /dev/null; then
    echo "Error: API is not running at $API_URL"
    echo "Start the API with: make dev"
    exit 1
fi

# Process invoice
echo "Sending request..."
RESPONSE=$(curl -s -X POST "$API_URL/process_invoice" \
    -F "file=@$SAMPLE_INVOICE" \
    -H "accept: application/json")

# Check if request succeeded
if echo "$RESPONSE" | grep -q "error"; then
    echo "Error processing invoice:"
    echo "$RESPONSE" | python3 -m json.tool
    exit 1
fi

# Display results
echo "✓ Invoice processed successfully!"
echo ""
echo "Response:"
echo "$RESPONSE" | python3 -m json.tool | head -50

# Extract key fields
INVOICE_ID=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('invoice_id', 'N/A'))")
CONFIDENCE=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('confidence', 0) * 100)")
IS_VALID=$(echo "$RESPONSE" | python3 -c "import sys, json; v=json.load(sys.stdin).get('validation', {}); print('PASS' if v.get('is_valid') or v.get('ok') else 'FAIL')")

echo ""
echo "Summary:"
echo "  Invoice ID: $INVOICE_ID"
echo "  Confidence: ${CONFIDENCE}%"
echo "  Validation: $IS_VALID"

