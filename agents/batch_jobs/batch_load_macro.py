"""
Batch job to fetch macroeconomic data from multiple API providers.

Providers:
- USA: FRED (GDP, CPI, Unemployment, Interest Rate)
- Canada: FRED (GDP, CPI, Unemployment, Interest Rate)
- EU: FRED (Eurozone EA20 GDP, HICP, Unemployment)
- India: World Bank (GDP Growth, Inflation, Unemployment)

Outputs:
- Raw JSON files: {country}_raw.json (API responses with metadata)
- Calculated JSON files: {country}_calculated.json (processed indicators)
- Error log: macro_errors_{timestamp}.log

Usage:
    python batch_load_macro.py

Reads API keys from: agents/.env
    - FRED_API_KEY

Output directory: agents/batch_jobs/batch_output/macro/
"""

import os
import json
import requests
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
from dotenv import load_dotenv


# =============================================================================
# CONFIGURATION
# =============================================================================

# API Endpoints
FRED_BASE = "https://api.stlouisfed.org/fred/series/observations"
WORLD_BANK_BASE = "https://api.worldbank.org/v2"

# Rate limits (calls per minute)
FRED_RATE_LIMIT = 100

# Delays (seconds)
FRED_DELAY = 1  # Minimal delay for 100 calls/min
RATE_LIMIT_WAIT = 60  # Wait time when rate limit hit

# Retry configuration
MAX_RETRIES = 3

# FRED Series IDs - USA
USA_SERIES = {
    'gdp': {
        'series_id': 'GDPC1',
        'units': 'pc1',  # Percent change from year ago
        'limit': 1,
        'description': 'Real GDP growth rate (YoY %)'
    },
    'inflation': {
        'series_id': 'CPIAUCSL',
        'units': 'pc1',  # Percent change from year ago
        'limit': 1,
        'description': 'CPI inflation rate (YoY %)'
    },
    'unemployment': {
        'series_id': 'LRHUTTTTUSM156S',
        'units': 'lin',  # Direct value
        'limit': 2,  # Fetch 2 months for averaging
        'description': 'Harmonized unemployment rate (%)'
    },
    'interest_rate': {
        'series_id': 'EFFR',
        'units': 'lin',  # Direct value
        'limit': 30,  # Fetch ~30 days for monthly average
        'description': 'Effective Federal Funds Rate (%)'
    }
}

# FRED Series IDs - Canada
CANADA_SERIES = {
    'gdp': {
        'series_id': 'NGDPRSAXDCCAQ',
        'units': 'pc1',  # Percent change from year ago
        'limit': 1,
        'description': 'Real GDP growth rate (YoY %)'
    },
    'inflation': {
        'series_id': 'CPALTT01CAQ659N',
        'units': 'lin',  # Already a percentage
        'limit': 1,
        'description': 'CPI inflation rate (YoY %)'
    },
    'unemployment': {
        'series_id': 'LRHUTTTTCAM156S',
        'units': 'lin',  # Direct value
        'limit': 2,  # Fetch 2 months for averaging
        'description': 'Harmonized unemployment rate (%)'
    },
    'interest_rate': {
        'series_id': 'IRSTCI01CAM156N',
        'units': 'lin',  # Direct value
        'limit': 1,
        'description': 'Policy interest rate (%)'
    }
}

# FRED Series IDs - EU (Eurozone EA20 - 20 countries)
EU_SERIES = {
    'gdp': {
        'series_id': 'CLV10MEURB1GQSCAEA20Q',
        'units': 'pc1',  # Percent change from year ago
        'limit': 1,
        'description': 'Real GDP growth rate (YoY %)'
    },
    'inflation': {
        'series_id': 'CP00MI15EA20M086NEST',
        'units': 'pc1',  # Percent change from year ago
        'limit': 1,
        'description': 'HICP inflation rate (YoY %)'
    },
    'unemployment': {
        'series_id': 'LRHUTTTTEZM156S',
        'units': 'lin',  # Direct value
        'limit': 2,  # Fetch 2 months for averaging
        'description': 'Harmonized unemployment rate (%)'
    }
}

# World Bank Indicator Codes - India
INDIA_INDICATORS = {
    'gdp_growth': {
        'code': 'NY.GDP.MKTP.KD.ZG',
        'description': 'Real GDP growth rate (annual %)'
    },
    'inflation': {
        'code': 'FP.CPI.TOTL.ZG',
        'description': 'CPI inflation rate (annual %)'
    },
    'unemployment': {
        'code': 'SL.UEM.TOTL.ZS',
        'description': 'Unemployment rate (% of labor force)'
    }
}


