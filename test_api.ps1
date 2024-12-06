# Test script for AI Content Recommendation API
$baseUrl = "https://ai-powered-production.up.railway.app"
$testEmail = "test@example.com"
$testPassword = "password"
$testName = "Test User"

function Write-TestHeader {
    param (
        [string]$message
    )
    Write-Host "`n$message" -ForegroundColor Cyan
}

function Write-Success {
    param (
        [string]$message,
        $response
    )
    Write-Host "Success! " -ForegroundColor Green -NoNewline
    Write-Host $message
    if ($response) {
        $response | ConvertTo-Json -Depth 10
    }
}

function Write-Error {
    param (
        [string]$message,
        $error
    )
    Write-Host "Error! " -ForegroundColor Red -NoNewline
    Write-Host $message
    if ($error) {
        Write-Host "Status Code: $($error.Exception.Response.StatusCode.Value__)"
        Write-Host "Status Description: $($error.Exception.Response.StatusDescription)"
        try {
            $reader = New-Object System.IO.StreamReader($error.Exception.Response.GetResponseStream())
            $errorDetails = $reader.ReadToEnd()
            Write-Host "Error Details: $errorDetails"
        } catch {
            Write-Host "Could not read error details"
        }
    }
}

# Test Health Check
Write-TestHeader "Testing Health Check Endpoint..."
Write-Host "Testing endpoint: GET $baseUrl/health"
try {
    $healthResponse = Invoke-RestMethod -Uri "$baseUrl/health" -Method Get
    Write-Success "Health check successful" $healthResponse
} catch {
    Write-Error "Health check failed" $_
}

# Test Root Endpoint
Write-TestHeader "Testing Root Endpoint..."
Write-Host "Testing endpoint: GET $baseUrl/"
try {
    $rootResponse = Invoke-RestMethod -Uri "$baseUrl/" -Method Get
    Write-Success "Root endpoint successful" $rootResponse
} catch {
    Write-Error "Root endpoint failed" $_
}

# Test User Registration
Write-TestHeader "Testing User Registration..."
Write-Host "Testing endpoint: POST $baseUrl/api/v1/auth/register"
$registerBody = @{
    email = $testEmail
    password = $testPassword
    name = $testName
} | ConvertTo-Json

$headers = @{
    "Content-Type" = "application/json"
    "Accept" = "application/json"
}

try {
    $registerResponse = Invoke-RestMethod -Uri "$baseUrl/api/v1/auth/register" -Method Post -Body $registerBody -Headers $headers
    Write-Success "Registration successful" $registerResponse
} catch {
    if ($_.Exception.Response.StatusCode.Value__ -eq 400) {
        Write-Host "Note: User already exists" -ForegroundColor Yellow
    } else {
        Write-Error "Registration failed" $_
    }
}

# Test Authentication
Write-TestHeader "Testing Authentication..."
Write-Host "Testing endpoint: POST $baseUrl/token"

$tokenBody = "username=$testEmail&password=$testPassword&grant_type=password"
$tokenHeaders = @{
    "Content-Type" = "application/x-www-form-urlencoded"
    "Accept" = "application/json"
}

try {
    $tokenResponse = Invoke-RestMethod -Uri "$baseUrl/token" -Method Post -Body $tokenBody -Headers $tokenHeaders
    Write-Success "Authentication successful" $tokenResponse
    $token = $tokenResponse.access_token
} catch {
    Write-Error "Authentication failed" $_
    exit
}

# Test Protected Endpoints
Write-TestHeader "Testing Protected Endpoints..."
Write-Host "Using token: $token"

Write-Host "`nTesting endpoint: GET $baseUrl/api/v1/recommendations"
$authHeaders = @{
    "Authorization" = "Bearer $token"
    "Accept" = "application/json"
}

try {
    $recommendationsResponse = Invoke-RestMethod -Uri "$baseUrl/api/v1/recommendations" -Method Get -Headers $authHeaders
    Write-Success "Recommendations retrieved successfully" $recommendationsResponse
} catch {
    Write-Error "Failed to get recommendations" $_
}

# Test CORS
Write-TestHeader "Testing CORS Configuration..."
Write-Host "Testing endpoint: OPTIONS $baseUrl/token"
try {
    $corsHeaders = @{
        "Origin" = "https://ai-powered-content-recommendation-frontend.vercel.app"
        "Access-Control-Request-Method" = "POST"
        "Access-Control-Request-Headers" = "content-type,authorization"
    }
    $corsResponse = Invoke-WebRequest -Uri "$baseUrl/token" -Method Options -Headers $corsHeaders
    Write-Success "CORS preflight successful" @{
        "Access-Control-Allow-Origin" = $corsResponse.Headers["Access-Control-Allow-Origin"]
        "Access-Control-Allow-Methods" = $corsResponse.Headers["Access-Control-Allow-Methods"]
        "Access-Control-Allow-Headers" = $corsResponse.Headers["Access-Control-Allow-Headers"]
    }
} catch {
    Write-Error "CORS preflight failed" $_
}

Write-Host "`nTests completed!" -ForegroundColor Green