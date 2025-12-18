# Test-StockSymbols.ps1
# PowerShell script to batch validate stock symbols using Twelve Data /stocks API
# Compatible with Windows 10 PowerShell

param(
    [Parameter(Mandatory=$true)]
    [string]$InputFile,
    
    [string]$ApiKey = "demo",
    
    [int]$BatchSize = 20  # Number of stocks per batch request (adjust based on API limits)
)

# Log files
$timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$logFileDetails = "twelvedata_symbol_test_details_iop_$timestamp.log"
$logFileSummary = "twelvedata_symbol_test_summary_info_$timestamp.log"
$logFileUnavailable = "twelvedata_symbol_test_stocks_unavailable_$timestamp.log"

# Function to write to detail log file
function Write-DetailLog {
    param([string]$Message)
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "[$ts] $Message" | Out-File -FilePath $logFileDetails -Append -Encoding UTF8
}

# Function to write to summary log file
function Write-SummaryLog {
    param([string]$Message)
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "[$ts] $Message" | Out-File -FilePath $logFileSummary -Append -Encoding UTF8
}

# Function to write to unavailable stocks log file (no timestamp, raw CSV line)
function Write-UnavailableLog {
    param([string]$Message)
    $Message | Out-File -FilePath $logFileUnavailable -Append -Encoding UTF8
}

# Check if input file exists
if (-not (Test-Path $InputFile)) {
    Write-DetailLog "ERROR: Input file not found: $InputFile"
    Write-SummaryLog "ERROR: Input file not found: $InputFile"
    exit 1
}

# Read and parse the stock list
$stocks = @()
$lines = Get-Content $InputFile

foreach ($line in $lines) {
    $lineTrimmed = $line.Trim()
    if ([string]::IsNullOrEmpty($lineTrimmed)) { continue }
    
    $parts = $lineTrimmed -split ","
    
    # Format with exchange: Region,Sector,Symbol,Name,Size,Exchange (6 columns)
    # Format without exchange: Region,Sector,Symbol,Name,Size (5 columns)
    
    if ($parts.Count -ge 5) {
        $symbol = $parts[2].Trim()
        $exchange = if ($parts.Count -ge 6 -and -not [string]::IsNullOrEmpty($parts[5].Trim())) { $parts[5].Trim() } else { $null }
        
        $stock = @{
            Region = $parts[0].Trim()
            Sector = $parts[1].Trim()
            Symbol = $symbol
            Name = $parts[3].Trim()
            Size = $parts[4].Trim()
            Exchange = $exchange
            RawLine = $line  # Keep original line for unavailable log
        }
        $stocks += $stock
    }
}

# Tracking variables for summary
$totalStocks = $stocks.Count
$availableStocks = @()
$unavailableStocks = @()

# Write initial summary info
Write-SummaryLog "=========================================="
Write-SummaryLog "TWELVE DATA SYMBOL VALIDATION - SUMMARY"
Write-SummaryLog "=========================================="
Write-SummaryLog ""
Write-SummaryLog "Input File: $InputFile"
Write-SummaryLog "Total Stocks Loaded: $totalStocks"
Write-SummaryLog "Batch Size: $BatchSize"
Write-SummaryLog ""

# Write detail log header
Write-DetailLog "=========================================="
Write-DetailLog "TWELVE DATA SYMBOL VALIDATION - DETAILED LOG"
Write-DetailLog "=========================================="
Write-DetailLog ""
Write-DetailLog "API Endpoint: /stocks (for exact symbol/exchange validation)"
Write-DetailLog "Input File: $InputFile"
Write-DetailLog "Total Stocks Loaded: $totalStocks"
Write-DetailLog "Batch Size: $BatchSize"
Write-DetailLog ""

# Split stocks into batches
$batches = @()
for ($i = 0; $i -lt $stocks.Count; $i += $BatchSize) {
    $end = [Math]::Min($i + $BatchSize - 1, $stocks.Count - 1)
    $batches += ,($stocks[$i..$end])
}

Write-DetailLog "Number of Batches: $($batches.Count)"
Write-SummaryLog "Number of Batches: $($batches.Count)"
Write-DetailLog ""

# API endpoint and headers
$uri = "https://api.twelvedata.com/batch"
$headers = @{
    "Content-Type" = "application/json"
    "Authorization" = "apikey $ApiKey"
}

