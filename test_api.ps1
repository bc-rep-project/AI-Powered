# Test script for AI Content Recommendation API
$baseUrl = "https://ai-powered-production.up.railway.app"
$testEmail = "test@example.com"
$testPassword = "password"
$testName = "Test User"

Write-Host "`nTesting Health Check Endpoint..."
Write-Host "Testing endpoint: GET $baseUrl/health"
$healthResponse = Invoke-RestMethod -Uri "$baseUrl/health" -Method Get
Write-Host "Success! Response:"
$healthResponse | ConvertTo-Json

Write-Host "`nTesting Root Endpoint..."
Write-Host "Testing endpoint: GET $baseUrl/"
$rootResponse = Invoke-RestMethod -Uri "$baseUrl/" -Method Get
Write-Host "Success! Response:"
$rootResponse | ConvertTo-Json

Write-Host "`nTesting User Registration..."
Write-Host "Testing endpoint: POST $baseUrl/api/v1/auth/register"
$registerBody = @{
    email = $testEmail
    password = $testPassword
    name = $testName
} | ConvertTo-Json

try {
    $registerResponse = Invoke-RestMethod -Uri "$baseUrl/api/v1/auth/register" -Method Post -Body $registerBody -ContentType "application/json"
    Write-Host "Success! Response:"
    $registerResponse | ConvertTo-Json
} catch {
    Write-Host "Note: Registration failed (user might already exist). Error:"
    Write-Host $_.Exception.Response.StatusCode.Value__
    Write-Host $_.Exception.Response.StatusDescription
    $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
    Write-Host $reader.ReadToEnd()
}

Write-Host "`nTesting Authentication..."
Write-Host "Testing endpoint: POST $baseUrl/token"
$tokenBody = "username=$testEmail&password=$testPassword&grant_type=password"
try {
    $tokenResponse = Invoke-RestMethod -Uri "$baseUrl/token" -Method Post -Body $tokenBody -ContentType "application/x-www-form-urlencoded"
    Write-Host "Success! Response:"
    $tokenResponse | ConvertTo-Json
    $token = $tokenResponse.access_token
} catch {
    Write-Host "Error occurred!"
    Write-Host "Status Code:" $_.Exception.Response.StatusCode.Value__
    Write-Host "Status Description:" $_.Exception.Response.StatusDescription
    $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
    Write-Host "Error Details:" $reader.ReadToEnd()
    exit
}

Write-Host "`nTesting Protected Endpoints..."
Write-Host "Using token: $token"

Write-Host "Testing endpoint: GET $baseUrl/api/v1/recommendations"
$headers = @{
    "Authorization" = "Bearer $token"
}
try {
    $recommendationsResponse = Invoke-RestMethod -Uri "$baseUrl/api/v1/recommendations" -Method Get -Headers $headers
    Write-Host "Success! Response:"
    $recommendationsResponse | ConvertTo-Json -Depth 4
} catch {
    Write-Host "Error occurred!"
    Write-Host "Status Code:" $_.Exception.Response.StatusCode.Value__
    Write-Host "Status Description:" $_.Exception.Response.StatusDescription
    $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
    Write-Host "Error Details:" $reader.ReadToEnd()
}

Write-Host "`nTesting CORS Configuration..."
Write-Host "Testing endpoint: OPTIONS $baseUrl/token"
try {
    $corsResponse = Invoke-RestMethod -Uri "$baseUrl/token" -Method Options
    Write-Host "Success! Response:"
    $corsResponse | ConvertTo-Json
} catch {
    Write-Host "Error occurred!"
    Write-Host "Status Code:" $_.Exception.Response.StatusCode.Value__
    Write-Host "Status Description:" $_.Exception.Response.StatusDescription
    $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
    Write-Host "Error Details:" $reader.ReadToEnd()
}

Write-Host "OK"