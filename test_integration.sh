#!/bin/bash

API_URL="https://ai-recommendation-api.onrender.com"
FRONTEND_URL="https://ai-powered-content-recommendation-frontend.vercel.app"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo "Testing Integration Flow..."

# Test 1: Register User
echo -e "\n${GREEN}Testing Registration...${NC}"
REGISTER_RESPONSE=$(curl -s -X POST "$API_URL/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d @- << EOF
{
  "username": "testuser",
  "email": "test@example.com",
  "password": "Test123!"
}
EOF
)

# Parse and check response
HTTP_STATUS=$(echo $REGISTER_RESPONSE | jq -r '.status // 500')
if [ $HTTP_STATUS -eq 201 ]; then
  echo "Registration successful!"
  echo "Response: $REGISTER_RESPONSE"
else
  echo -e "${RED}Registration failed!${NC}"
  echo "Response: $REGISTER_RESPONSE"
  exit 1
fi

# Test 2: Login
echo -e "\n${GREEN}Testing Login...${NC}"
LOGIN_RESPONSE=$(curl -s -X POST "$API_URL/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=test@example.com&password=Test123!")

LOGIN_TOKEN=$(echo $LOGIN_RESPONSE | jq -r '.access_token')

if [ "$LOGIN_TOKEN" != "null" ]; then
  echo "Login successful!"
else
  echo -e "${RED}Login failed!${NC}"
  echo "Response: $LOGIN_RESPONSE"
  exit 1
fi

# Test 3: Get Recommendations (Protected Route)
echo -e "\n${GREEN}Testing Protected Route...${NC}"
RECOMMENDATIONS=$(curl -s -X GET "$API_URL/api/v1/recommendations" \
  -H "Authorization: Bearer $ACCESS_TOKEN")

if [ $? -eq 0 ]; then
  echo "Successfully accessed protected route!"
  echo "First few recommendations: "
  echo $RECOMMENDATIONS | jq '.items[0:2]'
else
  echo -e "${RED}Failed to access protected route!${NC}"
  echo "Response: $RECOMMENDATIONS"
  exit 1
fi

echo -e "\n${GREEN}All tests passed successfully!${NC}" 