# =============================================================================
# GLOBAL STATE
# =============================================================================

class RateLimitTracker:
    """Track API calls and handle rate limiting."""
    
    def __init__(self, provider: str, limit: int, delay: float):
        self.provider = provider
        self.limit = limit
        self.delay = delay
        self.calls_this_minute = 0
        self.minute_start = time.time()
    
    def wait_if_needed(self):
        """Wait for delay between calls."""
        time.sleep(self.delay)
    
    def record_call(self):
        """Record an API call."""
        self.calls_this_minute += 1
    
    def handle_rate_limit_error(self):
        """Handle rate limit error - wait 60 seconds and reset."""
        print(f"  Rate limit hit for {self.provider}, waiting {RATE_LIMIT_WAIT}s...")
        time.sleep(RATE_LIMIT_WAIT)
        self.calls_this_minute = 0
        self.minute_start = time.time()


# Global tracker
fred_tracker = RateLimitTracker("FRED", FRED_RATE_LIMIT, FRED_DELAY)


# =============================================================================
# ERROR LOGGING
# =============================================================================

class ErrorLogger:
    """Handles detailed error logging to file."""
    
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.log_file = output_dir / f"macro_errors_{timestamp}.log"
        self.has_errors = False
    
    def log_error(self, 
                  country: str,
                  indicator: str,
                  endpoint: str,
                  parameters: Dict,
                  error_type: str,
                  error_message: str,
                  raw_response: Any = None,
                  stack_trace: str = None,
                  extra_context: str = None):
        """Log detailed error information."""
        self.has_errors = True
        
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Redact API keys from parameters
        safe_params = self._redact_keys(parameters)
        
        log_entry = f"""
================================================================================
[{timestamp}] ERROR - API Call Failed
================================================================================
Country: {country}
Indicator: {indicator}
Endpoint: {endpoint}
Parameters: {json.dumps(safe_params, indent=2)}
--------------------------------------------------------------------------------
Error Type: {error_type}
Error Message: {error_message}
--------------------------------------------------------------------------------
"""
        if extra_context:
            log_entry += f"Context: {extra_context}\n--------------------------------------------------------------------------------\n"
        
        if raw_response is not None:
            if isinstance(raw_response, (dict, list)):
                raw_str = json.dumps(raw_response, indent=2)
            else:
                raw_str = str(raw_response)
            log_entry += f"Raw Response:\n{raw_str}\n--------------------------------------------------------------------------------\n"
        
        if stack_trace:
            log_entry += f"Stack Trace:\n{stack_trace}\n"
        
        log_entry += "================================================================================\n"
        
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_entry)
    
    def log_unexpected_response(self,
                                country: str,
                                indicator: str,
                                endpoint: str,
                                parameters: Dict,
                                expected: str,
                                actual: Any,
                                raw_response: Any):
        """Log when response doesn't match expected structure."""
        self.has_errors = True
        
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        safe_params = self._redact_keys(parameters)
        
        log_entry = f"""
================================================================================
[{timestamp}] WARNING - Unexpected Response Structure
================================================================================
Country: {country}
Indicator: {indicator}
Endpoint: {endpoint}
Parameters: {json.dumps(safe_params, indent=2)}
--------------------------------------------------------------------------------
Expected: {expected}
Actual Keys/Type: {actual}
--------------------------------------------------------------------------------
Raw Response:
{json.dumps(raw_response, indent=2) if isinstance(raw_response, (dict, list)) else str(raw_response)}
================================================================================
"""
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_entry)
    
    def _redact_keys(self, params: Dict) -> Dict:
        """Redact API keys from parameters."""
        safe = params.copy()
        for key in ['api_key', 'apikey', 'api-key']:
            if key in safe:
                safe[key] = '***REDACTED***'
        return safe


# Global error logger (initialized in main)
error_logger: ErrorLogger = None


# =============================================================================
# API FETCH FUNCTIONS
# =============================================================================

