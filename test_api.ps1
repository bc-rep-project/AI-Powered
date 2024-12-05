# Test API endpoints for AI Content Recommendation System
$baseUrl = "https://ai-powered-production.up.railway.app"
$frontendUrl = "https://ai-powered-content-recommendation-frontend.vercel.app"

# Function to make API requests with error handling
function Invoke-APIRequest {
    param (
        [string]$Uri,
        [string]$Method = "GET",
        [hashtable]$Headers = @{},
        [string]$Body = "",
        [string]$ContentType = "application/json"
    )
    
    try {
        $params = @{
            Uri = $Uri
            Method = $Method
            Headers = $Headers
        }
        
        if ($Body -ne "") {
            $params.Add("Body", $Body)
            $params.Add("ContentType", $ContentType)
        }
        
        Write-Host "Testing endpoint: $Method $Uri" -ForegroundColor Cyan
        if ($Body -ne "") {
            Write-Host "Request Body: $Body" -ForegroundColor Cyan
        }
        $response = Invoke-RestMethod @params
        Write-Host "Success! Response:" -ForegroundColor Green
        $response | ConvertTo-Json -Depth 10
        return $response
    }
    catch {
        Write-Host "Error occurred!" -ForegroundColor Red
        Write-Host "Status Code: $($_.Exception.Response.StatusCode.value__)" -ForegroundColor Red
        Write-Host "Status Description: $($_.Exception.Response.StatusDescription)" -ForegroundColor Red
        
        try {
            $errorResponse = $_.ErrorDetails.Message | ConvertFrom-Json
            Write-Host "Error Details: $($errorResponse | ConvertTo-Json)" -ForegroundColor Red
        }
        catch {
            Write-Host "Raw Error: $_" -ForegroundColor Red
        }
        return $null
    }
}

# Test Health Check
Write-Host "`nTesting Health Check Endpoint..." -ForegroundColor Yellow
Invoke-APIRequest -Uri "$baseUrl/health"

# Test Root Endpoint
Write-Host "`nTesting Root Endpoint..." -ForegroundColor Yellow
Invoke-APIRequest -Uri "$baseUrl/"

# Test Authentication
Write-Host "`nTesting Authentication..." -ForegroundColor Yellow
$formData = @{
    username = "test@example.com"
    password = "password"
    grant_type = "password"
}
$authBody = ($formData.GetEnumerator() | ForEach-Object { "$($_.Key)=$($_.Value)" }) -join "&"
$token = Invoke-APIRequest -Uri "$baseUrl/token" -Method "POST" -Body $authBody -ContentType "application/x-www-form-urlencoded"

if ($token -and $token.access_token) {
    $authHeader = @{
        "Authorization" = "Bearer $($token.access_token)"
    }
    
    # Test Protected Endpoints
    Write-Host "`nTesting Protected Endpoints..." -ForegroundColor Yellow
    Write-Host "Using token: $($token.access_token)" -ForegroundColor Cyan
    Invoke-APIRequest -Uri "$baseUrl/api/v1/recommendations" -Headers $authHeader -Method "GET"
}

# Test CORS
Write-Host "`nTesting CORS Configuration..." -ForegroundColor Yellow
$corsHeaders = @{
    "Origin" = $frontendUrl
    "Access-Control-Request-Method" = "POST"
    "Access-Control-Request-Headers" = "content-type,authorization"
}
Invoke-APIRequest -Uri "$baseUrl/token" -Method "OPTIONS" -Headers $corsHeaders