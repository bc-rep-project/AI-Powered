#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'
CYAN='\033[0;36m'

# Configuration
API_URL="https://ai-powered-production.up.railway.app"
MONGODB_URL="mongodb+srv://johannderbiel:Fd0lLdKvUYxmRH9l@cluster0.bh0nl.mongodb.net/recommendation_engine?retryWrites=true&w=majority"
REDIS_URL="redis://default:gXzklmY9SM0YTIisyDEct4T6hGXJEbvS@redis-13150.c341.af-south-1-1.ec2.redns.redis-cloud.com:13150"

echo -e "${CYAN}Starting Integration Tests${NC}"

# Test 1: MongoDB Connection
echo -e "\n${CYAN}Testing MongoDB Connection...${NC}"
if mongosh "$MONGODB_URL" --eval "db.runCommand({ ping: 1 })" &>/dev/null; then
    echo -e "${GREEN}MongoDB Connection Successful${NC}"
else
    echo -e "${RED}MongoDB Connection Failed${NC}"
fi

# Test 2: Redis Connection
echo -e "\n${CYAN}Testing Redis Connection...${NC}"
if ! command -v redis-cli &> /dev/null; then
    echo -e "${RED}Redis CLI not found. Please install Redis tools using one of these methods:${NC}"
    echo "1. Using Chocolatey (recommended): choco install redis-64"
    echo "2. Download Redis for Windows from: https://github.com/microsoftarchive/redis/releases"
    echo "3. Using WSL: wsl -e sudo apt-get install redis-tools"
    echo -e "${RED}Redis Connection Failed${NC}"
else
    REDIS_RESPONSE=$(redis-cli -u "$REDIS_URL" ping 2>&1)
    if [ "$REDIS_RESPONSE" = "PONG" ]; then
        echo -e "${GREEN}Redis Connection Successful${NC}"
    else
        echo -e "${RED}Redis Connection Failed${NC}"
        echo "Response: $REDIS_RESPONSE"
    fi
fi

# Test 3: API Health Check
echo -e "\n${CYAN}Testing API Health...${NC}"
HEALTH_RESPONSE=$(curl -s "$API_URL/health")
echo "Health Response: $HEALTH_RESPONSE"
if echo "$HEALTH_RESPONSE" | grep -q '"status":"healthy"'; then
    echo -e "${GREEN}API Health Check Successful${NC}"
else
    echo -e "${RED}API Health Check Failed${NC}"
fi

# Test 4: User Registration
echo -e "\n${CYAN}Testing User Registration...${NC}"
echo "Sending registration request to $API_URL/api/v1/auth/register"
REGISTER_RESPONSE=$(curl -s -X POST "$API_URL/api/v1/auth/register" \
    -H "Content-Type: application/json" \
    -d '{
        "email": "test@example.com",
        "password": "testpass123",
        "full_name": "Test User"
    }')

echo "Registration Response: $REGISTER_RESPONSE"
if echo "$REGISTER_RESPONSE" | jq -e '.user_id' >/dev/null; then
    echo -e "${GREEN}User Registration Successful${NC}"
else
    echo -e "${RED}User Registration Failed${NC}"
    echo "Error: $(echo "$REGISTER_RESPONSE" | jq -r '.detail // .message // .')"
fi

# Test 5: Authentication
echo -e "\n${CYAN}Testing Authentication...${NC}"
echo "Sending authentication request to $API_URL/api/v1/auth/token"
TOKEN_RESPONSE=$(curl -s -X POST "$API_URL/api/v1/auth/token" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "username=test@example.com&password=testpass123&grant_type=password")

if echo "$TOKEN_RESPONSE" | jq -e '.access_token' >/dev/null; then
    ACCESS_TOKEN=$(echo "$TOKEN_RESPONSE" | jq -r '.access_token')
    echo -e "${GREEN}Authentication Successful${NC}"
else
    echo -e "${RED}Authentication Failed${NC}"
    echo "Error: $(echo "$TOKEN_RESPONSE" | jq -r '.detail // .message // .')"
fi

# Test 6: Get Recommendations
echo -e "\n${CYAN}Testing Recommendations Endpoint...${NC}"
echo "Sending recommendations request to $API_URL/api/v1/recommendations"
if [ -n "$ACCESS_TOKEN" ]; then
    REC_RESPONSE=$(curl -s -X GET "$API_URL/api/v1/recommendations" \
        -H "Authorization: Bearer $ACCESS_TOKEN" \
        -H "Content-Type: application/json")

    if echo "$REC_RESPONSE" | jq -e '.recommendations' >/dev/null; then
    echo -e "${GREEN}Recommendations Retrieved Successfully${NC}"
        echo "Number of recommendations: $(echo "$REC_RESPONSE" | jq '.recommendations | length')"
else
    echo -e "${RED}Failed to Get Recommendations${NC}"
        echo "Error: $(echo "$REC_RESPONSE" | jq -r '.detail // .message // .')"
    fi
else
    echo -e "${RED}Skipping recommendations test - no access token available${NC}"
fi

# Test 7: Redis Caching
echo -e "\n${CYAN}Testing Redis Caching...${NC}"
echo "Testing caching performance..."

# Using time command instead of bc for timing
time1=$(date +%s)
curl -s "$API_URL/api/v1/recommendations" -H "Authorization: Bearer $ACCESS_TOKEN" > /dev/null
time2=$(date +%s)
FIRST_REQUEST_TIME=$((time2 - time1))

time1=$(date +%s)
curl -s "$API_URL/api/v1/recommendations" -H "Authorization: Bearer $ACCESS_TOKEN" > /dev/null
time2=$(date +%s)
SECOND_REQUEST_TIME=$((time2 - time1))

echo "First request time: ${FIRST_REQUEST_TIME}s"
echo "Second request time: ${SECOND_REQUEST_TIME}s"

if [ $SECOND_REQUEST_TIME -lt $FIRST_REQUEST_TIME ]; then
    echo -e "${GREEN}Redis Caching Working (Second request faster)${NC}"
else
    echo -e "${RED}Redis Caching May Not Be Working Optimally${NC}"
fi

echo -e "\n${CYAN}Integration Tests Completed${NC}" 