# Process each batch
$batchNum = 0
foreach ($batch in $batches) {
    $batchNum++
    
    Write-DetailLog "=========================================="
    Write-DetailLog "BATCH $batchNum of $($batches.Count)"
    Write-DetailLog "=========================================="
    Write-DetailLog ""
    
    # Build the JSON body manually to avoid Unicode escaping
    # Also create a mapping of request IDs to stock info
    $jsonParts = @()
    $reqNum = 0
    $requestMapping = @{}  # Maps req_N to stock info
    
    foreach ($stock in $batch) {
        $reqNum++
        $requestId = "req_$reqNum"
        
        # Store mapping
        $requestMapping[$requestId] = $stock
        
        # Build URL using /stocks endpoint with or without exchange
        if ($stock.Exchange) {
            $url = "/stocks?symbol=$($stock.Symbol)&exchange=$($stock.Exchange)&apikey=$ApiKey"
        } else {
            $url = "/stocks?symbol=$($stock.Symbol)&apikey=$ApiKey"
        }
        
        $jsonParts += """$requestId"": {""url"": ""$url""}"
    }
    
    $jsonBody = "{`n    " + ($jsonParts -join ",`n    ") + "`n}"
    
    # Log request details
    Write-DetailLog "SECTION A: REQUEST DETAILS"
    Write-DetailLog "--------------------------"
    Write-DetailLog "Stocks in this batch:"
    foreach ($stock in $batch) {
        $exchInfo = if ($stock.Exchange) { " (Exchange: $($stock.Exchange))" } else { " (No Exchange)" }
        Write-DetailLog "  - $($stock.Symbol)$exchInfo"
    }
    Write-DetailLog ""
    Write-DetailLog "Request Body (JSON):"
    Write-DetailLog $jsonBody
    Write-DetailLog ""
    
    # Log curl equivalent (with redacted API key)
    $jsonBodyRedacted = $jsonBody -replace "apikey=$ApiKey", "apikey=YOUR_API_KEY"
    $curlCommand = "curl --location '$uri' --header 'Content-Type: application/json' --header 'Authorization: apikey YOUR_API_KEY' --data '$($jsonBodyRedacted -replace "`r`n", " " -replace "`n", " ")'"
    Write-DetailLog "Equivalent curl command:"
    Write-DetailLog $curlCommand
    Write-DetailLog ""
    
    # Make the API request
    Write-DetailLog "SECTION B: RAW API RESPONSE"
    Write-DetailLog "--------------------------"
    
    try {
        $response = Invoke-RestMethod -Uri $uri -Method Post -Headers $headers -Body $jsonBody
        
        Write-DetailLog "Response Status: Success (HTTP 200)"
        Write-DetailLog ""
        Write-DetailLog "Raw Response:"
        Write-DetailLog ($response | ConvertTo-Json -Depth 10)
        
        # Process each request's response to determine availability
        # /stocks endpoint returns: {"data": [...], "status": "ok"}
        # Empty data array means symbol/exchange combination doesn't exist
        foreach ($requestId in $requestMapping.Keys) {
            $stock = $requestMapping[$requestId]
            $reqResponse = $response.data.$requestId
            
            $isAvailable = $false
            
            if ($reqResponse.status -eq "success") {
                $stockData = $reqResponse.response.data
                
                # Check if data array is not empty
                if ($stockData -and $stockData.Count -gt 0) {
                    $isAvailable = $true
                }
            }
            
            if ($isAvailable) {
                $availableStocks += $stock
            } else {
                $unavailableStocks += $stock
            }
        }
        
    }
    catch {
        Write-DetailLog ""
        Write-DetailLog "SECTION C: ERRORS"
        Write-DetailLog "-----------------"
        Write-DetailLog "Exception Type: $($_.Exception.GetType().FullName)"
        Write-DetailLog "Error Message: $($_.Exception.Message)"
        
        if ($_.Exception.Response) {
            $statusCode = [int]$_.Exception.Response.StatusCode
            $statusDesc = $_.Exception.Response.StatusDescription
            Write-DetailLog "HTTP Status Code: $statusCode"
            Write-DetailLog "HTTP Status Description: $statusDesc"
        }
        
        if ($_.ErrorDetails.Message) {
            Write-DetailLog ""
            Write-DetailLog "API Error Details:"
            Write-DetailLog $_.ErrorDetails.Message
        }
        
        # Try to get the response body even on error
        try {
            $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
            $reader.BaseStream.Position = 0
            $responseBody = $reader.ReadToEnd()
            Write-DetailLog ""
            Write-DetailLog "Raw Error Response Body:"
            Write-DetailLog $responseBody
        }
        catch {
            Write-DetailLog "Could not read error response body"
        }
        
        # On batch error, mark all stocks in this batch as unavailable
        foreach ($stock in $batch) {
            $unavailableStocks += $stock
        }
    }
    
    Write-DetailLog ""
    
    # Add delay between batches to avoid rate limiting
    if ($batchNum -lt $batches.Count) {
        Start-Sleep -Seconds 2
    }
}

# Write final summary
Write-SummaryLog ""
Write-SummaryLog "=========================================="
Write-SummaryLog "FINAL RESULTS"
Write-SummaryLog "=========================================="
Write-SummaryLog ""
Write-SummaryLog "Total Stocks Tested: $totalStocks"
Write-SummaryLog "Total Stocks Available on Twelvedata: $($availableStocks.Count)"
Write-SummaryLog "Total Stocks NOT Available on Twelvedata: $($unavailableStocks.Count)"
Write-SummaryLog ""
Write-SummaryLog "=========================================="
Write-SummaryLog "END OF SUMMARY"
Write-SummaryLog "=========================================="

# Write unavailable stocks to separate log file
if ($unavailableStocks.Count -gt 0) {
    Write-UnavailableLog "# Stocks not available on Twelvedata (empty data[] returned from /stocks endpoint)"
    Write-UnavailableLog "# Generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
    Write-UnavailableLog "# Format: Region,Sector,Symbol,Name,Size,Exchange"
    Write-UnavailableLog ""
    
    foreach ($stock in $unavailableStocks) {
        Write-UnavailableLog $stock.RawLine
    }
} else {
    Write-UnavailableLog "# All stocks are available on Twelvedata"
    Write-UnavailableLog "# Generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
}

Write-DetailLog "=========================================="
Write-DetailLog "END OF DETAILED LOG"
Write-DetailLog "=========================================="