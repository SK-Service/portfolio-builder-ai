"""
Market Sentiment Tool - Reads from Firestore with real-time API fallback.

Provides analyst ratings, recommendations, and price targets for stocks.
Uses a tiered approach:
1. Check Firestore cache for the specific stock (if < 30 days old)
2. If enabled, fetch from Twelve Data API and cache
3. Fallback to sector proxy (any stock in same sector/country)

Twelve Data Endpoints:
- /analyst_ratings/light (75 credits) - Analyst firm ratings
- /recommendations (100 credits) - Buy/Hold/Sell consensus
- /price_target (75 credits) - Price target estimates
"""

import os
import logging
import requests
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone, timedelta
from firebase_admin import firestore
from .base import BaseTool, ToolError

logger = logging.getLogger(__name__)


class MarketSentimentTool(BaseTool):
    """
    Retrieves market sentiment data for stocks.
    Includes analyst ratings, recommendations, and price targets.
    """
    
    # Credit costs per endpoint
    CREDITS = {
        'analyst_ratings_light': 75,
        'recommendations': 100,
        'price_target': 75,
        'full': 250
    }
    
    def __init__(self):
        """Initialize with Firestore client and configuration."""
        try:
            self.db = firestore.client()
            self.sentiment_collection = self.db.collection('market_sentiment')
            self.config_collection = self.db.collection('config')
            self.usage_collection = self.db.collection('api_usage')
            
            # Load configuration
            self._load_config()
            
            logger.info("MarketSentimentTool initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Firestore: {e}")
            self.db = None
            self.sentiment_collection = None
            self.enable_realtime_api = False
    
    def _load_config(self):
        """Load configuration from Firestore."""
        try:
            # Get API key from Firestore config
            api_keys_doc = self.config_collection.document('api_keys').get()
            if api_keys_doc.exists:
                self.api_key = api_keys_doc.to_dict().get('twelve_data_api_key')
            else:
                self.api_key = None
                logger.warning("No API key found in Firestore config")
            
            # Get settings
            settings_doc = self.config_collection.document('settings').get()
            if settings_doc.exists:
                settings = settings_doc.to_dict()
                self.enable_realtime_api = settings.get('enable_realtime_api_calls', False)
                self.cache_ttl_days = settings.get('sentiment_cache_ttl_days', 30)
                self.use_sector_fallback = settings.get('sentiment_use_fallback', True)
            else:
                self.enable_realtime_api = False
                self.cache_ttl_days = 30
                self.use_sector_fallback = True
                
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            self.api_key = None
            self.enable_realtime_api = False
            self.cache_ttl_days = 30
            self.use_sector_fallback = True
    
    @property
    def name(self) -> str:
        return "get_market_sentiment"
    
    @property
    def description(self) -> str:
        return """Retrieves market sentiment and analyst opinions for stocks.

Returns comprehensive sentiment data including:
- Analyst Ratings: Recent ratings from analyst firms (upgrades, downgrades, maintains)
- Recommendations: Buy/Hold/Sell consensus with rating scores
- Price Targets: Analyst price target estimates (high, low, average)

Use this tool to gauge professional analyst sentiment toward stocks you're considering.
Data is refreshed periodically and may include sector-level proxies when specific stock data is unavailable.

Parameters:
- symbol: Stock ticker symbol (required)
- exchange: Exchange code for international stocks (optional, e.g., "XLON", "XPAR")
- country: Country for fallback lookup (optional, e.g., "USA", "EU")
- sector: Sector for fallback lookup (optional, e.g., "technology")

Note: When exact stock data is unavailable, returns sector proxy data with a flag indicating this."""
    
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Stock ticker symbol (e.g., AAPL, MSFT)"
                },
                "exchange": {
                    "type": "string",
                    "description": "Exchange code for international stocks (e.g., XLON, XPAR, TSX)"
                },
                "country": {
                    "type": "string",
                    "enum": ["USA", "Canada", "EU", "India"],
                    "description": "Country for sector fallback lookup"
                },
                "sector": {
                    "type": "string",
                    "description": "Sector for fallback lookup (technology, healthcare, etc.)"
                }
            },
            "required": ["symbol"]
        }
    
    def execute(self, symbol: str, exchange: str = None, 
                country: str = None, sector: str = None) -> Dict[str, Any]:
        """
        Retrieve sentiment for a stock with tiered lookup strategy.
        
        Strategy:
        1. Check Firestore for this specific stock (< cache_ttl_days old)
        2. If enabled, fetch from Twelve Data API
        3. Fallback to sector proxy if available
        """
        if not self.sentiment_collection:
            return ToolError.create(
                code=ToolError.API_UNAVAILABLE,
                message="Firestore not available",
                user_message="Sentiment data temporarily unavailable"
            )
        
        symbol = symbol.upper()
        
        # Step 1: Check cache for this specific stock
        cached = self._get_cached_sentiment(symbol)
        if cached:
            logger.info(f"Cache hit for {symbol}")
            return self._format_response(cached, is_cached=True, is_proxy=False)
        
        # Step 2: Try real-time API if enabled
        if self.enable_realtime_api and self.api_key:
            logger.info(f"Attempting real-time fetch for {symbol}")
            fetched = self._fetch_realtime(symbol, exchange)
            if fetched:
                # Cache the result
                self._save_to_cache(fetched)
                return self._format_response(fetched, is_cached=False, is_proxy=False)
        
        # Step 3: Fallback to sector proxy
        if self.use_sector_fallback and country and sector:
            logger.info(f"Looking for sector proxy: {country}/{sector}")
            proxy = self._find_sector_proxy(country, sector, exclude_symbol=symbol)
            if proxy:
                return self._format_response(
                    proxy, 
                    is_cached=True, 
                    is_proxy=True,
                    proxy_message=f"Using {proxy.get('symbol')} as sector proxy for {sector} in {country}"
                )
        
        # No data available
        return ToolError.create(
            code=ToolError.DATA_PARSE_ERROR,
            message=f"No sentiment data available for {symbol}",
            user_message=f"Sentiment data not available for {symbol}. Try specifying country and sector for proxy data.",
            severity=ToolError.WARNING
        )
    
    def _get_cached_sentiment(self, symbol: str) -> Optional[Dict]:
        """
        Get cached sentiment if exists and not expired.
        """
        try:
            doc = self.sentiment_collection.document(symbol).get()
            
            if not doc.exists:
                return None
            
            data = doc.to_dict()
            fetched_at = data.get('fetched_at')
            
            if not fetched_at:
                return None
            
            # Parse fetched_at timestamp
            if isinstance(fetched_at, str):
                fetched_at = datetime.fromisoformat(fetched_at.replace('Z', '+00:00'))
            
            # Check if expired
            expiry = fetched_at + timedelta(days=self.cache_ttl_days)
            if datetime.now(timezone.utc) > expiry:
                logger.info(f"Cache expired for {symbol}")
                return None
            
            return data
            
        except Exception as e:
            logger.error(f"Error getting cached sentiment: {e}")
            return None
    
    def _fetch_realtime(self, symbol: str, exchange: str = None) -> Optional[Dict]:
        """
        Fetch sentiment from Twelve Data API in real-time.
        """
        try:
            # Check credit availability
            if not self._check_credits_available(self.CREDITS['full']):
                logger.warning("Insufficient credits for real-time fetch")
                return None
            
            # Build requests
            base_params = {'symbol': symbol, 'apikey': self.api_key}
            if exchange:
                base_params['exchange'] = exchange
            
            sentiment_data = {}
            credits_used = 0
            
            # Fetch recommendations (most useful, always try this)
            rec_data = self._api_call('/recommendations', base_params)
            if rec_data:
                sentiment_data['recommendations'] = self._parse_recommendations(rec_data)
                credits_used += self.CREDITS['recommendations']
            
            # Fetch analyst ratings
            ratings_data = self._api_call('/analyst_ratings/light', base_params)
            if ratings_data:
                sentiment_data['analyst_ratings'] = self._parse_analyst_ratings(ratings_data)
                credits_used += self.CREDITS['analyst_ratings_light']
            
            # Fetch price targets
            pt_data = self._api_call('/price_target', base_params)
            if pt_data:
                sentiment_data['price_target'] = self._parse_price_target(pt_data)
                credits_used += self.CREDITS['price_target']
            
            # Record credit usage
            if credits_used > 0:
                self._record_credit_usage(credits_used)
            
            # Check if we got any data
            if not any([
                sentiment_data.get('recommendations'),
                sentiment_data.get('analyst_ratings'),
                sentiment_data.get('price_target')
            ]):
                return None
            
            # Build document
            return {
                'symbol': symbol,
                'exchange': exchange or 'USA',
                'analyst_ratings': sentiment_data.get('analyst_ratings'),
                'recommendations': sentiment_data.get('recommendations'),
                'price_target': sentiment_data.get('price_target'),
                'fetched_at': datetime.now(timezone.utc).isoformat(),
                'data_source': 'Twelve Data',
                'fetch_mode': 'realtime'
            }
            
        except Exception as e:
            logger.error(f"Real-time fetch error: {e}")
            return None
    
    def _api_call(self, endpoint: str, params: Dict) -> Optional[Dict]:
        """Make API call to Twelve Data."""
        try:
            url = f"https://api.twelvedata.com{endpoint}"
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('status') == 'error':
                logger.warning(f"API error for {endpoint}: {data.get('message')}")
                return None
            
            return data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API call failed: {e}")
            return None
    
    def _parse_recommendations(self, data: Dict) -> Optional[Dict]:
        """Parse recommendations response."""
        if 'trends' not in data:
            return None
        
        trends = data.get('trends', {})
        current = trends.get('current_month', {})
        
        strong_buy = current.get('strong_buy', 0)
        buy = current.get('buy', 0)
        hold = current.get('hold', 0)
        sell = current.get('sell', 0)
        strong_sell = current.get('strong_sell', 0)
        
        total = strong_buy + buy + hold + sell + strong_sell
        
        if total > 0:
            score = (strong_buy * 5 + buy * 4 + hold * 3 + sell * 2 + strong_sell * 1) / total
            
            if score >= 4.5:
                consensus = 'Strong Buy'
            elif score >= 3.5:
                consensus = 'Buy'
            elif score >= 2.5:
                consensus = 'Hold'
            elif score >= 1.5:
                consensus = 'Sell'
            else:
                consensus = 'Strong Sell'
        else:
            score = None
            consensus = 'No Data'
        
        return {
            'current_month': current,
            'previous_month': trends.get('previous_month', {}),
            'rating_score': round(score, 2) if score else None,
            'consensus': consensus,
            'total_analysts': total
        }
    
    def _parse_analyst_ratings(self, data: Dict) -> Optional[Dict]:
        """Parse analyst ratings response."""
        if 'ratings' not in data:
            return None
        
        ratings = data.get('ratings', [])
        
        upgrades = sum(1 for r in ratings if r.get('rating_change') == 'Upgrade')
        downgrades = sum(1 for r in ratings if r.get('rating_change') == 'Downgrade')
        maintains = sum(1 for r in ratings if r.get('rating_change') == 'Maintains')
        
        recent = [{
            'date': r.get('date'),
            'firm': r.get('firm'),
            'rating_change': r.get('rating_change'),
            'rating_current': r.get('rating_current')
        } for r in ratings[:10]]
        
        return {
            'total_ratings': len(ratings),
            'upgrades': upgrades,
            'downgrades': downgrades,
            'maintains': maintains,
            'recent_ratings': recent
        }
    
    def _parse_price_target(self, data: Dict) -> Optional[Dict]:
        """Parse price target response."""
        if 'price_target' not in data:
            return None
        
        pt = data.get('price_target', {})
        
        current = pt.get('current')
        average = pt.get('average')
        
        if current and average:
            try:
                upside = ((average - current) / current) * 100
            except (TypeError, ZeroDivisionError):
                upside = None
        else:
            upside = None
        
        return {
            'high': pt.get('high'),
            'low': pt.get('low'),
            'average': average,
            'median': pt.get('median'),
            'current_price': current,
            'upside_percent': round(upside, 2) if upside else None
        }
    
    def _find_sector_proxy(self, country: str, sector: str, 
                          exclude_symbol: str = None) -> Optional[Dict]:
        """
        Find a proxy stock from the same sector/country.
        """
        try:
            query = self.sentiment_collection\
                .where('country', '==', country)\
                .where('sector', '==', sector)\
                .limit(5)
            
            docs = list(query.stream())
            
            for doc in docs:
                data = doc.to_dict()
                if data.get('symbol') != exclude_symbol:
                    # Check if not too old (use 90 days for proxy)
                    fetched_at = data.get('fetched_at')
                    if fetched_at:
                        if isinstance(fetched_at, str):
                            fetched_at = datetime.fromisoformat(fetched_at.replace('Z', '+00:00'))
                        
                        age = datetime.now(timezone.utc) - fetched_at
                        if age.days <= 90:
                            return data
            
            return None
            
        except Exception as e:
            logger.error(f"Error finding sector proxy: {e}")
            return None
    
    def _save_to_cache(self, data: Dict):
        """Save sentiment data to Firestore cache."""
        try:
            symbol = data.get('symbol')
            if symbol:
                self.sentiment_collection.document(symbol).set(data)
                logger.info(f"Cached sentiment for {symbol}")
        except Exception as e:
            logger.error(f"Error saving to cache: {e}")
    
    def _check_credits_available(self, credits_needed: int) -> bool:
        """Check if enough API credits are available."""
        try:
            doc = self.usage_collection.document('twelve_data').get()
            
            if not doc.exists:
                return True  # No usage tracking yet, allow
            
            usage = doc.to_dict()
            current_minute = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')
            
            if usage.get('current_minute_start') != current_minute:
                return True  # New minute, credits reset
            
            used = usage.get('current_minute_credits', 0)
            limit = usage.get('credits_per_minute_limit', 500)
            
            return (used + credits_needed) <= limit
            
        except Exception as e:
            logger.error(f"Error checking credits: {e}")
            return True  # Allow on error
    
    def _record_credit_usage(self, credits: int):
        """Record API credit usage in Firestore."""
        try:
            doc_ref = self.usage_collection.document('twelve_data')
            
            current_minute = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')
            
            doc = doc_ref.get()
            if doc.exists:
                usage = doc.to_dict()
                if usage.get('current_minute_start') == current_minute:
                    # Same minute, increment
                    usage['current_minute_credits'] = usage.get('current_minute_credits', 0) + credits
                else:
                    # New minute, reset
                    usage['current_minute_start'] = current_minute
                    usage['current_minute_credits'] = credits
                
                usage['total_credits_used'] = usage.get('total_credits_used', 0) + credits
                usage['last_updated'] = datetime.now(timezone.utc).isoformat()
            else:
                usage = {
                    'current_minute_start': current_minute,
                    'current_minute_credits': credits,
                    'total_credits_used': credits,
                    'credits_per_minute_limit': 500,
                    'last_updated': datetime.now(timezone.utc).isoformat()
                }
            
            doc_ref.set(usage)
            
        except Exception as e:
            logger.error(f"Error recording credit usage: {e}")
    
    def _format_response(self, data: Dict, is_cached: bool, 
                        is_proxy: bool, proxy_message: str = None) -> Dict[str, Any]:
        """Format the response for the agent."""
        response = {
            "success": True,
            "data": {
                "symbol": data.get('symbol'),
                "exchange": data.get('exchange'),
                "recommendations": data.get('recommendations'),
                "analyst_ratings": data.get('analyst_ratings'),
                "price_target": data.get('price_target'),
                "fetched_at": data.get('fetched_at'),
                "data_source": data.get('data_source', 'Twelve Data')
            },
            "metadata": {
                "is_cached": is_cached,
                "is_sector_proxy": is_proxy,
                "cache_ttl_days": self.cache_ttl_days
            }
        }
        
        if is_proxy and proxy_message:
            response["metadata"]["proxy_message"] = proxy_message
            response["data"]["note"] = "This is sector-level proxy data, not specific to the requested stock."
        
        return response