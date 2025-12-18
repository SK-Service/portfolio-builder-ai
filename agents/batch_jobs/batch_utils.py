"""
Shared utilities for batch jobs.
Handles rate limiting, progress tracking, credit management, API calls with retry.
Designed for Twelve Data API integration.
"""

import time
import json
import os
import re
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timezone
import yaml
import requests
from dotenv import load_dotenv

# Load environment variables from .env file (parent directory)
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

logger = logging.getLogger(__name__)


class RateLimitExceeded(Exception):
    """Exception raised when API rate limit is hit."""
    pass


class InsufficientCredits(Exception):
    """Exception raised when not enough API credits available."""
    pass


class BatchConfig:
    """Load and manage batch configuration."""
    
    def __init__(self, config_path: str = "./config.yaml"):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.mode = self.config['mode']
        self.stocks_per_sector = self.config['stock_counts'][self.mode]
        self.countries = self.config['countries']
        self.sectors = self.config['sectors']
        
        # Twelve Data API settings
        td_config = self.config['twelve_data']
        self.td_credits_per_minute = td_config['credits_per_minute_limit']
        self.td_batch_size = td_config['batch_size']
        self.td_batch_interval = td_config['batch_interval_seconds']
        self.td_max_retries = td_config['max_retries']
        self.td_timeout = td_config['timeout']
        self.td_enable_realtime = td_config['enable_realtime_api_calls']
        self.td_credits = td_config['credits']
        
        # Sentiment settings (if present)
        if 'sentiment' in self.config:
            sentiment_config = self.config['sentiment']
            self.sentiment_mode = sentiment_config.get('mode', 'recommendations_only')
            self.sentiment_auto_select = sentiment_config.get('auto_select', True)
            self.sentiment_input_file = sentiment_config.get('input_file', 'stock_universe_seeds.csv')
            self.sentiment_cache_ttl_days = sentiment_config.get('cache_ttl_days', 30)
            self.sentiment_use_fallback = sentiment_config.get('use_sector_fallback', True)
        
        # Output paths
        self.base_dir = Path(self.config['output']['base_dir'])
        self.universe_dir = Path(self.config['output']['stock_universe'])
        self.fundamentals_dir = Path(self.config['output']['fundamentals'])
        self.sentiment_dir = Path(self.config['output']['sentiment'])
        self.progress_dir = Path(self.config['output']['progress'])
        
        # Firestore collections
        self.firestore_collections = self.config['firestore']['collections']
        
        # Create directories
        self._create_directories()
    
    def _create_directories(self):
        """Create output directories if they don't exist."""
        for directory in [self.base_dir, self.universe_dir, self.fundamentals_dir,
                         self.sentiment_dir, self.progress_dir]:
            directory.mkdir(parents=True, exist_ok=True)
        logger.info(f"Output directories ready in: {self.base_dir}")
    
    def get_api_key(self) -> str:
        """Get Twelve Data API key from environment."""
        api_key = os.getenv('TWELVE_DATA_API_KEY')
        if not api_key:
            raise ValueError("TWELVE_DATA_API_KEY environment variable not set")
        return api_key


class CreditTracker:
    """
    Track API credit usage to stay within rate limits.
    Implements per-minute tracking with automatic wait when limit approached.
    """
    
    def __init__(self, progress_dir: Path, credits_per_minute: int = 610):
        self.credits_per_minute = credits_per_minute
        self.tracking_file = progress_dir / "credit_tracking.json"
        self.credits_used_this_minute = 0
        self.minute_start_time = datetime.now(timezone.utc)
        self.total_session_credits = 0
    
    def _reset_if_new_minute(self):
        """Reset minute counter if we're in a new minute."""
        now = datetime.now(timezone.utc)
        elapsed = (now - self.minute_start_time).total_seconds()
        
        if elapsed >= 60:
            logger.debug(f"New minute started, resetting credit counter (was {self.credits_used_this_minute})")
            self.credits_used_this_minute = 0
            self.minute_start_time = now
    
    def can_use_credits(self, credits_needed: int) -> bool:
        """Check if we have enough credits available this minute."""
        self._reset_if_new_minute()
        return (self.credits_used_this_minute + credits_needed) <= self.credits_per_minute
    
    def wait_for_credits(self, credits_needed: int):
        """Wait until enough credits are available (minute reset)."""
        self._reset_if_new_minute()
        
        if self.can_use_credits(credits_needed):
            return
        
        # Calculate wait time
        now = datetime.now(timezone.utc)
        elapsed = (now - self.minute_start_time).total_seconds()
        wait_seconds = max(0, 61 - elapsed)  # Wait until next minute + 1 second buffer
        
        if wait_seconds > 0:
            logger.info(f"Credit limit approaching! Used: {self.credits_used_this_minute}/{self.credits_per_minute}")
            logger.info(f"Waiting {wait_seconds:.0f} seconds for rate limit reset...")
            print(f"\n  ⏳ Rate limit: Waiting {wait_seconds:.0f}s for credit reset...")
            time.sleep(wait_seconds)
        
        # Reset after waiting
        self.credits_used_this_minute = 0
        self.minute_start_time = datetime.now(timezone.utc)
    
    def use_credits(self, credits: int):
        """Record credit usage."""
        self._reset_if_new_minute()
        self.credits_used_this_minute += credits
        self.total_session_credits += credits
        logger.debug(f"Used {credits} credits. Minute: {self.credits_used_this_minute}/{self.credits_per_minute}")
    
    def get_available_credits(self) -> int:
        """Get remaining credits for this minute."""
        self._reset_if_new_minute()
        return self.credits_per_minute - self.credits_used_this_minute
    
    def get_summary(self) -> str:
        """Get credit usage summary."""
        return (f"Credits - This minute: {self.credits_used_this_minute}/{self.credits_per_minute}, "
                f"Session total: {self.total_session_credits}")


