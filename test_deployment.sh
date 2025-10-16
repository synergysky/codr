#!/bin/bash
# Test script for Railway deployment

# Configuration
RAILWAY_URL="${1:-https://codr-dev.up.railway.app}"
WEBHOOK_TOKEN="${2:-your-token-here}"

echo "🧪 Testing Railway deployment at: $RAILWAY_URL"
echo ""

# Test 1: Health check
echo "1️⃣  Testing health endpoint..."
HEALTH_RESPONSE=$(curl -s -w "\n%{http_code}" "$RAILWAY_URL/health")
HTTP_CODE=$(echo "$HEALTH_RESPONSE" | tail -n1)
BODY=$(echo "$HEALTH_RESPONSE" | head -n-1)

if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ Health check passed"
    echo "   Response: $BODY"
else
    echo "❌ Health check failed (HTTP $HTTP_CODE)"
    exit 1
fi
echo ""

# Test 2: Unauthorized webhook
echo "2️⃣  Testing webhook without token (should fail)..."
UNAUTH_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$RAILWAY_URL/webhook/zenhub" \
  -H "Content-Type: application/json" \
  -d '{"type":"test"}')
HTTP_CODE=$(echo "$UNAUTH_RESPONSE" | tail -n1)

if [ "$HTTP_CODE" = "401" ]; then
    echo "✅ Unauthorized request correctly rejected"
else
    echo "❌ Expected 401, got HTTP $HTTP_CODE"
fi
echo ""

# Test 3: Authorized webhook
echo "3️⃣  Testing webhook with token..."
WEBHOOK_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$RAILWAY_URL/webhook/zenhub?token=$WEBHOOK_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "issue.transfer",
    "issue_number": 999,
    "to_pipeline": {"name": "In Progress"}
  }')
HTTP_CODE=$(echo "$WEBHOOK_RESPONSE" | tail -n1)
BODY=$(echo "$WEBHOOK_RESPONSE" | head -n-1)

if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ Webhook accepted"
    echo "   Response: $BODY"
else
    echo "❌ Webhook failed (HTTP $HTTP_CODE)"
    echo "   Response: $BODY"
fi
echo ""

echo "🎉 All tests completed!"
echo ""
echo "Next steps:"
echo "  1. Check Railway logs for dispatch messages"
echo "  2. Check GitHub Actions for repository_dispatch events"
echo "  3. Configure Zenhub webhook to use: $RAILWAY_URL/webhook/zenhub?token=$WEBHOOK_TOKEN"
