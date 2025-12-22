#!/bin/bash
# Smoke test script for OCR pipeline
# Tests the full flow: upload -> staging -> OCR -> results

set -e

API_URL="${API_URL:-http://localhost:8000}"
TEST_FILE="${TEST_FILE:-examples/sample_invoice_1.png}"

echo "=========================================="
echo "FinScribe OCR Pipeline Smoke Test"
echo "=========================================="
echo "API URL: $API_URL"
echo "Test file: $TEST_FILE"
echo ""

# Check if file exists
if [ ! -f "$TEST_FILE" ]; then
    echo "❌ Test file not found: $TEST_FILE"
    echo "Please provide a valid test file path."
    exit 1
fi

# Check if API is reachable
echo "1. Checking API health..."
if ! curl -f -s "$API_URL/api/v1/health" > /dev/null; then
    echo "❌ API is not reachable at $API_URL"
    echo "Make sure docker-compose is running: docker-compose up"
    exit 1
fi
echo "✅ API is reachable"

# Upload file
echo ""
echo "2. Uploading test file..."
UPLOAD_RESPONSE=$(curl -s -X POST \
    -F "file=@$TEST_FILE" \
    "$API_URL/api/v1/analyze-ocr")

JOB_ID=$(echo "$UPLOAD_RESPONSE" | grep -o '"job_id":"[^"]*"' | cut -d'"' -f4)

if [ -z "$JOB_ID" ]; then
    echo "❌ Failed to get job_id from upload response:"
    echo "$UPLOAD_RESPONSE"
    exit 1
fi

echo "✅ File uploaded. Job ID: $JOB_ID"

# Poll for job status
echo ""
echo "3. Polling job status..."
MAX_ATTEMPTS=30
ATTEMPT=0
STATUS="queued"

while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    ATTEMPT=$((ATTEMPT + 1))
    echo "  Attempt $ATTEMPT/$MAX_ATTEMPTS..."
    
    STATUS_RESPONSE=$(curl -s "$API_URL/api/v1/jobs/$JOB_ID")
    STATUS=$(echo "$STATUS_RESPONSE" | grep -o '"status":"[^"]*"' | cut -d'"' -f4 || echo "unknown")
    
    echo "  Status: $STATUS"
    
    if [ "$STATUS" = "completed" ]; then
        echo "✅ Job completed!"
        break
    elif [ "$STATUS" = "failed" ]; then
        echo "❌ Job failed!"
        echo "Response: $STATUS_RESPONSE"
        exit 1
    fi
    
    sleep 2
done

if [ "$STATUS" != "completed" ]; then
    echo "❌ Job did not complete within timeout"
    exit 1
fi

# Check for OCR artifacts
echo ""
echo "4. Checking OCR artifacts..."
# Note: This would require access to storage to verify artifacts
# For now, we just verify the job completed

echo ""
echo "=========================================="
echo "✅ Smoke test passed!"
echo "=========================================="
echo "Job ID: $JOB_ID"
echo "Final status: $STATUS"
echo ""
echo "To inspect results:"
echo "  curl $API_URL/api/v1/jobs/$JOB_ID"
echo ""

