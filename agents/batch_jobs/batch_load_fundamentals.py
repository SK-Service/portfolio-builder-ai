"""
Batch job to fetch stock fundamentals from Twelve Data API.
Uses the /batch endpoint with /statistics requests for efficient processing.

Key features:
1. Uses mic_code (not exchange) for international stocks
2. Handles string responses and sanitizes malformed JSON
3. Proper credit tracking with 1-minute wait when limit approached
4. Detailed error logging with raw response capture
5. Comprehensive summary at end of job

Credit cost: 50 credits per symbol
"""

import os
import json
import logging
import time
from datetime import datetime, timezone
from typing import List, Dict, Tuple, Optional
from pathlib import Path

from batch_utils import (
    BatchConfig, ProgressTracker, CreditTracker, TwelveDataClient,
    save_json, load_json, setup_logging, prioritize_stocks, chunk_list,
    RateLimitExceeded
)

logger = logging.getLogger(__name__)

# Credit cost for statistics endpoint
STATISTICS_CREDITS = 50


# Global tracking for detailed summary
class JobStats:
    """Track detailed statistics for the job summary."""
    def __init__(self):
        self.total_processed = 0
        self.successful = []  # List of symbols
        self.failed_parse = []  # List of (symbol, reason, raw_response_snippet)
        self.failed_no_data = []  # List of (symbol, reason)
        self.failed_api_error = []  # List of (symbol, error_message)
        self.failed_batch = []  # List of symbols from failed batches
        self.sanitized_responses = []  # List of symbols where JSON was sanitized
        self.retries_needed = 0
    
    def add_success(self, symbol: str):
        self.successful.append(symbol)
        self.total_processed += 1
    
    def add_failed_parse(self, symbol: str, reason: str, raw_snippet: str = None):
        self.failed_parse.append((symbol, reason, raw_snippet))
        self.total_processed += 1
    
    def add_failed_no_data(self, symbol: str, reason: str):
        self.failed_no_data.append((symbol, reason))
        self.total_processed += 1
    
    def add_failed_api_error(self, symbol: str, error_msg: str):
        self.failed_api_error.append((symbol, error_msg))
        self.total_processed += 1
    
    def add_failed_batch(self, symbol: str):
        self.failed_batch.append(symbol)
        self.total_processed += 1
    
    def add_sanitized(self, symbol: str):
        self.sanitized_responses.append(symbol)
    
    def increment_retries(self):
        self.retries_needed += 1
    
    def get_all_failed(self) -> List[str]:
        """Get all failed symbols."""
        failed = []
        failed.extend([s for s, _, _ in self.failed_parse])
        failed.extend([s for s, _ in self.failed_no_data])
        failed.extend([s for s, _ in self.failed_api_error])
        failed.extend(self.failed_batch)
        return failed
    
    def print_summary(self, elapsed_minutes: float, output_dir: Path):
        """Print comprehensive summary."""
        total_failed = len(self.get_all_failed())
        
        print("\n" + "="*70)
        print("FUNDAMENTALS JOB - DETAILED SUMMARY")
        print("="*70)
        
        # Section 1: Overview
        print("\n[1] OVERVIEW")
        print(f"    Total stocks processed: {self.total_processed}")
        print(f"    Successfully saved: {len(self.successful)}")
        print(f"    Failed: {total_failed}")
        print(f"    Elapsed time: {elapsed_minutes:.1f} minutes")
        print(f"    Output directory: {output_dir}")
        
        # Section 2: Success rate
        if self.total_processed > 0:
            success_rate = (len(self.successful) / self.total_processed) * 100
            print(f"    Success rate: {success_rate:.1f}%")
        
        # Section 3: Bad responses handled
        print("\n[2] BAD RESPONSES (handled by sanitization rules)")
        if self.sanitized_responses:
            print(f"    Count: {len(self.sanitized_responses)}")
            print(f"    Stocks: {', '.join(self.sanitized_responses[:20])}")
            if len(self.sanitized_responses) > 20:
                print(f"    ... and {len(self.sanitized_responses) - 20} more")
        else:
            print("    None - all responses were clean JSON")
        
        # Section 4: Failed stocks - detailed breakdown
        print("\n[3] FAILED STOCKS - BREAKDOWN")
        
        # 4a: Parse failures
        if self.failed_parse:
            print(f"\n    [3a] Parse Failures ({len(self.failed_parse)}):")
            for symbol, reason, snippet in self.failed_parse[:10]:
                print(f"         - {symbol}: {reason}")
                if snippet:
                    # Log snippet to file, show truncated in console
                    print(f"           Response snippet: {snippet[:100]}...")
            if len(self.failed_parse) > 10:
                print(f"         ... and {len(self.failed_parse) - 10} more")
        
        # 4b: No meaningful data
        if self.failed_no_data:
            print(f"\n    [3b] No Meaningful Data ({len(self.failed_no_data)}):")
            for symbol, reason in self.failed_no_data[:10]:
                print(f"         - {symbol}: {reason}")
            if len(self.failed_no_data) > 10:
                print(f"         ... and {len(self.failed_no_data) - 10} more")
        
        # 4c: API errors
        if self.failed_api_error:
            print(f"\n    [3c] API Errors ({len(self.failed_api_error)}):")
            for symbol, error_msg in self.failed_api_error[:10]:
                print(f"         - {symbol}: {error_msg}")
            if len(self.failed_api_error) > 10:
                print(f"         ... and {len(self.failed_api_error) - 10} more")
        
        # 4d: Batch failures
        if self.failed_batch:
            print(f"\n    [3d] Batch Failures - retries exhausted ({len(self.failed_batch)}):")
            print(f"         Stocks: {', '.join(self.failed_batch[:20])}")
            if len(self.failed_batch) > 20:
                print(f"         ... and {len(self.failed_batch) - 20} more")
        
        # Section 5: Complete list of failed stocks
        all_failed = self.get_all_failed()
        if all_failed:
            print(f"\n[4] COMPLETE LIST OF FAILED STOCKS ({len(all_failed)}):")
            # Print in rows of 10
            for i in range(0, len(all_failed), 10):
                print(f"    {', '.join(all_failed[i:i+10])}")
        else:
            print("\n[4] NO FAILED STOCKS - All processed successfully!")
        
        # Section 6: Retry statistics
        print(f"\n[5] RETRY STATISTICS")
        print(f"    Batches that needed retry: {self.retries_needed}")
        
        print("\n" + "="*70)
    
    def log_to_file(self, log_path: Path):
        """Log detailed failure information to a separate file."""
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write("FUNDAMENTALS JOB - DETAILED FAILURE LOG\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n")
            f.write("="*70 + "\n\n")
            
            if self.failed_parse:
                f.write("PARSE FAILURES:\n")
                f.write("-"*50 + "\n")
                for symbol, reason, snippet in self.failed_parse:
                    f.write(f"\nSymbol: {symbol}\n")
                    f.write(f"Reason: {reason}\n")
                    if snippet:
                        f.write(f"Raw Response:\n{snippet}\n")
                f.write("\n")
            
            if self.failed_no_data:
                f.write("NO MEANINGFUL DATA:\n")
                f.write("-"*50 + "\n")
                for symbol, reason in self.failed_no_data:
                    f.write(f"{symbol}: {reason}\n")
                f.write("\n")
            
            if self.failed_api_error:
                f.write("API ERRORS:\n")
                f.write("-"*50 + "\n")
                for symbol, error_msg in self.failed_api_error:
                    f.write(f"{symbol}: {error_msg}\n")
                f.write("\n")
            
            if self.failed_batch:
                f.write("BATCH FAILURES (retries exhausted):\n")
                f.write("-"*50 + "\n")
                f.write(", ".join(self.failed_batch) + "\n")


