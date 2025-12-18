"""
Macro Economic Data Tool with real API integration.
Supports USA (Alpha Vantage), Canada (FRED), EU (FRED), India (World Bank).
"""

from typing import Dict, Any, Optional
from .base import BaseTool, ToolError
from .cache import FirestoreCache
import requests
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class MacroEconomicDataTool(BaseTool):
    """
    Retrieves macroeconomic indicators from various APIs.
    Includes caching and fallback strategies.
    """
    
    def __init__(self, alpha_vantage_key: str, fred_key: str):
        """
        Initialize with API keys.
        
        Args:
            alpha_vantage_key: Alpha Vantage API key
            fred_key: FRED API key
        """
        self.alpha_vantage_key = alpha_vantage_key
        self.fred_key = fred_key
        self.cache = FirestoreCache(collection_name="macro_data_cache")
        
        # API endpoints
        self.av_base = "https://www.alphavantage.co/query"
        self.fred_base = "https://api.stlouisfed.org/fred/series/observations"
        self.wb_base = "https://api.worldbank.org/v2"
    
    @property
    def name(self) -> str:
        return "get_macro_economic_data"
    
    @property
    def description(self) -> str:
        return """Retrieves current macroeconomic indicators for the specified country.

Returns raw economic data including:
- GDP growth rate (annual %)
- Inflation rate (annual %)  
- Unemployment rate (%)
- Interest rates
- Economic context and trends

Data sources:
- USA: Alpha Vantage
- Canada: FRED (Federal Reserve Economic Data)
- EU: FRED (Eurozone aggregates)
- India: World Bank API

Use this tool FIRST to understand the current economic environment before making portfolio decisions."""
    
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "country": {
                    "type": "string",
                    "enum": ["USA", "Canada", "EU", "India"],
                    "description": "Target country for economic data"
                }
            },
            "required": ["country"]
        }
    
    def execute(self, country: str) -> Dict[str, Any]:
        """
        Retrieve macro data with caching and fallback.
        
        Strategy:
        1. Check cache (1-hour TTL)
        2. If miss, call API
        3. If API fails, use stale cache (up to 24h old)
        4. If no cache, return structured error
        """
        # Check fresh cache
        cached = self.cache.get(ttl_hours=720, country=country)
        if cached:
            logger.info(f"Using cached macro data for {country}")
            return {
                "success": True,
                "data": cached,
                "from_cache": True
            }
        
        # Attempt API call
        try:
            if country == "USA":
                data = self._fetch_usa_data()
            elif country == "Canada":
                data = self._fetch_canada_data()
            elif country == "EU":
                data = self._fetch_eu_data()
            elif country == "India":
                data = self._fetch_india_data()
            else:
                return ToolError.create(
                    code=ToolError.INVALID_PARAMETERS,
                    message=f"Unsupported country: {country}",
                    user_message=f"Economic data not available for {country}"
                )
            
            # Cache successful result
            self.cache.set(data, country=country)
            
            return {
                "success": True,
                "data": data,
                "from_cache": False
            }
            
        except Exception as e:
            logger.error(f"API call failed for {country}: {e}")
            
            # Try stale cache as fallback
            stale = self.cache.get_stale(max_age_hours=1440, country=country)
            if stale:
                logger.warning(f"Using stale cache for {country}")
                return {
                    "success": True,
                    "data": stale,
                    "from_cache": True,
                    "warning": ToolError.create(
                        code=ToolError.CACHE_STALE,
                        message="Using cached data due to API unavailability",
                        severity=ToolError.WARNING,
                        user_message="Economic data may be slightly outdated"
                    )
                }
            
            # No cache available - return error
            return ToolError.create(
                code=ToolError.API_UNAVAILABLE,
                message=f"Failed to fetch macro data for {country}",
                user_message="Economic data temporarily unavailable",
                technical_details=str(e)
            )
        
    def _fetch_usa_data(self) -> Dict[str, Any]:
        """Fetch USA data from Alpha Vantage."""
        import time
        
        indicators = {}
        
        # GDP - Calculate year-over-year growth from annual data
        try:
            time.sleep(12)
            gdp_response = requests.get(
                self.av_base,
                params={"function": "REAL_GDP", "apikey": self.alpha_vantage_key},
                timeout=10
            )
            gdp_response.raise_for_status()
            gdp_data = gdp_response.json()
            
            if "data" in gdp_data and len(gdp_data["data"]) >= 2:
                # [0] = 2024, [1] = 2023 (annual data, descending order)
                latest = gdp_data["data"][0]
                previous = gdp_data["data"][1]
                
                latest_value = float(latest.get("value", 0))
                previous_value = float(previous.get("value", 1))
                
                if previous_value > 0:
                    # Simple year-over-year growth calculation
                    annual_growth = ((latest_value - previous_value) / previous_value) * 100
                    
                    indicators["gdp_growth"] = {
                        "value": round(annual_growth, 2),
                        "unit": "percent",
                        "period": latest.get("date"),
                        "description": "Real GDP annual growth rate (year-over-year)"
                    }
                else:
                    logger.warning("Invalid GDP previous value")
            else:
                logger.warning("Insufficient GDP data points")
                
        except Exception as e:
            logger.error(f"Failed to fetch US GDP: {e}")
        
        # Inflation - Already annual percentage
        try:
            time.sleep(12)
            inflation_response = requests.get(
                self.av_base,
                params={"function": "INFLATION", "apikey": self.alpha_vantage_key},
                timeout=10
            )
            inflation_response.raise_for_status()
            inflation_data = inflation_response.json()
            
            if "data" in inflation_data and len(inflation_data["data"]) > 0:
                latest = inflation_data["data"][0]
                value = latest.get("value", "0")
                
                try:
                    inflation_rate = float(value)
                except (ValueError, TypeError):
                    logger.warning(f"Invalid inflation value: {value}")
                    inflation_rate = 0
                
                indicators["inflation"] = {
                    "value": round(inflation_rate, 2),
                    "unit": "percent",
                    "period": latest.get("date"),
                    "description": "Annual inflation rate (CPI)"
                }
            else:
                logger.warning("No inflation data available")
                
        except Exception as e:
            logger.error(f"Failed to fetch US inflation: {e}")
        
        # Unemployment - Monthly percentage
        try:
            time.sleep(12)
            unemployment_response = requests.get(
                self.av_base,
                params={"function": "UNEMPLOYMENT", "apikey": self.alpha_vantage_key},
                timeout=10
            )
            unemployment_response.raise_for_status()
            unemployment_data = unemployment_response.json()
            
            if "data" in unemployment_data and len(unemployment_data["data"]) > 0:
                latest = unemployment_data["data"][0]
                value = latest.get("value", "0")
                
                try:
                    unemployment_rate = float(value)
                except (ValueError, TypeError):
                    logger.warning(f"Invalid unemployment value: {value}")
                    unemployment_rate = 0
                
                indicators["unemployment"] = {
                    "value": round(unemployment_rate, 2),
                    "unit": "percent",
                    "period": latest.get("date"),
                    "description": "Unemployment rate"
                }
            else:
                logger.warning("No unemployment data available")
                
        except Exception as e:
            logger.error(f"Failed to fetch US unemployment: {e}")
        
        if not indicators:
            raise ValueError("No indicators successfully retrieved from Alpha Vantage")
        
        return {
            "country": "USA",
            "data_source": "Alpha Vantage",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "indicators": indicators,
            "economic_context": self._generate_context(indicators)
        }
    
    def _fetch_canada_data(self, years: int) -> Dict[str, Any]:
        """Fetch Canada data from FRED."""
        result = {}
        series_ids = {
            "gdp": "NGDPRSAXDCCAQ",
            "inflation": "FPCPITOTLZGCAN",
            "unemployment": "LRUNTTTTCAQ156S"
        }
        
        indicators = {}
        
        # Calculate start date
        start_date = (datetime.now() - timedelta(days=years*365)).strftime('%Y-%m-%d')
        
        # Fetch GDP - Returns absolute values, need to calculate growth
        try:
            response = requests.get(
                self.fred_base,
                params={
                    "series_id": series_ids['gdp'],
                    "api_key": self.fred_key,
                    "file_type": "json",
                    "limit": 2,
                    "sort_order": "desc"
                },
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            if "observations" in data and len(data["observations"]) >= 2:
                # [0] = most recent, [1] = previous period
                latest = data["observations"][0]
                previous = data["observations"][1]
                
                latest_value = latest.get("value", ".")
                previous_value = previous.get("value", ".")
                
                if latest_value != "." and previous_value != ".":
                    latest_gdp = float(latest_value)
                    previous_gdp = float(previous_value)
                    
                    if previous_gdp > 0:
                        gdp_growth = ((latest_gdp - previous_gdp) / previous_gdp) * 100
                        
                        indicators["gdp_growth"] = {
                            "value": round(gdp_growth, 2),
                            "unit": "percent",
                            "period": latest.get("date"),
                            "description": "Real GDP growth rate (annual %)"
                        }
        except Exception as e:
            logger.error(f"Failed to fetch Canada GDP: {e}")
        
        # Fetch Inflation - Already a percentage rate
        try:
            response = requests.get(
                self.fred_base,
                params={
                    "series_id": series_ids['inflation'],
                    "api_key": self.fred_key,
                    "file_type": "json",
                    "limit": 1,
                    "sort_order": "desc"
                },
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            if "observations" in data and len(data["observations"]) > 0:
                obs = data["observations"][0]
                value = obs.get("value", ".")
                
                if value != ".":
                    indicators["inflation"] = {
                        "value": round(float(value), 2),
                        "unit": "percent",
                        "period": obs.get("date"),
                        "description": "Consumer Price Index inflation (annual %)"
                    }
        except Exception as e:
            logger.error(f"Failed to fetch Canada inflation: {e}")
        
        # Fetch Unemployment
        try:
            response = requests.get(
                self.fred_base,
                params={
                    "series_id": series_ids['unemployment'],
                    "api_key": self.fred_key,
                    "file_type": "json",
                    "limit": 1,
                    "sort_order": "desc"
                },
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            if "observations" in data and len(data["observations"]) > 0:
                obs = data["observations"][0]
                value = obs.get("value", ".")
                
                if value != ".":
                    indicators["unemployment"] = {
                        "value": round(float(value), 2),
                        "unit": "percent",
                        "period": obs.get("date"),
                        "description": "Unemployment rate (% of labor force)"
                    }
        except Exception as e:
            logger.error(f"Failed to fetch Canada unemployment: {e}")
        
        if not indicators:
            raise ValueError("No indicators successfully retrieved")
        
        return {
            "country": "Canada",
            "data_source": "FRED (Federal Reserve Economic Data)",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "indicators": indicators,
            "economic_context": self._generate_context(indicators)
        }
    
    def _fetch_eu_data(self) -> Dict[str, Any]:
        """Fetch EU data from FRED (Eurozone aggregates)."""
        series_ids = {
            "gdp": "CLVMNACSCAB1GQEA19",
            "inflation": "CP0000EZ19M086NEST",
            "unemployment": "LRHUTTTTEZM156S"
        }
        
        indicators = {}
        
        # Fetch GDP - Returns absolute values, need to calculate growth
        try:
            response = requests.get(
                self.fred_base,
                params={
                    "series_id": series_ids['gdp'],
                    "api_key": self.fred_key,
                    "file_type": "json",
                    "limit": 2,
                    "sort_order": "desc"
                },
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            if "observations" in data and len(data["observations"]) >= 2:
                latest = data["observations"][0]
                previous = data["observations"][1]
                
                latest_value = latest.get("value", ".")
                previous_value = previous.get("value", ".")
                
                if latest_value != "." and previous_value != ".":
                    latest_gdp = float(latest_value)
                    previous_gdp = float(previous_value)
                    
                    if previous_gdp > 0:
                        gdp_growth = ((latest_gdp - previous_gdp) / previous_gdp) * 100
                        
                        indicators["gdp_growth"] = {
                            "value": round(gdp_growth, 2),
                            "unit": "percent",
                            "period": latest.get("date"),
                            "description": "Real GDP growth rate (annual %)"
                        }
        except Exception as e:
            logger.error(f"Failed to fetch EU GDP: {e}")
        
        # Fetch Inflation - HICP index, need to calculate year-over-year change
        try:
            response = requests.get(
                self.fred_base,
                params={
                    "series_id": series_ids['inflation'],
                    "api_key": self.fred_key,
                    "file_type": "json",
                    "limit": 13,
                    "sort_order": "desc"
                },
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            if "observations" in data and len(data["observations"]) >= 13:
                # [0] = current month, [12] = same month last year
                current = data["observations"][0]
                year_ago = data["observations"][12]
                
                current_value = current.get("value", ".")
                year_ago_value = year_ago.get("value", ".")
                
                if current_value != "." and year_ago_value != ".":
                    current_index = float(current_value)
                    year_ago_index = float(year_ago_value)
                    
                    if year_ago_index > 0:
                        inflation_rate = ((current_index - year_ago_index) / year_ago_index) * 100
                        
                        indicators["inflation"] = {
                            "value": round(inflation_rate, 2),
                            "unit": "percent",
                            "period": current.get("date"),
                            "description": "HICP annual inflation rate"
                        }
        except Exception as e:
            logger.error(f"Failed to fetch EU inflation: {e}")
        
        # Fetch Unemployment
        try:
            response = requests.get(
                self.fred_base,
                params={
                    "series_id": series_ids['unemployment'],
                    "api_key": self.fred_key,
                    "file_type": "json",
                    "limit": 1,
                    "sort_order": "desc"
                },
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            if "observations" in data and len(data["observations"]) > 0:
                obs = data["observations"][0]
                value = obs.get("value", ".")
                
                if value != ".":
                    indicators["unemployment"] = {
                        "value": round(float(value), 2),
                        "unit": "percent",
                        "period": obs.get("date"),
                        "description": "Unemployment rate (% of labor force)"
                    }
        except Exception as e:
            logger.error(f"Failed to fetch EU unemployment: {e}")
        
        if not indicators:
            raise ValueError("No indicators successfully retrieved")
        
        return {
            "country": "EU",
            "data_source": "FRED (Eurozone Data)",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "indicators": indicators,
            "economic_context": self._generate_context(indicators)
        }
    
    def _fetch_india_data(self) -> Dict[str, Any]:
        """Fetch India data from World Bank."""
        indicator_codes = {
            "gdp_growth": "NY.GDP.MKTP.KD.ZG",
            "inflation": "FP.CPI.TOTL.ZG",
            "unemployment": "SL.UEM.TOTL.ZS"
        }
        
        indicators = {}
        
        for indicator, code in indicator_codes.items():
            try:
                response = requests.get(
                    f"{self.wb_base}/country/IN/indicator/{code}",
                    params={
                        "format": "json",
                        "per_page": 1,
                        "date": "2020:2024"  # Recent years
                    },
                    timeout=10
                )
                response.raise_for_status()
                data = response.json()
                
                if len(data) > 1 and len(data[1]) > 0:
                    latest = data[1][0]
                    value = latest.get("value")
                    
                    if value is not None:
                        indicators[indicator] = {
                            "value": float(value),
                            "unit": "percent",
                            "period": latest.get("date"),
                            "description": self._get_indicator_description(indicator)
                        }
            except Exception as e:
                logger.error(f"Failed to fetch India {indicator}: {e}")
        
        if not indicators:
            raise ValueError("No indicators successfully retrieved")
        
        return {
            "country": "India",
            "data_source": "World Bank Open Data",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "indicators": indicators,
            "economic_context": self._generate_context(indicators)
        }
    
    def _get_indicator_description(self, indicator: str) -> str:
        """Get human-readable description for indicator."""
        descriptions = {
            "gdp_growth": "Real GDP growth rate (annual %)",
            "inflation": "Consumer Price Index inflation (annual %)",
            "unemployment": "Unemployment rate (% of labor force)"
        }
        return descriptions.get(indicator, indicator)
    
    def _generate_context(self, indicators: Dict) -> str:
        """Generate economic context summary from indicators."""
        gdp = indicators.get("gdp_growth", {}).get("value", 0)
        inflation = indicators.get("inflation", {}).get("value", 0)
        unemployment = indicators.get("unemployment", {}).get("value", 0)
        
        context_parts = []
        
        if gdp > 3:
            context_parts.append("Strong economic growth")
        elif gdp > 2:
            context_parts.append("Moderate economic growth")
        else:
            context_parts.append("Weak economic growth")
        
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