# TestSentimentsAPI.ps1
# PowerShell script to test Twelve Data sentiment APIs via /batch endpoint
# Fetches analyst ratings, recommendations, and price targets
# Creates detailed logs for debugging API issues

param(
    [Parameter(Mandatory=$true)]
    [string]$InputFile,
    
    [string]$ApiKey = "demo",
    
    [int]$BatchSize = 2,
    
    [int]$CreditPerStock = 250,
    
    [int]$CreditLimitPerMinute = 610
)

# Log files with timestamp
$timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$logFileDetails = "twelvedata_sentiments_iop_$timestamp.log"
$logFileSummary = "twelvedata_sentiments_summary_$timestamp.log"
$logFileNoData = "twelvedata_sentiments_nodata_$timestamp.log"

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
$partialStocks = @()
$noDataStocks = @()
$errorStocks = @()

# Write initial headers
Write-SummaryLog "=========================================="
Write-SummaryLog "TWELVE DATA SENTIMENTS API TEST - SUMMARY"
Write-SummaryLog "=========================================="
Write-SummaryLog ""
Write-SummaryLog "Input File: $InputFile"
Write-SummaryLog "Total Stocks: $totalStocks"
Write-SummaryLog "Batch Size: $BatchSize (stocks per batch)"
Write-SummaryLog "Credit per stock: $CreditPerStock"
Write-SummaryLog "Credit limit per minute: $CreditLimitPerMinute"
Write-SummaryLog "API Key: $($ApiKey.Substring(0, [Math]::Min(4, $ApiKey.Length)))..."
Write-SummaryLog ""
Write-SummaryLog "Endpoints per stock:"
Write-SummaryLog "  - /analyst_ratings/light (75 credits)"
Write-SummaryLog "  - /recommendations (100 credits)"
Write-SummaryLog "  - /price_target (75 credits)"
Write-SummaryLog ""

Write-DetailLog "=========================================="
Write-DetailLog "TWELVE DATA SENTIMENTS API TEST - DETAILED LOG"
Write-DetailLog "=========================================="
Write-DetailLog ""
Write-DetailLog "Purpose: Debug sentiment endpoints via /batch API"
Write-DetailLog "Input File: $InputFile"
Write-DetailLog "Total Stocks: $totalStocks"
Write-DetailLog "Batch Size: $BatchSize (stocks per batch)"
Write-DetailLog "Endpoints: analyst_ratings/light, recommendations, price_target"
Write-DetailLog ""