# Global job stats instance
job_stats = JobStats()


def collect_stocks_from_universe(universe_dir: Path) -> List[Dict[str, str]]:
    """
    Collect all stocks from universe JSON files.
    """
    all_stocks = []
    
    for json_file in universe_dir.glob("*.json"):
        data = load_json(json_file)
        if data and 'stocks' in data:
            country = data.get('country', '')
            sector = data.get('sector', '')
            
            for stock in data['stocks']:
                all_stocks.append({
                    'symbol': stock['symbol'],
                    'name': stock['name'],
                    'exchange': stock.get('exchange', ''),
                    'market_cap_tier': stock.get('market_cap_tier', 'unknown'),
                    'country': country,
                    'sector': sector
                })
    
    logger.info(f"Collected {len(all_stocks)} stocks from universe files")
    return all_stocks


def parse_statistics_response(symbol: str, exchange: str, name: str, 
                              country: str, sector: str, stats_data: Dict,
                              raw_response_str: str = None) -> Optional[Dict]:
    """
    Parse Twelve Data statistics response into our standard format.
    
    Args:
        symbol: Stock symbol
        exchange: Exchange/MIC code
        name: Company name
        country: Country
        sector: Sector
        stats_data: Parsed statistics data
        raw_response_str: Raw response string for error logging
    
    Returns:
        Parsed fundamentals dict or None if parsing failed
    """
    
    def safe_float(value, default=None):
        """Safely convert value to float."""
        try:
            if value is None or value == 'None' or value == '':
                return default
            return float(value)
        except (ValueError, TypeError):
            return default
    
    # Check if we have valid statistics data
    if not stats_data:
        logger.warning(f"{symbol}: Empty stats_data")
        logger.warning(f"{symbol}: RAW RESPONSE: {raw_response_str[:500] if raw_response_str else 'N/A'}")
        job_stats.add_failed_parse(symbol, "Empty stats_data", raw_response_str[:1000] if raw_response_str else None)
        return None
    
    # Validate stats_data is a dict
    if not isinstance(stats_data, dict):
        logger.warning(f"{symbol}: stats_data is not a dict, type: {type(stats_data)}")
        logger.warning(f"{symbol}: RAW RESPONSE: {raw_response_str[:500] if raw_response_str else 'N/A'}")
        job_stats.add_failed_parse(symbol, f"stats_data is {type(stats_data)}, not dict", 
                                   raw_response_str[:1000] if raw_response_str else None)
        return None
    
    logger.debug(f"{symbol}: stats_data keys: {list(stats_data.keys())}")
    
    # Handle case where stats_data might be the response wrapper
    if 'statistics' not in stats_data:
        # Check if this is a nested response structure
        if 'response' in stats_data and isinstance(stats_data['response'], dict):
            logger.debug(f"{symbol}: Unwrapping 'response' layer")
            stats_data = stats_data['response']
        
        if 'statistics' not in stats_data:
            available_keys = list(stats_data.keys())
            logger.warning(f"{symbol}: No 'statistics' key in response. Available keys: {available_keys}")
            logger.warning(f"{symbol}: RAW RESPONSE: {raw_response_str[:500] if raw_response_str else 'N/A'}")
            job_stats.add_failed_parse(symbol, f"No 'statistics' key. Keys: {available_keys}", 
                                       raw_response_str[:1000] if raw_response_str else None)
            return None
    
    statistics = stats_data.get('statistics', {})
    
    # Check if statistics is empty
    if not statistics:
        logger.warning(f"{symbol}: 'statistics' object is empty")
        logger.warning(f"{symbol}: RAW RESPONSE: {raw_response_str[:500] if raw_response_str else 'N/A'}")
        job_stats.add_failed_parse(symbol, "'statistics' object is empty", 
                                   raw_response_str[:1000] if raw_response_str else None)
        return None
    
    logger.debug(f"{symbol}: statistics keys: {list(statistics.keys())}")
    
    meta = stats_data.get('meta', {})
    valuations = statistics.get('valuations_metrics', {})
    financials = statistics.get('financials', {})
    stock_stats = statistics.get('stock_statistics', {})
    price_summary = statistics.get('stock_price_summary', {})
    dividends = statistics.get('dividends_and_splits', {})
    
    # Build fundamentals document
    fundamentals = {
        # Identity
        'symbol': symbol,
        'name': name or meta.get('name', ''),
        'exchange': exchange if exchange else 'USA',
        'currency': meta.get('currency', ''),  # e.g., USD, INR, EUR, CAD
        'country': country,
        'sector': sector,
        
        # Valuation metrics
        'pe_ratio': safe_float(valuations.get('trailing_pe')),
        'forward_pe': safe_float(valuations.get('forward_pe')),
        'peg_ratio': safe_float(valuations.get('peg_ratio')),
        'price_to_book': safe_float(valuations.get('price_to_book_mrq')),
        'price_to_sales': safe_float(valuations.get('price_to_sales_ttm')),
        'ev_to_revenue': safe_float(valuations.get('enterprise_to_revenue')),
        'ev_to_ebitda': safe_float(valuations.get('enterprise_to_ebitda')),
        'market_cap': safe_float(valuations.get('market_capitalization')),
        'enterprise_value': safe_float(valuations.get('enterprise_value')),
        
        # Profitability metrics
        'profit_margin': safe_float(financials.get('profit_margin')),
        'operating_margin': safe_float(financials.get('operating_margin')),
        'gross_margin': safe_float(financials.get('gross_margin')),
        'return_on_assets': safe_float(financials.get('return_on_assets_ttm')),
        'return_on_equity': safe_float(financials.get('return_on_equity_ttm')),
        
        # Income statement metrics
        'revenue_ttm': safe_float(financials.get('income_statement', {}).get('revenue_ttm')),
        'revenue_per_share': safe_float(financials.get('income_statement', {}).get('revenue_per_share_ttm')),
        'quarterly_revenue_growth': safe_float(financials.get('income_statement', {}).get('quarterly_revenue_growth')),
        'ebitda': safe_float(financials.get('income_statement', {}).get('ebitda')),
        'diluted_eps': safe_float(financials.get('income_statement', {}).get('diluted_eps_ttm')),
        'quarterly_earnings_growth': safe_float(financials.get('income_statement', {}).get('quarterly_earnings_growth_yoy')),
        
        # Balance sheet metrics
        'total_cash': safe_float(financials.get('balance_sheet', {}).get('total_cash_mrq')),
        'total_debt': safe_float(financials.get('balance_sheet', {}).get('total_debt_mrq')),
        'debt_to_equity': safe_float(financials.get('balance_sheet', {}).get('total_debt_to_equity_mrq')),
        'current_ratio': safe_float(financials.get('balance_sheet', {}).get('current_ratio_mrq')),
        'book_value_per_share': safe_float(financials.get('balance_sheet', {}).get('book_value_per_share_mrq')),
        
        # Cash flow
        'operating_cash_flow': safe_float(financials.get('cash_flow', {}).get('operating_cash_flow_ttm')),
        'free_cash_flow': safe_float(financials.get('cash_flow', {}).get('levered_free_cash_flow_ttm')),
        
        # Stock statistics
        'shares_outstanding': safe_float(stock_stats.get('shares_outstanding')),
        'float_shares': safe_float(stock_stats.get('float_shares')),
        'avg_volume_10d': safe_float(stock_stats.get('avg_10_volume')),
        'avg_volume_90d': safe_float(stock_stats.get('avg_90_volume')),
        'shares_short': safe_float(stock_stats.get('shares_short')),
        'short_ratio': safe_float(stock_stats.get('short_ratio')),
        'percent_insiders': safe_float(stock_stats.get('percent_held_by_insiders')),
        'percent_institutions': safe_float(stock_stats.get('percent_held_by_institutions')),
        
        # Price summary / Technical
        'week_52_low': safe_float(price_summary.get('fifty_two_week_low')),
        'week_52_high': safe_float(price_summary.get('fifty_two_week_high')),
        'week_52_change': safe_float(price_summary.get('fifty_two_week_change')),
        'beta': safe_float(price_summary.get('beta')),
        'day_50_ma': safe_float(price_summary.get('day_50_ma')),
        'day_200_ma': safe_float(price_summary.get('day_200_ma')),
        
        # Dividends
        'dividend_yield': safe_float(dividends.get('forward_annual_dividend_yield')),
        'trailing_dividend_yield': safe_float(dividends.get('trailing_annual_dividend_yield')),
        'dividend_rate': safe_float(dividends.get('forward_annual_dividend_rate')),
        'payout_ratio': safe_float(dividends.get('payout_ratio')),
        'dividend_date': dividends.get('dividend_date'),
        'ex_dividend_date': dividends.get('ex_dividend_date'),
        
        # Metadata
        'last_updated': datetime.now(timezone.utc).isoformat(),
        'data_source': 'Twelve Data'
    }
    
    # Log extracted key metrics for debugging
    logger.debug(f"{symbol}: pe_ratio={fundamentals['pe_ratio']}, market_cap={fundamentals['market_cap']}, "
                 f"profit_margin={fundamentals['profit_margin']}, revenue_ttm={fundamentals['revenue_ttm']}")
    
    # Check if we have any meaningful data
    has_data = any([
        fundamentals['pe_ratio'] is not None,
        fundamentals['market_cap'] is not None,
        fundamentals['profit_margin'] is not None,
        fundamentals['revenue_ttm'] is not None
    ])
    
    if not has_data:
        reason = (f"All key metrics None - pe:{fundamentals['pe_ratio']}, "
                  f"mktcap:{fundamentals['market_cap']}, margin:{fundamentals['profit_margin']}, "
                  f"rev:{fundamentals['revenue_ttm']}")
        logger.warning(f"{symbol}: No meaningful data - {reason}")
        job_stats.add_failed_no_data(symbol, reason)
        return None
    
    return fundamentals


