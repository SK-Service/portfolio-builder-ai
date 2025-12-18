# TestStatisticsAPI.ps1
# PowerShell script to test Twelve Data /statistics API via /batch endpoint
# Creates detailed logs for debugging API issues

param(
    [Parameter(Mandatory=$true)]
    [string]$InputFile,
    
    [string]$ApiKey = "demo",
    
    [int]$BatchSize = 6,
    
    [int]$CreditPerCall = 50,
    
    [int]$CreditLimitPerMinute = 610
)

# Log files with timestamp
$timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$logFileDetails = "twelvedata_statistics_iop_$timestamp.log"
$logFileSummary = "twelvedata_statistics_summary_$timestamp.log"
$logFileNoData = "twelvedata_statistics_nodata_$timestamp.log"

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

# Function to write to no-data stocks log file
function Write-NoDataLog {
    param([string]$Message)
    $Message | Out-File -FilePath $logFileNoData -Append -Encoding UTF8
}

# Check if input file exists
if (-not (Test-Path $InputFile)) {
    Write-Host "ERROR: Input file not found: $InputFile" -ForegroundColor Red
    exit 1
}

# Read and parse the stock list
$stocks = @()
$lines = Get-Content $InputFile

$isFirstLine = $true
foreach ($line in $lines) {
    # Skip header line
    if ($isFirstLine) {
        $isFirstLine = $false
        if ($line -match "^country,sector,symbol") {
            continue
        }
    }
    
    $lineTrimmed = $line.Trim()
    if ([string]::IsNullOrEmpty($lineTrimmed)) { continue }
    
    $parts = $lineTrimmed -split ","
    
    # Format: country,sector,symbol,name,market_cap_tier,exchange (6 columns)
    # Or: country,sector,symbol,name,market_cap_tier (5 columns for USA)
    
    if ($parts.Count -ge 5) {
        $stock = @{
            Country = $parts[0].Trim()
            Sector = $parts[1].Trim()
            Symbol = $parts[2].Trim()
            Name = $parts[3].Trim()
            MarketCapTier = $parts[4].Trim()
            Exchange = if ($parts.Count -ge 6 -and -not [string]::IsNullOrEmpty($parts[5].Trim())) { $parts[5].Trim() } else { $null }
            RawLine = $line
        }
        $stocks += $stock
    }
}

# Tracking variables
$totalStocks = $stocks.Count
$successStocks = @()
$noDataStocks = @()
$errorStocks = @()

# Write initial headers
Write-SummaryLog "=========================================="
Write-SummaryLog "TWELVE DATA STATISTICS API TEST - SUMMARY"
Write-SummaryLog "=========================================="
Write-SummaryLog ""
Write-SummaryLog "Input File: $InputFile"
Write-SummaryLog "Total Stocks: $totalStocks"
Write-SummaryLog "Batch Size: $BatchSize"
Write-SummaryLog "Credit per call: $CreditPerCall"
Write-SummaryLog "Credit limit per minute: $CreditLimitPerMinute"
Write-SummaryLog "API Key: $($ApiKey.Substring(0, [Math]::Min(4, $ApiKey.Length)))..."
Write-SummaryLog ""

Write-DetailLog "=========================================="
Write-DetailLog "TWELVE DATA STATISTICS API TEST - DETAILED LOG"
Write-DetailLog "=========================================="
Write-DetailLog ""
Write-DetailLog "Purpose: Debug /statistics endpoint via /batch API"
Write-DetailLog "Input File: $InputFile"
Write-DetailLog "Total Stocks: $totalStocks"
Write-DetailLog "Batch Size: $BatchSize"
Write-DetailLog ""

Write-NoDataLog "# Stocks with no statistics data returned"
Write-NoDataLog "# Generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
Write-NoDataLog "# Format: country,sector,symbol,name,market_cap_tier,exchange"
Write-NoDataLog ""

# Split stocks into batches
$batches = @()
for ($i = 0; $i -lt $stocks.Count; $i += $BatchSize) {
    $end = [Math]::Min($i + $BatchSize - 1, $stocks.Count - 1)
    $batches += ,($stocks[$i..$end])
}

Write-DetailLog "Number of Batches: $($batches.Count)"
Write-SummaryLog "Number of Batches: $($batches.Count)"
Write-DetailLog ""

