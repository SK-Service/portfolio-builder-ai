# Test script for BFF endpoints
# Replace with your actual key from .env
# DO NOT COMMIT YOUR KEYS TO SOURCE CONTROL - have $APP_KEY set in your environment instead

param(
    [Parameter(Mandatory=$true)]
    [string]$APP_KEY
)

$headers = @{
    'X-Portfolio-App-Key' = $APP_KEY
    'X-Requested-With' = 'XMLHttpRequest'
}

Write-Host "Testing BFF API Endpoints..." -ForegroundColor Green

# Test Health (no auth needed)
Write-Host "`nTesting /api/health..." -ForegroundColor Yellow
Invoke-RestMethod -Uri "http://localhost:5001/api/health" -Method GET

# Test Config
Write-Host "`nTesting /api/config..." -ForegroundColor Yellow
Invoke-RestMethod -Uri "http://localhost:5001/api/config" -Method GET -Headers $headers

# Test Rate Limit Check
Write-Host "`nTesting /api/rate-limit/check..." -ForegroundColor Yellow
$rateLimitBody = @{ fingerprint = "test-123" } | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:5001/api/rate-limit/check" -Method POST -Headers $headers -ContentType "application/json" -Body $rateLimitBody

# Test Portfolio Generate
Write-Host "`nTesting /api/portfolio/generate..." -ForegroundColor Yellow
$portfolioBody = @{
    riskTolerance = "Medium"
    investmentHorizonYears = 10
    country = "USA"
    investmentAmount = 10000
    currency = "USD"
} | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:5001/api/portfolio/generate" -Method POST -Headers $headers -ContentType "application/json" -Body $portfolioBody

Write-Host "`nAll tests completed!" -ForegroundColor Green