def process_batch(batch_stocks: List[Dict], client: TwelveDataClient, 
                  fundamentals_dir: Path, tracker: ProgressTracker) -> Tuple[int, int, bool]:
    """
    Process a batch of stocks using the /batch endpoint.
    
    Returns:
        Tuple of (success_count, failure_count, batch_failed)
        batch_failed=True means the entire batch request failed OR rate limit hit (should retry)
    """
    success_count = 0
    failure_count = 0
    rate_limit_in_batch = False  # Track if any request in batch hit rate limit
    
    # Build batch request
    requests_dict = {}
    stock_mapping = {}
    
    for idx, stock in enumerate(batch_stocks):
        req_id = f"req_{idx + 1}"
        url = client.build_statistics_url(stock['symbol'], stock.get('exchange', ''))
        requests_dict[req_id] = {"url": url}
        stock_mapping[req_id] = stock
    
    logger.debug(f"Batch request URLs: {[r['url'].split('apikey=')[0] for r in requests_dict.values()]}")
    
    # Execute batch and get both parsed response and raw text
    response, raw_response_text, was_sanitized = client.execute_batch_with_raw(requests_dict)
    
    if response is None:
        # Log the failed raw response
        if raw_response_text:
            logger.error(f"Batch failed - RAW RESPONSE (first 2000 chars): {raw_response_text[:2000]}")
        else:
            logger.error("Batch failed - No response received")
        return 0, 0, True  # Signal retry needed
    
    # Track if sanitization was needed
    if was_sanitized:
        for stock in batch_stocks:
            job_stats.add_sanitized(stock['symbol'])
    
    # Get the data portion of response
    if 'data' in response and isinstance(response['data'], dict):
        batch_data = response['data']
    else:
        batch_data = response
    
    # Process each response
    for req_id, stock in stock_mapping.items():
        symbol = stock['symbol']
        
        # Skip if already completed
        if tracker.is_completed(symbol):
            success_count += 1
            continue
        
        # Get response for this request
        req_response = batch_data.get(req_id, {})
        
        # Extract raw response for this specific request for logging
        raw_req_response = None
        try:
            raw_req_response = json.dumps(req_response, indent=2)[:2000] if req_response else None
        except:
            raw_req_response = str(req_response)[:2000] if req_response else None
        
        if not req_response:
            logger.warning(f"{symbol}: No response for {req_id}")
            logger.warning(f"{symbol}: Full batch response keys: {list(batch_data.keys())}")
            job_stats.add_failed_parse(symbol, f"No response for {req_id}", raw_response_text[:1000] if raw_response_text else None)
            tracker.mark_failed(symbol, "No response in batch", "no_data")
            failure_count += 1
            continue
        
        # Check for request-level error
        if isinstance(req_response, dict):
            if req_response.get('status') == 'error':
                error_msg = req_response.get('message', 'Unknown error')
                error_code = req_response.get('code', 'N/A')
                logger.warning(f"{symbol}: API error - {error_msg} (code: {error_code})")
                job_stats.add_failed_api_error(symbol, f"{error_msg} (code: {error_code})")
                tracker.mark_failed(symbol, error_msg, "api_error")
                failure_count += 1
                continue
            
            # Handle nested response structure
            if req_response.get('status') == 'success' and 'response' in req_response:
                stats_data = req_response['response']
                
                # CRITICAL: Check if the nested response is actually a rate limit error
                # Twelve Data returns: {"status": "success", "response": {"code": 429, "message": "...", "status": "error"}}
                if isinstance(stats_data, dict) and stats_data.get('status') == 'error':
                    error_code = stats_data.get('code', 'N/A')
                    error_msg = stats_data.get('message', 'Unknown error')
                    
                    # Check for rate limit (429) - this should trigger batch retry
                    if error_code == 429 or 'rate limit' in str(error_msg).lower() or 'api credits' in str(error_msg).lower():
                        logger.warning(f"{symbol}: Per-request rate limit hit (code {error_code})")
                        # Signal that this batch needs retry due to rate limiting
                        rate_limit_in_batch = True
                        failure_count += 1
                        continue
                    else:
                        logger.warning(f"{symbol}: Nested API error - {error_msg} (code: {error_code})")
                        job_stats.add_failed_api_error(symbol, f"{error_msg} (code: {error_code})")
                        tracker.mark_failed(symbol, error_msg, "api_error")
                        failure_count += 1
                        continue
            else:
                stats_data = req_response
        else:
            logger.warning(f"{symbol}: Unexpected response type: {type(req_response)}")
            logger.warning(f"{symbol}: RAW RESPONSE: {raw_req_response}")
            job_stats.add_failed_parse(symbol, f"Unexpected response type: {type(req_response)}", raw_req_response)
            tracker.mark_failed(symbol, f"Unexpected response type", "parse_error")
            failure_count += 1
            continue
        
        # Log what we're parsing
        if isinstance(stats_data, dict):
            logger.info(f"{symbol}: Parsing stats_data with keys: {list(stats_data.keys())}")
            if 'statistics' in stats_data:
                logger.info(f"{symbol}: Found 'statistics' key")
            else:
                logger.info(f"{symbol}: NO 'statistics' key - will check nested response")
        else:
            logger.info(f"{symbol}: stats_data is NOT a dict, type: {type(stats_data)}")
        
        # Parse the statistics
        fundamentals = parse_statistics_response(
            symbol=symbol,
            exchange=stock.get('exchange', ''),
            name=stock['name'],
            country=stock.get('country', ''),
            sector=stock.get('sector', ''),
            stats_data=stats_data,
            raw_response_str=raw_req_response
        )
        
        if fundamentals is None:
            tracker.mark_failed(symbol, "No meaningful data in response", "no_data")
            failure_count += 1
            continue
        
        # Save to JSON file
        output_file = fundamentals_dir / f"{symbol}.json"
        save_json(fundamentals, output_file)
        
        tracker.mark_completed(symbol)
        job_stats.add_success(symbol)
        success_count += 1
        
        pe_str = f"PE: {fundamentals.get('pe_ratio')}" if fundamentals.get('pe_ratio') else "PE: N/A"
        mc_str = f"MktCap: {fundamentals.get('market_cap'):,.0f}" if fundamentals.get('market_cap') else "MktCap: N/A"
        logger.info(f"[OK] {symbol}: Saved ({pe_str}, {mc_str})")
    
    # If any request in batch hit rate limit, signal batch retry
    if rate_limit_in_batch:
        logger.warning(f"Batch contained rate-limited requests - signaling retry")
        return success_count, failure_count, True  # batch_failed=True to trigger retry
    
    return success_count, failure_count, False