def fetch_with_retry(fetch_func, tracker: RateLimitTracker, country: str, indicator: str, 
                     endpoint: str, parameters: Dict) -> Tuple[Optional[Dict], bool]:
    """
    Execute fetch function with retry logic.
    
    Returns:
        Tuple of (response_data, success_flag)
    """
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            tracker.wait_if_needed()
            tracker.record_call()
            
            response = fetch_func()
            
            # Check for rate limit in response
            if isinstance(response, dict):
                # FRED error response
                if 'error_code' in response or 'error_message' in response:
                    error_logger.log_error(
                        country=country,
                        indicator=indicator,
                        endpoint=endpoint,
                        parameters=parameters,
                        error_type="APIError",
                        error_message=response.get('error_message', 'Unknown API error'),
                        raw_response=response
                    )
                    if response.get('error_code') == 429:
                        tracker.handle_rate_limit_error()
                        continue
                    return None, False
            
            return response, True
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                error_logger.log_error(
                    country=country,
                    indicator=indicator,
                    endpoint=endpoint,
                    parameters=parameters,
                    error_type="HTTPError",
                    error_message=f"429 Too Many Requests (attempt {attempt}/{MAX_RETRIES})",
                    raw_response=e.response.text if e.response else None,
                    stack_trace=traceback.format_exc()
                )
                tracker.handle_rate_limit_error()
                continue
            else:
                error_logger.log_error(
                    country=country,
                    indicator=indicator,
                    endpoint=endpoint,
                    parameters=parameters,
                    error_type="HTTPError",
                    error_message=str(e),
                    raw_response=e.response.text if e.response else None,
                    stack_trace=traceback.format_exc()
                )
                return None, False
                
        except requests.exceptions.RequestException as e:
            error_logger.log_error(
                country=country,
                indicator=indicator,
                endpoint=endpoint,
                parameters=parameters,
                error_type=type(e).__name__,
                error_message=str(e),
                stack_trace=traceback.format_exc()
            )
            if attempt < MAX_RETRIES:
                time.sleep(5 * attempt)  # Exponential backoff for network errors
                continue
            return None, False
            
        except Exception as e:
            error_logger.log_error(
                country=country,
                indicator=indicator,
                endpoint=endpoint,
                parameters=parameters,
                error_type=type(e).__name__,
                error_message=str(e),
                stack_trace=traceback.format_exc()
            )
            return None, False
    
    return None, False


# =============================================================================
# USA - FRED
# =============================================================================

