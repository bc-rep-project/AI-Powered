#!/bin/bash

# Test script for AI Content Recommendation API
BASE_URL="https://ai-powered-production.up.railway.app"
TEST_EMAIL="test@example.com"
TEST_PASSWORD="password"
TEST_NAME="Test User"

echo -e "\nTesting Health Check Endpoint..."
echo "Testing endpoint: GET $BASE_URL/health"
HEALTH_RESPONSE=$(curl -s "$BASE_URL/health")
echo "Success! Response:"
echo $HEALTH_RESPONSE | jq '.'

echo -e "\nTesting Root Endpoint..."
echo "Testing endpoint: GET $BASE_URL/"
ROOT_RESPONSE=$(curl -s "$BASE_URL/")
echo "Success! Response:"
echo $ROOT_RESPONSE | jq '.'

echo -e "\nTesting User Registration..."
echo "Testing endpoint: POST $BASE_URL/api/v1/auth/register"
REGISTER_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$TEST_EMAIL\",\"password\":\"$TEST_PASSWORD\",\"name\":\"$TEST_NAME\"}")

if [[ $REGISTER_RESPONSE == *"error"* ]]; then
  echo "Note: Registration failed (user might already exist). Response:"
else
  echo "Success! Response:"
fi
echo $REGISTER_RESPONSE | jq '.'

echo -e "\nTesting Authentication..."
echo "Testing endpoint: POST $BASE_URL/token"
TOKEN_RESPONSE=$(curl -s -X POST "$BASE_URL/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=$TEST_EMAIL&password=$TEST_PASSWORD&grant_type=password")

if [[ $TOKEN_RESPONSE == *"error"* ]]; then
  echo "Error occurred! Response:"
  echo $TOKEN_RESPONSE | jq '.'
  exit 1
else
  echo "Success! Response:"
  echo $TOKEN_RESPONSE | jq '.'
  TOKEN=$(echo $TOKEN_RESPONSE | jq -r '.access_token')
fi

echo -e "\nTesting Protected Endpoints..."
echo "Using token: $TOKEN"

echo "Testing endpoint: GET $BASE_URL/api/v1/recommendations"
RECOMMENDATIONS_RESPONSE=$(curl -s -X GET "$BASE_URL/api/v1/recommendations" \
  -H "Authorization: Bearer $TOKEN")

if [[ $RECOMMENDATIONS_RESPONSE == *"error"* ]]; then
  echo "Error occurred! Response:"
else
  echo "Success! Response:"
fi
echo $RECOMMENDATIONS_RESPONSE | jq '.'

echo -e "\nTesting CORS Configuration..."
echo "Testing endpoint: OPTIONS $BASE_URL/token"
CORS_RESPONSE=$(curl -s -X OPTIONS "$BASE_URL/token" \
  -H "Origin: https://ai-powered-content-recommendation-frontend.vercel.app" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: content-type,authorization" \
  -v 2>&1)

echo "Response headers:"
echo "$CORS_RESPONSE" | grep -i "< access-control"

echo "OK"