def main():
    global job_stats
    job_stats = JobStats()  # Reset stats for this run
    
    print("="*70)
    print("FUNDAMENTALS BATCH JOB - TWELVE DATA")
    print("="*70)
    
    # Load configuration
    config = BatchConfig()
    setup_logging(config)
    
    # Get API key
    try:
        api_key = config.get_api_key()
        logger.info(f"API Key loaded: {api_key[:4]}...{api_key[-4:]}")
    except ValueError as e:
        logger.error(str(e))
        print(f"\nERROR: {e}")
        print("Set TWELVE_DATA_API_KEY in your .env file")
        return
    
    # Initialize client and trackers
    client = TwelveDataClient(api_key, timeout=config.td_timeout)
    credit_tracker = CreditTracker(config.progress_dir, config.td_credits_per_minute)
    
    # Collect stocks from universe
    logger.info("Collecting stocks from universe files...")
    all_stocks = collect_stocks_from_universe(config.universe_dir)
    
    if not all_stocks:
        logger.error("No stocks found in universe files")
        print("\nERROR: No stocks found. Run batch_load_stock_universe.py first")
        return
    
    # Prioritize: large cap first
    all_stocks = prioritize_stocks(all_stocks)
    logger.info(f"Total stocks to process: {len(all_stocks)}")
    
    # Setup progress tracking
    tracker = ProgressTracker("fundamentals", config.progress_dir)
    tracker.set_total(len(all_stocks))
    
    # Filter out already completed
    remaining_stocks = [s for s in all_stocks if not tracker.is_completed(s['symbol'])]
    logger.info(f"Remaining after filtering completed: {len(remaining_stocks)}")
    
    # Calculate batches
    batch_size = config.td_batch_size
    batches = chunk_list(remaining_stocks, batch_size)
    credits_per_batch = batch_size * STATISTICS_CREDITS
    
    print(f"\nBatch Processing Configuration:")
    print(f"  Mode: {config.mode}")
    print(f"  Total stocks: {len(all_stocks)}")
    print(f"  Already completed: {len(all_stocks) - len(remaining_stocks)}")
    print(f"  Remaining: {len(remaining_stocks)}")
    print(f"  Batch size: {batch_size} stocks")
    print(f"  Total batches: {len(batches)}")
    print(f"  Credits per batch: {credits_per_batch}")
    print(f"  Credit limit: {config.td_credits_per_minute}/minute")
    
    # Estimate time
    batches_per_minute = config.td_credits_per_minute // credits_per_batch
    estimated_minutes = len(batches) / batches_per_minute if batches_per_minute > 0 else len(batches)
    print(f"  Estimated time: ~{estimated_minutes:.0f} minutes")
    
    # Show progress summary
    tracker.print_startup_summary()
    
    proceed = input("\nProceed with API calls? (yes/no): ")
    if proceed.lower() != 'yes':
        print("Aborted")
        return
    
    # Process batches
    total_success = 0
    total_failed = 0
    start_time = datetime.now()
    max_retries = 3
    
    for batch_num, batch_stocks in enumerate(batches, 1):
        credits_needed = len(batch_stocks) * STATISTICS_CREDITS
        
        logger.info(f"BATCH {batch_num}/{len(batches)} - {len(batch_stocks)} stocks")
        print(f"\nBatch {batch_num}/{len(batches)}")
        
        # Retry loop for this batch
        for retry in range(max_retries):
            try:
                # Wait for credits BEFORE each attempt (including retries)
                credit_tracker.wait_for_credits(credits_needed)
                print(f"  Attempt {retry + 1}/{max_retries} ({credit_tracker.get_summary()})")
                
                # Process batch
                success, failed, batch_failed = process_batch(
                    batch_stocks, client, config.fundamentals_dir, tracker
                )
                
                # Credits are consumed regardless of success/failure
                credit_tracker.use_credits(credits_needed)
                
                if batch_failed:
                    # Batch request failed (e.g., malformed JSON or rate limit hit)
                    if retry < max_retries - 1:
                        job_stats.increment_retries()
                        logger.warning(f"Batch {batch_num} failed, retry {retry + 2}/{max_retries}...")
                        print(f"  [!] Batch failed, will retry after credit reset...")
                        # Force wait for next minute to ensure rate limit is cleared
                        # This handles both malformed JSON (rare) and rate limit (more common)
                        credit_tracker.force_wait_for_reset()
                        continue
                    else:
                        # All retries exhausted, mark stocks as failed
                        logger.error(f"Batch {batch_num} failed after {max_retries} retries")
                        for stock in batch_stocks:
                            if not tracker.is_completed(stock['symbol']):
                                tracker.mark_failed(stock['symbol'], "Batch failed after retries", "network")
                                job_stats.add_failed_batch(stock['symbol'])
                        total_failed += len(batch_stocks)
                        print(f"  [X] Batch failed after {max_retries} attempts")
                        break
                
                # Batch succeeded (even if some individual stocks failed)
                total_success += success
                total_failed += failed
                
                print(f"  [OK] {success} success, [X] {failed} failed")
                break  # Exit retry loop
                
            except RateLimitExceeded as e:
                logger.error(f"Rate limit exceeded: {e}")
                tracker.mark_rate_limit_reached()
                
                print("\n" + "="*70)
                print("API RATE LIMIT REACHED")
                print("="*70)
                print(f"Stopped at batch {batch_num}/{len(batches)}")
                print(f"Progress saved. Run again to resume.")
                
                # Print summary even on early exit
                elapsed = (datetime.now() - start_time).total_seconds() / 60
                job_stats.print_summary(elapsed, config.fundamentals_dir)
                return
                
            except KeyboardInterrupt:
                print("\n\nInterrupted by user. Progress saved.")
                print(f"Run again to resume from batch {batch_num}")
                
                # Print summary even on interrupt
                elapsed = (datetime.now() - start_time).total_seconds() / 60
                job_stats.print_summary(elapsed, config.fundamentals_dir)
                return
                
            except Exception as e:
                logger.error(f"Unexpected error in batch {batch_num}: {e}")
                import traceback
                traceback.print_exc()
                # Credits were likely consumed, so record them
                credit_tracker.use_credits(credits_needed)
                if retry < max_retries - 1:
                    job_stats.increment_retries()
                    print(f"  [!] Error occurred, will retry...")
                    time.sleep(5)
                    continue
                break
        
        # Progress update every 10 batches
        if batch_num % 10 == 0:
            elapsed = (datetime.now() - start_time).total_seconds() / 60
            print(f"\n  === Progress: {tracker.get_summary()} ===")
            print(f"  === Elapsed: {elapsed:.1f} min, Retries: {job_stats.retries_needed}, {credit_tracker.get_summary()} ===\n")
        
        # Small delay between batches
        if batch_num < len(batches):
            time.sleep(2)
    
    # Final summary
    elapsed = (datetime.now() - start_time).total_seconds() / 60
    
    # Print detailed summary
    job_stats.print_summary(elapsed, config.fundamentals_dir)
    
    # Log failures to separate file
    failure_log_path = config.progress_dir / "fundamentals_failures.log"
    job_stats.log_to_file(failure_log_path)
    print(f"\nDetailed failure log saved to: {failure_log_path}")
    
    # Count output files
    output_files = list(config.fundamentals_dir.glob("*.json"))
    print(f"JSON files created: {len(output_files)}")
    
    print("\nNext step: Run upload_to_firestore.py to upload to Firestore")


if __name__ == "__main__":
    main()