def download_usa_data(api_key: str) -> Dict[str, Any]:
    """
    Fetch USA macroeconomic data from FRED.
    
    Series:
    - GDPC1: Real GDP (with pc1 transformation)
    - CPIAUCSL: CPI (with pc1 transformation)
    - LRHUTTTTUSM156S: Harmonized Unemployment Rate
    - EFFR: Effective Federal Funds Rate
    
    Returns raw data structure with metadata.
    """
    print("Fetching USA data (FRED)...")
    
    raw_data = {
        "fetch_timestamp": datetime.now(timezone.utc).isoformat(),
        "api_provider": "FRED",
        "country": "USA",
        "requests": []
    }
    
    for indicator, config in USA_SERIES.items():
        print(f"  - {indicator}...", end=" ", flush=True)
        
        params = {
            "series_id": config['series_id'],
            "api_key": api_key,
            "file_type": "json",
            "limit": config['limit'],
            "sort_order": "desc",
            "units": config['units']
        }
        
        def do_fetch():
            response = requests.get(FRED_BASE, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        
        result, success = fetch_with_retry(
            fetch_func=do_fetch,
            tracker=fred_tracker,
            country="USA",
            indicator=indicator,
            endpoint=FRED_BASE,
            parameters=params
        )
        
        request_entry = {
            "indicator": indicator,
            "series_id": config['series_id'],
            "units": config['units'],
            "endpoint": FRED_BASE,
            "parameters": {
                "series_id": config['series_id'],
                "limit": config['limit'],
                "sort_order": "desc",
                "units": config['units']
            },
            "status": "success" if success else "failed",
            "response": result
        }
        
        # Validate response structure
        if success and result:
            if "observations" not in result:
                error_logger.log_unexpected_response(
                    country="USA",
                    indicator=indicator,
                    endpoint=FRED_BASE,
                    parameters=params,
                    expected="'observations' key in response",
                    actual=list(result.keys()) if isinstance(result, dict) else type(result).__name__,
                    raw_response=result
                )
                request_entry["status"] = "unexpected_structure"
        
        raw_data["requests"].append(request_entry)
        print("✓" if success else "✗")
    
    return raw_data


# =============================================================================
# CANADA - FRED
# =============================================================================

def download_canada_data(api_key: str) -> Dict[str, Any]:
    """
    Fetch Canada macroeconomic data from FRED.
    
    Series:
    - NGDPRSAXDCCAQ: Real GDP (with pc1 transformation)
    - CPALTT01CAQ659N: CPI Inflation (already percentage)
    - LRHUTTTTCAM156S: Harmonized Unemployment Rate
    - IRSTCI01CAM156N: Interest Rate
    
    Returns raw data structure with metadata.
    """
    print("Fetching Canada data (FRED)...")
    
    raw_data = {
        "fetch_timestamp": datetime.now(timezone.utc).isoformat(),
        "api_provider": "FRED",
        "country": "Canada",
        "requests": []
    }
    
    for indicator, config in CANADA_SERIES.items():
        print(f"  - {indicator}...", end=" ", flush=True)
        
        params = {
            "series_id": config['series_id'],
            "api_key": api_key,
            "file_type": "json",
            "limit": config['limit'],
            "sort_order": "desc",
            "units": config['units']
        }
        
        def do_fetch():
            response = requests.get(FRED_BASE, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        
        result, success = fetch_with_retry(
            fetch_func=do_fetch,
            tracker=fred_tracker,
            country="Canada",
            indicator=indicator,
            endpoint=FRED_BASE,
            parameters=params
        )
        
        request_entry = {
            "indicator": indicator,
            "series_id": config['series_id'],
            "units": config['units'],
            "endpoint": FRED_BASE,
            "parameters": {
                "series_id": config['series_id'],
                "limit": config['limit'],
                "sort_order": "desc",
                "units": config['units']
            },
            "status": "success" if success else "failed",
            "response": result
        }
        
        # Validate response structure
        if success and result:
            if "observations" not in result:
                error_logger.log_unexpected_response(
                    country="Canada",
                    indicator=indicator,
                    endpoint=FRED_BASE,
                    parameters=params,
                    expected="'observations' key in response",
                    actual=list(result.keys()) if isinstance(result, dict) else type(result).__name__,
                    raw_response=result
                )
                request_entry["status"] = "unexpected_structure"
        
        raw_data["requests"].append(request_entry)
        print("✓" if success else "✗")
    
    return raw_data


# =============================================================================
# EU - FRED (Eurozone EA20)
# =============================================================================

def download_eu_data(api_key: str) -> Dict[str, Any]:
    """
    Fetch EU (Eurozone EA20) macroeconomic data from FRED.
    
    Series:
    - CLV10MEURB1GQSCAEA20Q: Real GDP EA20 (with pc1 transformation)
    - CP00MI15EA20M086NEST: HICP EA20 (with pc1 transformation)
    - LRHUTTTTEZM156S: Unemployment Rate
    
    Returns raw data structure with metadata.
    """
    print("Fetching EU data (FRED - Eurozone EA20)...")
    
    raw_data = {
        "fetch_timestamp": datetime.now(timezone.utc).isoformat(),
        "api_provider": "FRED",
        "country": "EU",
        "requests": []
    }
    
    for indicator, config in EU_SERIES.items():
        print(f"  - {indicator}...", end=" ", flush=True)
        
        params = {
            "series_id": config['series_id'],
            "api_key": api_key,
            "file_type": "json",
            "limit": config['limit'],
            "sort_order": "desc",
            "units": config['units']
        }
        
        def do_fetch():
            response = requests.get(FRED_BASE, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        
        result, success = fetch_with_retry(
            fetch_func=do_fetch,
            tracker=fred_tracker,
            country="EU",
            indicator=indicator,
            endpoint=FRED_BASE,
            parameters=params
        )
        
        request_entry = {
            "indicator": indicator,
            "series_id": config['series_id'],
            "units": config['units'],
            "endpoint": FRED_BASE,
            "parameters": {
                "series_id": config['series_id'],
                "limit": config['limit'],
                "sort_order": "desc",
                "units": config['units']
            },
            "status": "success" if success else "failed",
            "response": result
        }
        
        # Validate response structure
        if success and result:
            if "observations" not in result:
                error_logger.log_unexpected_response(
                    country="EU",
                    indicator=indicator,
                    endpoint=FRED_BASE,
                    parameters=params,
                    expected="'observations' key in response",
                    actual=list(result.keys()) if isinstance(result, dict) else type(result).__name__,
                    raw_response=result
                )
                request_entry["status"] = "unexpected_structure"
        
        raw_data["requests"].append(request_entry)
        print("✓" if success else "✗")
    
    return raw_data


# =============================================================================
# INDIA - WORLD BANK
# =============================================================================

def download_india_data() -> Dict[str, Any]:
    """
    Fetch India macroeconomic data from World Bank API.
    
    Indicators (using mrnev=1 for most recent value):
    - NY.GDP.MKTP.KD.ZG: GDP Growth (annual %)
    - FP.CPI.TOTL.ZG: CPI Inflation (annual %)
    - SL.UEM.TOTL.ZS: Unemployment (% of labor force)
    
    Returns raw data structure with metadata.
    """
    print("Fetching India data (World Bank)...")
    
    raw_data = {
        "fetch_timestamp": datetime.now(timezone.utc).isoformat(),
        "api_provider": "World Bank",
        "country": "India",
        "requests": []
    }
    
    for indicator, config in INDIA_INDICATORS.items():
        print(f"  - {indicator}...", end=" ", flush=True)
        
        endpoint = f"{WORLD_BANK_BASE}/country/IN/indicator/{config['code']}"
        params = {
            "format": "json",
            "mrnev": 1  # Most recent non-empty value
        }
        
        try:
            response = requests.get(endpoint, params=params, timeout=30)
            response.raise_for_status()
            result = response.json()
            success = True
            
            # World Bank returns [metadata, data] structure
            if not isinstance(result, list) or len(result) < 2:
                error_logger.log_unexpected_response(
                    country="India",
                    indicator=indicator,
                    endpoint=endpoint,
                    parameters=params,
                    expected="List with [metadata, data]",
                    actual=type(result).__name__ if not isinstance(result, list) else f"List with {len(result)} elements",
                    raw_response=result
                )
                success = False
            elif result[1] is None or len(result[1]) == 0:
                error_logger.log_unexpected_response(
                    country="India",
                    indicator=indicator,
                    endpoint=endpoint,
                    parameters=params,
                    expected="Non-empty data array",
                    actual="Empty or null data array",
                    raw_response=result
                )
                success = False
                
        except requests.exceptions.RequestException as e:
            error_logger.log_error(
                country="India",
                indicator=indicator,
                endpoint=endpoint,
                parameters=params,
                error_type=type(e).__name__,
                error_message=str(e),
                stack_trace=traceback.format_exc()
            )
            result = None
            success = False
        except Exception as e:
            error_logger.log_error(
                country="India",
                indicator=indicator,
                endpoint=endpoint,
                parameters=params,
                error_type=type(e).__name__,
                error_message=str(e),
                stack_trace=traceback.format_exc()
            )
            result = None
            success = False
        
        request_entry = {
            "indicator": indicator,
            "indicator_code": config['code'],
            "endpoint": endpoint,
            "parameters": params,
            "status": "success" if success else "failed",
            "response": result
        }
        
        raw_data["requests"].append(request_entry)
        print("✓" if success else "✗")
        
        # Small delay for World Bank (be nice to free API)
        time.sleep(0.5)
    
    return raw_data


# =============================================================================
# DOWNLOAD ALL
# =============================================================================

def download_all(fred_key: str) -> Dict[str, Dict]:
    """
    Download data from all providers.
    
    Returns dict with raw data for each country.
    """
    results = {}
    
    # USA - FRED
    results["usa"] = download_usa_data(fred_key)
    
    # Canada - FRED
    results["canada"] = download_canada_data(fred_key)
    
    # EU - FRED
    results["eu"] = download_eu_data(fred_key)
    
    # India - World Bank (no key needed)
    results["india"] = download_india_data()
    
    return results


# =============================================================================
# CALCULATION FUNCTIONS
# =============================================================================

def extract_fred_value(observations: List, average_count: int = 1) -> Tuple[Optional[float], Optional[str]]:
    """
    Extract value from FRED observations.
    
    Args:
        observations: List of observation dicts
        average_count: Number of observations to average (1 = just latest)
    
    Returns:
        Tuple of (value, period)
    """
    if not observations:
        return None, None
    
    values = []
    period = None
    
    for i, obs in enumerate(observations):
        if i >= average_count:
            break
        
        value = obs.get("value", ".")
        if value != ".":
            try:
                values.append(float(value))
                if period is None:
                    period = obs.get("date")
            except (ValueError, TypeError):
                continue
    
    if not values:
        return None, None
    
    avg_value = sum(values) / len(values)
    return round(avg_value, 2), period


def calculate_usa_indicators(raw_data: Dict) -> Dict[str, Any]:
    """
    Calculate USA indicators from raw FRED data.
    
    All values use FRED transformations:
    - GDP: pc1 (percent change from year ago)
    - Inflation: pc1 (percent change from year ago)
    - Unemployment: Average of last 2 months
    - Interest Rate: Average of last month (~30 daily values)
    """
    indicators = {}
    
    for request in raw_data.get("requests", []):
        if request.get("status") != "success":
            continue
        
        indicator = request.get("indicator")
        response = request.get("response", {})
        observations = response.get("observations", [])
        
        if not observations:
            continue
        
        try:
            if indicator == "gdp":
                value, period = extract_fred_value(observations, average_count=1)
                if value is not None:
                    indicators["gdp_growth"] = {
                        "value": value,
                        "unit": "percent",
                        "period": period,
                        "description": USA_SERIES['gdp']['description']
                    }
            
            elif indicator == "inflation":
                value, period = extract_fred_value(observations, average_count=1)
                if value is not None:
                    indicators["inflation"] = {
                        "value": value,
                        "unit": "percent",
                        "period": period,
                        "description": USA_SERIES['inflation']['description']
                    }
            
            elif indicator == "unemployment":
                # Average of last 2 months
                value, period = extract_fred_value(observations, average_count=2)
                if value is not None:
                    indicators["unemployment"] = {
                        "value": value,
                        "unit": "percent",
                        "period": period,
                        "description": USA_SERIES['unemployment']['description']
                    }
            
            elif indicator == "interest_rate":
                # Average of last month (~30 daily values)
                value, period = extract_fred_value(observations, average_count=30)
                if value is not None:
                    indicators["interest_rate"] = {
                        "value": value,
                        "unit": "percent",
                        "period": period,
                        "description": USA_SERIES['interest_rate']['description']
                    }
                    
        except (ValueError, TypeError, KeyError) as e:
            error_logger.log_error(
                country="USA",
                indicator=indicator,
                endpoint="calculation",
                parameters={},
                error_type="CalculationError",
                error_message=str(e),
                raw_response=response,
                stack_trace=traceback.format_exc()
            )
    
    return indicators


def calculate_canada_indicators(raw_data: Dict) -> Dict[str, Any]:
    """
    Calculate Canada indicators from raw FRED data.
    
    - GDP: pc1 transformation
    - Inflation: Direct value (already percentage)
    - Unemployment: Average of last 2 months
    - Interest Rate: Direct value
    """
    indicators = {}
    
    for request in raw_data.get("requests", []):
        if request.get("status") != "success":
            continue
        
        indicator = request.get("indicator")
        response = request.get("response", {})
        observations = response.get("observations", [])
        
        if not observations:
            continue
        
        try:
            if indicator == "gdp":
                value, period = extract_fred_value(observations, average_count=1)
                if value is not None:
                    indicators["gdp_growth"] = {
                        "value": value,
                        "unit": "percent",
                        "period": period,
                        "description": CANADA_SERIES['gdp']['description']
                    }
            
            elif indicator == "inflation":
                value, period = extract_fred_value(observations, average_count=1)
                if value is not None:
                    indicators["inflation"] = {
                        "value": value,
                        "unit": "percent",
                        "period": period,
                        "description": CANADA_SERIES['inflation']['description']
                    }
            
            elif indicator == "unemployment":
                # Average of last 2 months
                value, period = extract_fred_value(observations, average_count=2)
                if value is not None:
                    indicators["unemployment"] = {
                        "value": value,
                        "unit": "percent",
                        "period": period,
                        "description": CANADA_SERIES['unemployment']['description']
                    }
            
            elif indicator == "interest_rate":
                value, period = extract_fred_value(observations, average_count=1)
                if value is not None:
                    indicators["interest_rate"] = {
                        "value": value,
                        "unit": "percent",
                        "period": period,
                        "description": CANADA_SERIES['interest_rate']['description']
                    }
                    
        except (ValueError, TypeError, KeyError) as e:
            error_logger.log_error(
                country="Canada",
                indicator=indicator,
                endpoint="calculation",
                parameters={},
                error_type="CalculationError",
                error_message=str(e),
                raw_response=response,
                stack_trace=traceback.format_exc()
            )
    
    return indicators


def calculate_eu_indicators(raw_data: Dict) -> Dict[str, Any]:
    """
    Calculate EU indicators from raw FRED data.
    
    - GDP: pc1 transformation
    - Inflation: pc1 transformation
    - Unemployment: Average of last 2 months
    """
    indicators = {}
    
    for request in raw_data.get("requests", []):
        if request.get("status") != "success":
            continue
        
        indicator = request.get("indicator")
        response = request.get("response", {})
        observations = response.get("observations", [])
        
        if not observations:
            continue
        
        try:
            if indicator == "gdp":
                value, period = extract_fred_value(observations, average_count=1)
                if value is not None:
                    indicators["gdp_growth"] = {
                        "value": value,
                        "unit": "percent",
                        "period": period,
                        "description": EU_SERIES['gdp']['description']
                    }
            
            elif indicator == "inflation":
                value, period = extract_fred_value(observations, average_count=1)
                if value is not None:
                    indicators["inflation"] = {
                        "value": value,
                        "unit": "percent",
                        "period": period,
                        "description": EU_SERIES['inflation']['description']
                    }
            
            elif indicator == "unemployment":
                # Average of last 2 months
                value, period = extract_fred_value(observations, average_count=2)
                if value is not None:
                    indicators["unemployment"] = {
                        "value": value,
                        "unit": "percent",
                        "period": period,
                        "description": EU_SERIES['unemployment']['description']
                    }
                    
        except (ValueError, TypeError, KeyError) as e:
            error_logger.log_error(
                country="EU",
                indicator=indicator,
                endpoint="calculation",
                parameters={},
                error_type="CalculationError",
                error_message=str(e),
                raw_response=response,
                stack_trace=traceback.format_exc()
            )
    
    return indicators


def calculate_india_indicators(raw_data: Dict) -> Dict[str, Any]:
    """
    Calculate India indicators from raw World Bank data.
    
    All values are pre-calculated by World Bank:
    - GDP Growth: Annual %
    - Inflation: Annual %
    - Unemployment: % of labor force
    """
    indicators = {}
    
    for request in raw_data.get("requests", []):
        if request.get("status") != "success":
            continue
        
        indicator = request.get("indicator")
        response = request.get("response", [])
        
        # World Bank format: [metadata, data_array]
        if not isinstance(response, list) or len(response) < 2:
            continue
        
        data_array = response[1]
        if not data_array:
            continue
        
        try:
            # Get most recent non-null value (mrnev=1 should give us just one)
            for entry in data_array:
                value = entry.get("value")
                if value is not None:
                    indicator_name = indicator
                    config = INDIA_INDICATORS.get(indicator, {})
                    
                    indicators[indicator_name] = {
                        "value": round(float(value), 2),
                        "unit": "percent",
                        "period": entry.get("date"),
                        "description": config.get('description', indicator)
                    }
                    break
                    
        except (ValueError, TypeError, KeyError) as e:
            error_logger.log_error(
                country="India",
                indicator=indicator,
                endpoint="calculation",
                parameters={},
                error_type="CalculationError",
                error_message=str(e),
                raw_response=response,
                stack_trace=traceback.format_exc()
            )
    
    return indicators


def generate_economic_context(indicators: Dict) -> str:
    """Generate economic context summary from indicators."""
    gdp = indicators.get("gdp_growth", {}).get("value", 0)
    inflation = indicators.get("inflation", {}).get("value", 0)
    unemployment = indicators.get("unemployment", {}).get("value", 0)
    
    context_parts = []
    
    if gdp > 3:
        context_parts.append("Strong economic growth")
    elif gdp > 2:
        context_parts.append("Moderate economic growth")
    elif gdp > 0:
        context_parts.append("Weak economic growth")
    else:
        context_parts.append("Economic contraction")
    
    if inflation > 4:
        context_parts.append("elevated inflation")
    elif inflation > 2:
        context_parts.append("moderate inflation")
    else:
        context_parts.append("low inflation")
    
    if unemployment > 7:
        context_parts.append("high unemployment")
    elif unemployment > 5:
        context_parts.append("moderate unemployment")
    else:
        context_parts.append("low unemployment")
    
    return ", ".join(context_parts) + "."


def calculate_and_validate(raw_data: Dict[str, Dict], output_dir: Path) -> Dict[str, Dict]:
    """
    Process raw data and calculate indicators for all countries.
    
    Saves calculated JSON files and returns results.
    """
    print("\nCalculating indicators...")
    
    results = {}
    
    # Calculate for each country
    calculations = {
        "usa": ("USA", "FRED", calculate_usa_indicators),
        "canada": ("Canada", "FRED", calculate_canada_indicators),
        "eu": ("EU", "FRED (Eurozone EA20)", calculate_eu_indicators),
        "india": ("India", "World Bank Open Data", calculate_india_indicators)
    }
    
    for key, (country_name, data_source, calc_func) in calculations.items():
        if key not in raw_data:
            continue
        
        print(f"  - {country_name}...", end=" ", flush=True)
        
        indicators = calc_func(raw_data[key])
        
        calculated = {
            "country": country_name,
            "data_source": data_source,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "indicators": indicators,
            "economic_context": generate_economic_context(indicators)
        }
        
        # Save calculated file
        output_file = output_dir / f"{key}_calculated.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(calculated, f, indent=2)
        
        results[key] = calculated
        print(f"✓ ({len(indicators)} indicators)")
    
    return results


# =============================================================================
# MAIN
# =============================================================================

def main():
    """Main entry point."""
    global error_logger
    
    print("=" * 60)
    print("MACRO ECONOMIC DATA BATCH LOADER")
    print("=" * 60)
    
    # Determine paths
    script_dir = Path(__file__).parent.resolve()
    
    # Handle both running from batch_jobs and other locations
    if script_dir.name == "batch_jobs":
        agents_dir = script_dir.parent
    else:
        # Assume we're somewhere in agents directory
        agents_dir = script_dir
        while agents_dir.name != "agents" and agents_dir.parent != agents_dir:
            agents_dir = agents_dir.parent
        if agents_dir.name != "agents":
            agents_dir = script_dir  # Fallback
    
    env_file = agents_dir / ".env"
    output_dir = agents_dir / "batch_jobs" / "batch_output" / "macro"
    
    print(f"\nConfiguration:")
    print(f"  .env file: {env_file}")
    print(f"  Output dir: {output_dir}")
    
    # Create output directory if needed
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"  Output directory ready: ✓")
    
    # Initialize error logger
    error_logger = ErrorLogger(output_dir)
    
    # Load environment variables
    if not env_file.exists():
        print(f"\nERROR: .env file not found at {env_file}")
        return
    
    load_dotenv(env_file)
    
    fred_key = os.getenv("FRED_API_KEY")
    
    if not fred_key:
        print("\nERROR: FRED_API_KEY not found in .env")
        return
    
    print(f"  FRED key: {fred_key[:4]}...{fred_key[-4:]}")
    
    # Check for existing raw files
    existing_files = {
        "usa": output_dir / "usa_raw.json",
        "canada": output_dir / "canada_raw.json",
        "eu": output_dir / "eu_raw.json",
        "india": output_dir / "india_raw.json"
    }
    
    has_existing = all(f.exists() for f in existing_files.values())
    
    if has_existing:
        print(f"\n  Existing raw files found in {output_dir}")
    
    # Ask user whether to download or use existing
    print("\n" + "-" * 60)
    proceed = input("Download fresh data from APIs? (yes/no): ").strip().lower()
    
    if proceed == "yes":
        print("\n" + "-" * 60)
        print("DOWNLOADING RAW DATA")
        print("-" * 60)
        
        # Download all data
        raw_data = download_all(fred_key)
        
        # Save raw data files
        print("\nSaving raw data files...")
        for country, data in raw_data.items():
            output_file = output_dir / f"{country}_raw.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            print(f"  - {output_file.name} ✓")
    
    elif proceed == "no":
        if not has_existing:
            print("\nERROR: No existing raw files found. Please run with 'yes' first.")
            return
        
        print("\n" + "-" * 60)
        print("LOADING EXISTING RAW DATA")
        print("-" * 60)
        
        # Load existing raw files
        raw_data = {}
        for country, filepath in existing_files.items():
            print(f"  Loading {filepath.name}...", end=" ", flush=True)
            with open(filepath, 'r', encoding='utf-8') as f:
                raw_data[country] = json.load(f)
            print("✓")
    
    else:
        print("\nInvalid input. Please enter 'yes' or 'no'.")
        return
    
    print("\n" + "-" * 60)
    print("CALCULATING INDICATORS")
    print("-" * 60)
    
    # Calculate and validate
    calculated_data = calculate_and_validate(raw_data, output_dir)
    
    # Print summary
    print("\n" + "=" * 60, flush=True)
    print("SUMMARY", flush=True)
    print("=" * 60, flush=True)
    
    total_indicators = 0
    expected = {"usa": 4, "canada": 4, "eu": 3, "india": 3}
    
    for country, data in calculated_data.items():
        indicators = data.get("indicators", {})
        count = len(indicators)
        total_indicators += count
        exp = expected.get(country, 0)
        status = "✓" if count == exp else f"({count}/{exp})"
        print(f"  {data['country']:10}: {count}/{exp} indicators {status}", flush=True)
        
        # Show indicator values
        for name, ind in indicators.items():
            print(f"              - {name}: {ind['value']}% ({ind['period']})", flush=True)
    
    print(f"\n  Total indicators: {total_indicators}/14", flush=True)
    print(f"\n  Output directory: {output_dir}", flush=True)
    
    if error_logger.has_errors:
        print(f"  Error log: {error_logger.log_file.name}", flush=True)
    else:
        print("  Errors: None", flush=True)
    
    print("\n" + "=" * 60, flush=True)
    print("COMPLETE", flush=True)
    print("=" * 60, flush=True)


if __name__ == "__main__":
    main()