Write-NoDataLog "# Stocks with no sentiment data returned"
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
Write-Host "TWELVE DATA SENTIMENTS API TEST"
Write-Host "=========================================="
Write-Host "Input File: $InputFile"
Write-Host "Total Stocks: $totalStocks"
Write-Host "Batches: $($batches.Count)"
Write-Host "Endpoints per stock: analyst_ratings/light, recommendations, price_target"
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
    $creditsNeeded = $batch.Count * $CreditPerStock
    
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
    # Each stock gets 3 endpoints: analyst_ratings, recommendations, price_target
    $jsonParts = @()
    $requestMapping = @{}
    $stockIndex = 0
    
    foreach ($stock in $batch) {
        $stockIndex++
        
        # Create request IDs for each endpoint of this stock
        $analystRatingsId = "stock${stockIndex}_analyst_ratings"
        $recommendationsId = "stock${stockIndex}_recommendations"
        $priceTargetId = "stock${stockIndex}_price_target"
        
        # Store mapping for later
        $requestMapping[$stockIndex] = @{
            Stock = $stock
            AnalystRatingsId = $analystRatingsId
            RecommendationsId = $recommendationsId
            PriceTargetId = $priceTargetId
        }
        
        # Build URLs for each endpoint
        if ($stock.Exchange) {
            $analystRatingsUrl = "/analyst_ratings/light?symbol=$($stock.Symbol)&mic_code=$($stock.Exchange)&apikey=$ApiKey"
            $recommendationsUrl = "/recommendations?symbol=$($stock.Symbol)&mic_code=$($stock.Exchange)&apikey=$ApiKey"
            $priceTargetUrl = "/price_target?symbol=$($stock.Symbol)&mic_code=$($stock.Exchange)&apikey=$ApiKey"
        } else {
            $analystRatingsUrl = "/analyst_ratings/light?symbol=$($stock.Symbol)&apikey=$ApiKey"
            $recommendationsUrl = "/recommendations?symbol=$($stock.Symbol)&apikey=$ApiKey"
            $priceTargetUrl = "/price_target?symbol=$($stock.Symbol)&apikey=$ApiKey"
        }
        
        $jsonParts += """$analystRatingsId"": {""url"": ""$analystRatingsUrl""}"
        $jsonParts += """$recommendationsId"": {""url"": ""$recommendationsUrl""}"
        $jsonParts += """$priceTargetId"": {""url"": ""$priceTargetUrl""}"
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
        
        # Process each stock's response
        Write-DetailLog "SECTION C: PER-STOCK ANALYSIS"
        Write-DetailLog "-----------------------------"
        
        foreach ($stockIdx in $requestMapping.Keys) {
            $mapping = $requestMapping[$stockIdx]
            $stock = $mapping.Stock
            
            Write-DetailLog ""
            Write-DetailLog "Stock: $($stock.Symbol) ($($stock.Name))"
            Write-DetailLog "  Exchange: $(if ($stock.Exchange) { $stock.Exchange } else { 'None (USA)' })"
            
            # Get batch data
            $batchData = if ($response.data) { $response.data } else { $response }
            
            # Get each endpoint response
            $analystRatingsResp = $batchData.$($mapping.AnalystRatingsId)
            $recommendationsResp = $batchData.$($mapping.RecommendationsId)
            $priceTargetResp = $batchData.$($mapping.PriceTargetId)
            
            Write-DetailLog "  Responses found:"
            Write-DetailLog "    - analyst_ratings/light: $(if ($analystRatingsResp) { 'Yes' } else { 'No' })"
            Write-DetailLog "    - recommendations: $(if ($recommendationsResp) { 'Yes' } else { 'No' })"
            Write-DetailLog "    - price_target: $(if ($priceTargetResp) { 'Yes' } else { 'No' })"
            
            # Check each endpoint status
            $analystSuccess = $false
            $recoSuccess = $false
            $priceSuccess = $false
            
            # Analyst Ratings
            if ($analystRatingsResp) {
                if ($analystRatingsResp.status -eq "error") {
                    Write-DetailLog "    analyst_ratings ERROR: $($analystRatingsResp.message)"
                } elseif ($analystRatingsResp.status -eq "success" -or $analystRatingsResp.response) {
                    $arData = if ($analystRatingsResp.response) { $analystRatingsResp.response } else { $analystRatingsResp }
                    if ($arData.ratings) {
                        $analystSuccess = $true
                        Write-DetailLog "    analyst_ratings: $($arData.ratings.Count) ratings found"
                    } else {
                        Write-DetailLog "    analyst_ratings: No ratings data"
                    }
                }
            }
            
            # Recommendations
            if ($recommendationsResp) {
                if ($recommendationsResp.status -eq "error") {
                    Write-DetailLog "    recommendations ERROR: $($recommendationsResp.message)"
                } elseif ($recommendationsResp.status -eq "success" -or $recommendationsResp.response) {
                    $recoData = if ($recommendationsResp.response) { $recommendationsResp.response } else { $recommendationsResp }
                    if ($recoData.trends -or $recoData.rating) {
                        $recoSuccess = $true
                        $rating = $recoData.rating
                        Write-DetailLog "    recommendations: Rating = $rating"
                    } else {
                        Write-DetailLog "    recommendations: No trends data"
                    }
                }
            }
            
            # Price Target
            if ($priceTargetResp) {
                if ($priceTargetResp.status -eq "error") {
                    Write-DetailLog "    price_target ERROR: $($priceTargetResp.message)"
                } elseif ($priceTargetResp.status -eq "success" -or $priceTargetResp.response) {
                    $ptData = if ($priceTargetResp.response) { $priceTargetResp.response } else { $priceTargetResp }
                    if ($ptData.price_target) {
                        $priceSuccess = $true
                        $avgTarget = $ptData.price_target.average
                        Write-DetailLog "    price_target: Average = $avgTarget"
                    } else {
                        Write-DetailLog "    price_target: No price target data"
                    }
                }
            }
            
            # Categorize result
            if ($analystSuccess -and $recoSuccess -and $priceSuccess) {
                Write-DetailLog "  Result: FULL SUCCESS (all 3 endpoints)"
                $successStocks += $stock
            } elseif ($analystSuccess -or $recoSuccess -or $priceSuccess) {
                Write-DetailLog "  Result: PARTIAL SUCCESS"
                $partialStocks += $stock
            } else {
                Write-DetailLog "  Result: NO DATA"
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
    $partialSoFar = $partialStocks.Count
    $noDataSoFar = $noDataStocks.Count
    $errorSoFar = $errorStocks.Count
    Write-Host "  Results: $($batch.Count) stocks | Full: $successSoFar | Partial: $partialSoFar | No Data: $noDataSoFar | Errors: $errorSoFar" -ForegroundColor Gray
    
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
Write-SummaryLog "Full Success (all 3 endpoints): $($successStocks.Count)"
Write-SummaryLog "Partial Success (1-2 endpoints): $($partialStocks.Count)"
Write-SummaryLog "No Data: $($noDataStocks.Count)"
Write-SummaryLog "Errors: $($errorStocks.Count)"
Write-SummaryLog ""
Write-SummaryLog "Success Rate (Full): $([math]::Round(($successStocks.Count / $totalStocks) * 100, 2))%"
Write-SummaryLog "Success Rate (Any Data): $([math]::Round((($successStocks.Count + $partialStocks.Count) / $totalStocks) * 100, 2))%"
Write-SummaryLog ""

# Breakdown by country
Write-SummaryLog "Full Success by Country:"
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
Write-Host "Full Success: $($successStocks.Count)" -ForegroundColor Green
Write-Host "Partial Success: $($partialStocks.Count)" -ForegroundColor Yellow
Write-Host "No Data: $($noDataStocks.Count)" -ForegroundColor Yellow
Write-Host "Errors: $($errorStocks.Count)" -ForegroundColor Red
Write-Host ""
Write-Host "Log Files Created:"
Write-Host "  Detail: $logFileDetails"
Write-Host "  Summary: $logFileSummary"
Write-Host "  No Data: $logFileNoData"
Write-Host ""