Write-Host "=========================================="
Write-Host "TWELVE DATA STATISTICS API TEST"
Write-Host "=========================================="
Write-Host "Input File: $InputFile"
Write-Host "Total Stocks: $totalStocks"
Write-Host "Batches: $($batches.Count)"
Write-Host ""

# API endpoint
$batchUri = "https://api.twelvedata.com/batch"
$headers = @{
    "Content-Type" = "application/json"
    "Authorization" = "apikey $ApiKey"
}

# Process each batch
$batchNum = 0
$creditsUsedThisMinute = 0
$minuteStartTime = Get-Date

foreach ($batch in $batches) {
    $batchNum++
    
    # Calculate credits needed for this batch
    $creditsNeeded = $batch.Count * $CreditPerCall
    
    # Check if we need to wait for rate limit reset
    if (($creditsUsedThisMinute + $creditsNeeded) -gt $CreditLimitPerMinute) {
        $elapsed = (Get-Date) - $minuteStartTime
        $secondsToWait = [Math]::Max(0, 60 - $elapsed.TotalSeconds)
        
        if ($secondsToWait -gt 0) {
            Write-Host ""
            Write-Host "  Rate limit approaching! Credits used: $creditsUsedThisMinute / $CreditLimitPerMinute" -ForegroundColor Yellow
            Write-Host "  Waiting $([Math]::Ceiling($secondsToWait)) seconds for rate limit to reset..." -ForegroundColor Yellow
            Write-DetailLog "Rate limit pause: Credits used $creditsUsedThisMinute, waiting $([Math]::Ceiling($secondsToWait)) seconds"
            Start-Sleep -Seconds ([Math]::Ceiling($secondsToWait) + 1)
        }
        
        # Reset credit counter after waiting
        $creditsUsedThisMinute = 0
        $minuteStartTime = Get-Date
    }
    
    Write-Host "Processing Batch $batchNum/$($batches.Count)... (Credits this minute: $creditsUsedThisMinute + $creditsNeeded = $($creditsUsedThisMinute + $creditsNeeded))" -ForegroundColor Cyan
    
    Write-DetailLog "=========================================="
    Write-DetailLog "BATCH $batchNum of $($batches.Count)"
    Write-DetailLog "=========================================="
    Write-DetailLog ""
    
    # Build the JSON body for batch request
    $jsonParts = @()
    $reqNum = 0
    $requestMapping = @{}
    
    foreach ($stock in $batch) {
        $reqNum++
        $requestId = "req_$reqNum"
        $requestMapping[$requestId] = $stock
        
        # Build URL for /statistics endpoint
        if ($stock.Exchange) {
            $url = "/statistics?symbol=$($stock.Symbol)&mic_code=$($stock.Exchange)&apikey=$ApiKey"
        } else {
            $url = "/statistics?symbol=$($stock.Symbol)&apikey=$ApiKey"
        }
        
        $jsonParts += """$requestId"": {""url"": ""$url""}"
    }
    
    $jsonBody = "{`n    " + ($jsonParts -join ",`n    ") + "`n}"
    
    # Log request details
    Write-DetailLog "SECTION A: REQUEST DETAILS"
    Write-DetailLog "--------------------------"
    Write-DetailLog "Stocks in this batch:"
    foreach ($stock in $batch) {
        $exchInfo = if ($stock.Exchange) { " (Exchange: $($stock.Exchange))" } else { " (No Exchange - USA)" }
        Write-DetailLog "  - $($stock.Symbol)$exchInfo - $($stock.Name)"
    }
    Write-DetailLog ""
    Write-DetailLog "Request URL: $batchUri"
    Write-DetailLog ""
    Write-DetailLog "Request Headers:"
    Write-DetailLog "  Content-Type: application/json"
    Write-DetailLog "  Authorization: apikey $($ApiKey.Substring(0, [Math]::Min(4, $ApiKey.Length)))...REDACTED"
    Write-DetailLog ""
    Write-DetailLog "Request Body (JSON):"
    Write-DetailLog $jsonBody
    Write-DetailLog ""
    
    # Log curl equivalent (with redacted API key)
    $jsonBodyForCurl = $jsonBody -replace [regex]::Escape($ApiKey), "YOUR_API_KEY"
    $curlCommand = "curl --location '$batchUri' --header 'Content-Type: application/json' --header 'Authorization: apikey YOUR_API_KEY' --data '$($jsonBodyForCurl -replace "`r`n", " " -replace "`n", " ")'"
    Write-DetailLog "Equivalent curl command:"
    Write-DetailLog $curlCommand
    Write-DetailLog ""
    
    # Make the API request
    Write-DetailLog "SECTION B: RAW API RESPONSE"
    Write-DetailLog "--------------------------"
    
    try {
        $rawResponse = Invoke-RestMethod -Uri $batchUri -Method Post -Headers $headers -Body $jsonBody
        
        # Handle case where response is returned as a string instead of parsed object
        if ($rawResponse -is [string]) {
            Write-DetailLog "Response returned as string, converting to object..."
            
            # Sanitize malformed JSON from Twelve Data API
            # The API sometimes returns }}}null} instead of }}} which breaks JSON parsing
            $sanitizedResponse = $rawResponse -replace '\}null\}', '}}'
            $sanitizedResponse = $sanitizedResponse -replace '\}\}null\}', '}}}'
            $sanitizedResponse = $sanitizedResponse -replace '\}\}\}null\}', '}}}}'
            
            if ($rawResponse -ne $sanitizedResponse) {
                Write-DetailLog "WARNING: Sanitized malformed JSON (removed erroneous null insertions)"
            }
            
            $response = $sanitizedResponse | ConvertFrom-Json
        } else {
            $response = $rawResponse
        }
        
        Write-DetailLog "Response Status: Success (HTTP 200)"
        Write-DetailLog ""
        Write-DetailLog "Raw Response (Full JSON):"
        $responseJson = $response | ConvertTo-Json -Depth 20
        Write-DetailLog $responseJson
        Write-DetailLog ""
        
        # Process each request's response
        Write-DetailLog "SECTION C: PER-STOCK ANALYSIS"
        Write-DetailLog "-----------------------------"
        
        foreach ($requestId in $requestMapping.Keys) {
            $stock = $requestMapping[$requestId]
            $symbolKey = $stock.Symbol
            
            Write-DetailLog ""
            Write-DetailLog "Stock: $($stock.Symbol) ($($stock.Name))"
            Write-DetailLog "  Exchange: $(if ($stock.Exchange) { $stock.Exchange } else { 'None (USA)' })"
            
            # Navigate response structure
            $reqResponse = $null
            
            # Try different response structures
            if ($response.data -and $response.data.$requestId) {
                $reqResponse = $response.data.$requestId
            } elseif ($response.$requestId) {
                $reqResponse = $response.$requestId
            }
            
            Write-DetailLog "  Response for $requestId found: $(if ($reqResponse) { 'Yes' } else { 'No' })"
            
            if ($reqResponse) {
                Write-DetailLog "  Response structure:"
                Write-DetailLog "    Status: $($reqResponse.status)"
                
                if ($reqResponse.status -eq "error") {
                    Write-DetailLog "    Error Message: $($reqResponse.message)"
                    Write-DetailLog "    Error Code: $($reqResponse.code)"
                    $errorStocks += $stock
                    Write-NoDataLog $stock.RawLine
                }
                elseif ($reqResponse.status -eq "success" -or $reqResponse.response) {
                    # Get the actual statistics data
                    $statsData = $null
                    if ($reqResponse.response) {
                        $statsData = $reqResponse.response
                    } else {
                        $statsData = $reqResponse
                    }
                    
                    # Check if statistics object exists
                    $hasStatistics = $false
                    if ($statsData.statistics) {
                        $hasStatistics = $true
                        Write-DetailLog "    Has statistics object: Yes"
                        Write-DetailLog "    Statistics keys: $($statsData.statistics.PSObject.Properties.Name -join ', ')"
                        
                        # Check for valuations_metrics
                        if ($statsData.statistics.valuations_metrics) {
                            Write-DetailLog "    Has valuations_metrics: Yes"
                            $pe = $statsData.statistics.valuations_metrics.trailing_pe
                            $marketCap = $statsData.statistics.valuations_metrics.market_capitalization
                            Write-DetailLog "      Sample - PE: $pe, Market Cap: $marketCap"
                        } else {
                            Write-DetailLog "    Has valuations_metrics: No"
                        }
                        
                        $successStocks += $stock
                    } else {
                        Write-DetailLog "    Has statistics object: No"
                        Write-DetailLog "    Available keys: $($statsData.PSObject.Properties.Name -join ', ')"
                        $noDataStocks += $stock
                        Write-NoDataLog $stock.RawLine
                    }
                } else {
                    Write-DetailLog "    Unexpected response structure"
                    Write-DetailLog "    Keys: $($reqResponse.PSObject.Properties.Name -join ', ')"
                    $noDataStocks += $stock
                    Write-NoDataLog $stock.RawLine
                }
            } else {
                Write-DetailLog "  No response found for this request ID"
                $noDataStocks += $stock
                Write-NoDataLog $stock.RawLine
            }
        }
        
    }
    catch {
        Write-DetailLog ""
        Write-DetailLog "SECTION D: ERRORS"
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
        
        # Mark all stocks in batch as error
        foreach ($stock in $batch) {
            $errorStocks += $stock
            Write-NoDataLog $stock.RawLine
        }
        
        Write-Host "  Batch $batchNum FAILED - see log for details" -ForegroundColor Red
    }
    
    Write-DetailLog ""
    
    # Progress update
    $successSoFar = $successStocks.Count
    $noDataSoFar = $noDataStocks.Count
    $errorSoFar = $errorStocks.Count
    Write-Host "  Results: $($batch.Count) stocks | Success: $successSoFar | No Data: $noDataSoFar | Errors: $errorSoFar" -ForegroundColor Gray
    
    # Update credits used
    $creditsUsedThisMinute += $creditsNeeded
    Write-DetailLog "Credits used this minute: $creditsUsedThisMinute / $CreditLimitPerMinute"
    
    # Add small delay between batches
    if ($batchNum -lt $batches.Count) {
        Write-Host "  Waiting 2 seconds before next batch..." -ForegroundColor DarkGray
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
Write-SummaryLog "Statistics Data Returned: $($successStocks.Count)"
Write-SummaryLog "No Statistics Data: $($noDataStocks.Count)"
Write-SummaryLog "Errors: $($errorStocks.Count)"
Write-SummaryLog ""
Write-SummaryLog "Success Rate: $([math]::Round(($successStocks.Count / $totalStocks) * 100, 2))%"
Write-SummaryLog ""

# Breakdown by country
Write-SummaryLog "Breakdown by Country:"
$countrySummary = $successStocks | Group-Object -Property Country
foreach ($group in $countrySummary) {
    Write-SummaryLog "  $($group.Name): $($group.Count) successful"
}

Write-SummaryLog ""
Write-SummaryLog "No Data by Country:"
$noDataByCountry = $noDataStocks | Group-Object -Property Country
foreach ($group in $noDataByCountry) {
    Write-SummaryLog "  $($group.Name): $($group.Count) no data"
}

Write-SummaryLog ""
Write-SummaryLog "=========================================="
Write-SummaryLog "LOG FILES CREATED"
Write-SummaryLog "=========================================="
Write-SummaryLog "Detail Log: $logFileDetails"
Write-SummaryLog "Summary Log: $logFileSummary"
Write-SummaryLog "No Data Stocks: $logFileNoData"
Write-SummaryLog ""
Write-SummaryLog "=========================================="
Write-SummaryLog "END OF SUMMARY"
Write-SummaryLog "=========================================="

Write-DetailLog "=========================================="
Write-DetailLog "END OF DETAILED LOG"
Write-DetailLog "=========================================="

# Console final output
Write-Host ""
Write-Host "=========================================="
Write-Host "TEST COMPLETE"
Write-Host "=========================================="
Write-Host "Total Stocks: $totalStocks"
Write-Host "Success: $($successStocks.Count)" -ForegroundColor Green
Write-Host "No Data: $($noDataStocks.Count)" -ForegroundColor Yellow
Write-Host "Errors: $($errorStocks.Count)" -ForegroundColor Red
Write-Host ""
Write-Host "Log Files Created:"
Write-Host "  Detail: $logFileDetails"
Write-Host "  Summary: $logFileSummary"
Write-Host "  No Data: $logFileNoData"
Write-Host ""