class ProgressTracker:
    """Track and resume batch job progress."""
    
    def __init__(self, job_name: str, progress_dir: Path):
        self.job_name = job_name
        self.progress_file = progress_dir / f"{job_name}_progress.json"
        self.progress = self._load_progress()
    
    def _load_progress(self) -> Dict:
        """Load existing progress or create new."""
        if self.progress_file.exists():
            with open(self.progress_file, 'r') as f:
                return json.load(f)
        return {
            'job_name': self.job_name,
            'started_at': datetime.now(timezone.utc).isoformat(),
            'completed': 0,
            'total': 0,
            'processed_items': [],
            'failed_items': [],
            'rate_limit_reached': False,
            'last_updated': None
        }
    
    def set_total(self, total: int):
        """Set total items to process."""
        self.progress['total'] = total
        self._save()
    
    def mark_completed(self, item_id: str):
        """Mark item as completed."""
        if item_id not in self.progress['processed_items']:
            self.progress['processed_items'].append(item_id)
            self.progress['completed'] = len(self.progress['processed_items'])
            self.progress['last_updated'] = datetime.now(timezone.utc).isoformat()
            self._save()
    
    def mark_failed(self, item_id: str, error: str, error_type: str = "unknown"):
        """Mark item as failed with error type."""
        existing = [f for f in self.progress['failed_items'] if f['item_id'] == item_id]
        if not existing:
            self.progress['failed_items'].append({
                'item_id': item_id,
                'error': error,
                'error_type': error_type,
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
            self._save()
    
    def mark_rate_limit_reached(self):
        """Mark that rate limit was reached."""
        self.progress['rate_limit_reached'] = True
        self.progress['rate_limit_timestamp'] = datetime.now(timezone.utc).isoformat()
        self._save()
    
    def is_completed(self, item_id: str) -> bool:
        """Check if item already processed."""
        return item_id in self.progress['processed_items']
    
    def get_remaining_count(self) -> int:
        """Get count of remaining items."""
        return self.progress['total'] - self.progress['completed']
    
    def get_failed_by_type(self, error_type: str) -> list:
        """Get failed items of specific type."""
        return [f for f in self.progress['failed_items'] if f.get('error_type') == error_type]
    
    def _save(self):
        """Save progress to file."""
        with open(self.progress_file, 'w') as f:
            json.dump(self.progress, f, indent=2)
    
    def get_summary(self) -> str:
        """Get progress summary."""
        rate_limit_failures = len(self.get_failed_by_type('rate_limit'))
        network_failures = len(self.get_failed_by_type('network'))
        api_failures = len(self.get_failed_by_type('api_error'))
        no_data_failures = len(self.get_failed_by_type('no_data'))
        other_failures = len([f for f in self.progress['failed_items'] 
                             if f.get('error_type') not in ['rate_limit', 'network', 'api_error', 'no_data']])
        
        summary = (f"{self.job_name}: {self.progress['completed']}/{self.progress['total']} completed, "
                  f"{self.get_remaining_count()} remaining")
        
        if self.progress['failed_items']:
            summary += f"\n  Failures: {no_data_failures} no_data, {api_failures} api, {network_failures} network, {other_failures} other"
        
        return summary
    
    def print_startup_summary(self):
        """Print summary when script starts."""
        print("\n" + "="*70)
        print("PROGRESS SUMMARY")
        print("="*70)
        print(f"Total items: {self.progress['total']}")
        print(f"Completed: {self.progress['completed']}")
        print(f"Remaining: {self.get_remaining_count()}")
        
        if self.progress['failed_items']:
            print(f"Failed (will retry): {len(self.progress['failed_items'])}")
            rate_limit_count = len(self.get_failed_by_type('rate_limit'))
            if rate_limit_count > 0:
                print(f"  - Rate limit failures: {rate_limit_count}")
        
        if self.progress.get('rate_limit_reached'):
            print(f"\nLast run hit rate limit at: {self.progress.get('rate_limit_timestamp')}")
        
        print("="*70 + "\n")


class TwelveDataClient:
    """
    Client for Twelve Data API with batch support.
    Uses the /batch endpoint for efficient multi-request calls.
    Includes JSON sanitization for malformed responses.
    """
    
    BASE_URL = "https://api.twelvedata.com"
    BATCH_URL = f"{BASE_URL}/batch"
    
    def __init__(self, api_key: str, timeout: int = 60):
        self.api_key = api_key
        self.timeout = timeout
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"apikey {api_key}"
        }
    
    def build_statistics_url(self, symbol: str, exchange: str = None) -> str:
        """
        Build URL for statistics endpoint.
        Uses mic_code for international stocks (not exchange).
        """
        if exchange and exchange.strip():
            # Use mic_code parameter for international stocks
            return f"/statistics?symbol={symbol}&mic_code={exchange}&apikey={self.api_key}"
        return f"/statistics?symbol={symbol}&apikey={self.api_key}"
    
    def sanitize_json_response(self, raw_text: str) -> str:
        """
        Sanitize malformed JSON from Twelve Data API.
        
        The API sometimes returns malformed JSON like:
        - }}}null} instead of }}}
        - }}null} instead of }}
        
        This fixes those issues before parsing.
        """
        if not raw_text:
            return raw_text
        
        original = raw_text
        
        # Fix various malformed null insertions
        sanitized = re.sub(r'\}null\}', '}}', raw_text)
        sanitized = re.sub(r'\}\}null\}', '}}}', sanitized)
        sanitized = re.sub(r'\}\}\}null\}', '}}}}', sanitized)
        sanitized = re.sub(r'null\}', '}', sanitized)
        
        if original != sanitized:
            logger.warning("Sanitized malformed JSON response (removed erroneous null insertions)")
        
        return sanitized
    
    def execute_batch(self, requests_dict: Dict[str, Dict]) -> Optional[Dict]:
        """
        Execute batch API call.
        
        Args:
            requests_dict: Dictionary of request IDs to URL configs
                          e.g., {"req_1": {"url": "/statistics?symbol=AAPL&apikey=xxx"}}
        
        Returns:
            Response dictionary or None if failed
        """
        result, _, _ = self.execute_batch_with_raw(requests_dict)
        return result
    
    def execute_batch_with_raw(self, requests_dict: Dict[str, Dict]) -> Tuple[Optional[Dict], Optional[str], bool]:
        """
        Execute batch API call and return both parsed response and raw text.
        
        Args:
            requests_dict: Dictionary of request IDs to URL configs
                          e.g., {"req_1": {"url": "/statistics?symbol=AAPL&apikey=xxx"}}
        
        Returns:
            Tuple of (parsed_response, raw_response_text, was_sanitized)
            - parsed_response: Response dictionary or None if failed
            - raw_response_text: Raw response string for error logging
            - was_sanitized: True if JSON sanitization was applied
        """
        raw_text = None
        was_sanitized = False
        
        try:
            logger.debug(f"Executing batch with {len(requests_dict)} requests")
            
            # Use stream=False and explicit encoding handling
            response = requests.post(
                self.BATCH_URL,
                headers=self.headers,
                json=requests_dict,
                timeout=self.timeout,
                stream=False
            )
            response.raise_for_status()
            
            # Force UTF-8 encoding for response
            response.encoding = 'utf-8'
            raw_text = response.text
            
            logger.debug(f"Response length: {len(raw_text)} characters")
            
            # Try direct JSON parsing first
            try:
                data = json.loads(raw_text)
                logger.debug("Direct JSON parsing successful")
            except json.JSONDecodeError as e:
                logger.warning(f"Direct JSON parsing failed at position {e.pos}: {e.msg}")
                
                # Log context around the error position
                error_pos = e.pos
                start = max(0, error_pos - 50)
                end = min(len(raw_text), error_pos + 50)
                logger.warning(f"Context around error: ...{raw_text[start:end]}...")
                
                # Attempt sanitization
                sanitized_text = self.sanitize_json_response(raw_text)
                was_sanitized = (sanitized_text != raw_text)
                
                try:
                    data = json.loads(sanitized_text)
                    logger.info("JSON parsing successful after sanitization")
                except json.JSONDecodeError as e2:
                    logger.error(f"JSON parsing failed even after sanitization: {e2}")
                    logger.error(f"Raw response (first 1000 chars): {raw_text[:1000]}")
                    logger.error(f"Raw response (last 500 chars): {raw_text[-500:]}")
                    
                    # Save failed response for debugging
                    debug_file = Path("batch_output/debug_failed_response.txt")
                    debug_file.parent.mkdir(parents=True, exist_ok=True)
                    with open(debug_file, 'w', encoding='utf-8') as f:
                        f.write(raw_text)
                    logger.error(f"Full response saved to {debug_file}")
                    
                    return None, raw_text, was_sanitized
            
            # If data is a string (shouldn't happen but handle it)
            if isinstance(data, str):
                logger.warning("Response returned as string, converting to object...")
                sanitized = self.sanitize_json_response(data)
                was_sanitized = (sanitized != data)
                try:
                    data = json.loads(sanitized)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse string response: {e}")
                    return None, raw_text, was_sanitized
            
            # Check for top-level errors
            if isinstance(data, dict) and data.get('status') == 'error':
                error_msg = data.get('message', 'Unknown error')
                logger.error(f"Batch API error: {error_msg}")
                
                if 'rate limit' in error_msg.lower() or 'limit exceeded' in error_msg.lower():
                    raise RateLimitExceeded(error_msg)
                
                return None, raw_text, was_sanitized
            
            return data, raw_text, was_sanitized
            
        except requests.exceptions.Timeout as e:
            logger.error(f"Batch request timeout: {e}")
            return None, raw_text, was_sanitized
        except requests.exceptions.RequestException as e:
            logger.error(f"Batch request failed: {e}")
            return None, raw_text, was_sanitized
    
    def execute_single(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """
        Execute single API call (for real-time tool use).
        """
        try:
            url = f"{self.BASE_URL}{endpoint}"
            params = params or {}
            params['apikey'] = self.api_key
            
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            # Handle potential string response
            try:
                data = response.json()
            except json.JSONDecodeError:
                sanitized = self.sanitize_json_response(response.text)
                data = json.loads(sanitized)
            
            if isinstance(data, dict) and data.get('status') == 'error':
                error_msg = data.get('message', 'Unknown error')
                logger.error(f"API error: {error_msg}")
                
                if 'rate limit' in error_msg.lower():
                    raise RateLimitExceeded(error_msg)
                
                return None
            
            return data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            return None


def save_json(data: Any, filepath: Path, pretty: bool = True):
    """Save data to JSON file."""
    with open(filepath, 'w') as f:
        if pretty:
            json.dump(data, f, indent=2, default=str)
        else:
            json.dump(data, f, default=str)
    logger.debug(f"Saved: {filepath}")


def load_json(filepath: Path) -> Optional[Any]:
    """Load data from JSON file."""
    if not filepath.exists():
        return None
    with open(filepath, 'r') as f:
        return json.load(f)


def setup_logging(config: BatchConfig):
    """Configure logging for batch jobs."""
    log_file = config.base_dir / config.config['logging']['file']
    log_level = getattr(logging, config.config['logging']['level'])
    
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    logger.info(f"Logging configured: {log_file}")


def load_stocks_from_csv(csv_path: str) -> List[Dict[str, str]]:
    """
    Load stocks from CSV file.
    """
    import csv
    
    stocks = []
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            stocks.append({
                'country': row['country'],
                'sector': row['sector'],
                'symbol': row['symbol'],
                'name': row['name'],
                'market_cap_tier': row['market_cap_tier'],
                'exchange': row.get('exchange', '')  # May be empty for USA stocks
            })
    
    return stocks


def prioritize_stocks(stocks: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """Sort stocks by priority: large cap first, then mid, then small."""
    tier_order = {'large': 0, 'mid': 1, 'small': 2}
    return sorted(stocks, key=lambda s: tier_order.get(s.get('market_cap_tier', 'small'), 3))


def select_representative_stocks(stocks: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """Select 1 representative stock per sector per country (preferring large cap)."""
    from collections import defaultdict
    groups = defaultdict(list)
    
    for stock in stocks:
        key = (stock['country'], stock['sector'])
        groups[key].append(stock)
    
    representatives = []
    for key, group_stocks in groups.items():
        sorted_stocks = prioritize_stocks(group_stocks)
        if sorted_stocks:
            representatives.append(sorted_stocks[0])
            logger.debug(f"Selected {sorted_stocks[0]['symbol']} for {key[0]}/{key[1]}")
    
    return representatives


def chunk_list(lst: List, chunk_size: int) -> List[List]:
    """Split list into chunks of specified size."""
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]