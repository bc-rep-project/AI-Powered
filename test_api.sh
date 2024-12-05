#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

BASE_URL="https://diplomatic-heart-production.up.railway.app"
FRONTEND_URL="https://ai-powered-content-recommendation-frontend.vercel.app"

# Function to make API requests
make_request() {
    local method=$1
    local endpoint=$2
    local headers=$3
    local data=$4

    echo -e "${CYAN}Testing endpoint: $method $BASE_URL$endpoint${NC}"
    
    if [ -n "$data" ]; then
        response=$(curl -s -X $method "$BASE_URL$endpoint" $headers -d "$data")
    else
        response=$(curl -s -X $method "$BASE_URL$endpoint" $headers)
    fi
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}Success! Response:${NC}"
        echo $response | jq '.' 2>/dev/null || echo $response
    else
        echo -e "${RED}Error occurred!${NC}"
        echo $response
    fi
    echo
}

# Test Health Check
echo -e "${YELLOW}Testing Health Check Endpoint...${NC}"
make_request "GET" "/health"

# Test Root Endpoint
echo -e "${YELLOW}Testing Root Endpoint...${NC}"
make_request "GET" "/"

# Test Authentication
echo -e "${YELLOW}Testing Authentication...${NC}"
auth_response=$(curl -s -X POST "$BASE_URL/token" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "username=test@example.com&password=password")
echo $auth_response | jq '.' 2>/dev/null || echo $auth_response
echo

# Extract token if authentication successful
token=$(echo $auth_response | jq -r '.access_token' 2>/dev/null)
if [ "$token" != "null" ] && [ -n "$token" ]; then
    # Test Protected Endpoints
    echo -e "${YELLOW}Testing Protected Endpoints...${NC}"
    make_request "GET" "/recommendations" "-H 'Authorization: Bearer $token'"
fi

# Test CORS
echo -e "${YELLOW}Testing CORS Configuration...${NC}"
make_request "OPTIONS" "/token" "-H 'Origin: $FRONTEND_URL' -H 'Access-Control-Request-Method: POST' -H 'Access-Control-Request-Headers: content-type'"