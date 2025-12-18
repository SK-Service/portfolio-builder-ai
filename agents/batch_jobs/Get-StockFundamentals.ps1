# Get-StockFundamentals.ps1
# PowerShell script to retrieve stock fundamentals from Twelve Data API
# Compatible with Windows 10 PowerShell

param(
    [string]$ApiKey = "demo"  # Replace with your actual API key
)

# Log file for debugging
$logFile = "twelvedata_debug_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"

# Function to write to log file
function Write-Log {
    param([string]$Message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "[$timestamp] $Message" | Out-File -FilePath $logFile -Append -Encoding UTF8
}

# Define the stocks to query
$stocks = @(
    @{ Symbol = "AC"; Exchange = "XPAR" },
    @{ Symbol = "AHT"; Exchange = "XLON" },
    @{ Symbol = "POWERGRID"; Exchange = "XNSE" },
    @{ Symbol = "GODREJPROP"; Exchange = "XNSE" }
)

# Build the JSON body manually to avoid Unicode escaping of ampersands
$jsonParts = @()
foreach ($stock in $stocks) {
    $requestId = "req_$($stock.Symbol)"
    $url = "/statistics?symbol=$($stock.Symbol)&exchange=$($stock.Exchange)&apikey=$ApiKey"
    $jsonParts += """$requestId"": {""url"": ""$url""}"
}
$jsonBody = "{`n    " + ($jsonParts -join ",`n    ") + "`n}"

# API endpoint and headers
$uri = "https://api.twelvedata.com/batch"
$headers = @{
    "Content-Type" = "application/json"
    "Authorization" = "apikey $ApiKey"
}

# Start logging
Write-Log "=========================================="
Write-Log "TWELVE DATA API DEBUG LOG"
Write-Log "=========================================="
Write-Log ""

# Log the exact request details
Write-Log "SECTION A: REQUEST DETAILS"
Write-Log "--------------------------"
Write-Log "Endpoint: $uri"
Write-Log "Method: POST"
Write-Log ""
Write-Log "Headers:"
foreach ($key in $headers.Keys) {
    if ($key -eq "Authorization") {
        Write-Log "  $key`: apikey [REDACTED]"
    } else {
        Write-Log "  $key`: $($headers[$key])"
    }
}
Write-Log ""
Write-Log "Request Body (JSON):"
Write-Log $jsonBody
Write-Log ""

# Also log the equivalent curl command for sharing with Twelve Data support
# Redact API key in curl command
$jsonBodyRedacted = $jsonBody -replace "apikey=$ApiKey", "apikey=YOUR_API_KEY"
$curlCommand = @"
curl --location '$uri' \
--header 'Content-Type: application/json' \
--header 'Authorization: apikey YOUR_API_KEY' \
--data '$($jsonBodyRedacted -replace "`r`n", " " -replace "`n", " ")'
"@

Write-Log "Equivalent curl command:"
Write-Log $curlCommand
Write-Log ""

# Make the API request
Write-Log "=========================================="
Write-Log "SECTION B: RAW API RESPONSE"
Write-Log "=========================================="
Write-Log ""

try {
    $response = Invoke-RestMethod -Uri $uri -Method Post -Headers $headers -Body $jsonBody
    
    Write-Log "Response Status: Success (HTTP 200)"
    Write-Log ""
    Write-Log "Raw Response:"
    Write-Log ($response | ConvertTo-Json -Depth 10)
    
}
catch {
    Write-Log "=========================================="
    Write-Log "SECTION C: ERRORS"
    Write-Log "=========================================="
    Write-Log ""
    Write-Log "Exception Type: $($_.Exception.GetType().FullName)"
    Write-Log "Error Message: $($_.Exception.Message)"
    Write-Log ""
    
    if ($_.Exception.Response) {
        $statusCode = [int]$_.Exception.Response.StatusCode
        $statusDesc = $_.Exception.Response.StatusDescription
        Write-Log "HTTP Status Code: $statusCode"
        Write-Log "HTTP Status Description: $statusDesc"
    }
    
    if ($_.ErrorDetails.Message) {
        Write-Log ""
        Write-Log "API Error Details:"
        Write-Log $_.ErrorDetails.Message
    }
    
    # Try to get the response body even on error
    try {
        $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
        $reader.BaseStream.Position = 0
        $responseBody = $reader.ReadToEnd()
        Write-Log ""
        Write-Log "Raw Error Response Body:"
        Write-Log $responseBody
    }
    catch {
        Write-Log "Could not read error response body"
    }
}

Write-Log ""
Write-Log "=========================================="
Write-Log "END OF LOG"
Write-Log "=========================================="