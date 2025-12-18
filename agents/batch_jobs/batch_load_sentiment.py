"""
Batch job to fetch stock sentiment data from Twelve Data API.
Fetches analyst ratings, recommendations, and price targets.

Endpoints used:
- /analyst_ratings/light (75 credits) - Analyst ratings for US and international
- /recommendations (100 credits) - Buy/Hold/Sell recommendations
- /price_target (75 credits) - Analyst price targets

Modes:
- "full": All 3 endpoints (250 credits per stock)
- "recommendations_only": Only /recommendations (100 credits per stock)

Supports auto-select (1 representative stock per sector/country) or manual CSV input.
"""

import os
import logging
import time
from datetime import datetime, timezone
from typing import List, Dict, Tuple, Optional
from pathlib import Path

from batch_utils import (
    BatchConfig, ProgressTracker, CreditTracker, TwelveDataClient,
    save_json, load_json, setup_logging, load_stocks_from_csv,
    select_representative_stocks, chunk_list, RateLimitExceeded
)

logger = logging.getLogger(__name__)

# Credit costs
CREDITS = {
    'analyst_ratings_light': 75,
    'recommendations': 100,
    'price_target': 75,
    'full': 250,  # All three
    'recommendations_only': 100  # Just recommendations
}


def fetch_sentiment_full(stock: Dict, client: TwelveDataClient) -> Dict:
    """
    Fetch all sentiment data for a stock (full mode: 250 credits).
    
    Makes 3 batch requests:
    - /analyst_ratings/light
    - /recommendations  
    - /price_target
    
    Returns combined sentiment document.
    """
    symbol = stock['symbol']
    exchange = stock.get('exchange', '')
    
    # Build batch request with all 3 endpoints
    requests_dict = {
        'analyst_ratings': {'url': client.build_analyst_ratings_url(symbol, exchange)},
        'recommendations': {'url': client.build_recommendations_url(symbol, exchange)},
        'price_target': {'url': client.build_price_target_url(symbol, exchange)}
    }
    
    logger.info(f"Fetching full sentiment for {symbol}")
    response = client.execute_batch(requests_dict)
    
    if response is None:
        return None
    
    # Parse responses
    batch_data = response.get('data', response)
    
    return {
        'analyst_ratings': parse_analyst_ratings(batch_data.get('analyst_ratings', {})),
        'recommendations': parse_recommendations(batch_data.get('recommendations', {})),
        'price_target': parse_price_target(batch_data.get('price_target', {}))
    }


def fetch_sentiment_recommendations_only(stock: Dict, client: TwelveDataClient) -> Dict:
    """
    Fetch only recommendations for a stock (lite mode: 100 credits).
    
    Returns sentiment document with just recommendations.
    """
    symbol = stock['symbol']
    exchange = stock.get('exchange', '')
    
    # Single request for recommendations
    requests_dict = {
        'recommendations': {'url': client.build_recommendations_url(symbol, exchange)}
    }
    
    logger.info(f"Fetching recommendations for {symbol}")
    response = client.execute_batch(requests_dict)
    
    if response is None:
        return None
    
    batch_data = response.get('data', response)
    
    return {
        'analyst_ratings': None,
        'recommendations': parse_recommendations(batch_data.get('recommendations', {})),
        'price_target': None
    }


def parse_analyst_ratings(response: Dict) -> Optional[Dict]:
    """Parse analyst ratings response."""
    if not response or response.get('status') == 'error':
        return None
    
    data = response.get('response', response)
    
    if 'ratings' not in data:
        return None
    
    ratings = data.get('ratings', [])
    
    # Count rating changes
    upgrade_count = sum(1 for r in ratings if r.get('rating_change') == 'Upgrade')
    downgrade_count = sum(1 for r in ratings if r.get('rating_change') == 'Downgrade')
    maintains_count = sum(1 for r in ratings if r.get('rating_change') == 'Maintains')
    
    # Get recent ratings
    recent_ratings = []
    for r in ratings[:10]:  # Top 10 most recent
        recent_ratings.append({
            'date': r.get('date'),
            'firm': r.get('firm'),
            'rating_change': r.get('rating_change'),
            'rating_current': r.get('rating_current'),
            'rating_prior': r.get('rating_prior')
        })
    
    return {
        'total_ratings': len(ratings),
        'upgrades': upgrade_count,
        'downgrades': downgrade_count,
        'maintains': maintains_count,
        'recent_ratings': recent_ratings
    }


def parse_recommendations(response: Dict) -> Optional[Dict]:
    """Parse recommendations response."""
    if not response or response.get('status') == 'error':
        return None
    
    data = response.get('response', response)
    
    if 'trends' not in data:
        return None
    
    trends = data.get('trends', {})
    current = trends.get('current_month', {})
    
    # Calculate consensus
    strong_buy = current.get('strong_buy', 0)
    buy = current.get('buy', 0)
    hold = current.get('hold', 0)
    sell = current.get('sell', 0)
    strong_sell = current.get('strong_sell', 0)
    
    total = strong_buy + buy + hold + sell + strong_sell
    
    if total > 0:
        # Calculate weighted score (5=strong buy, 1=strong sell)
        score = (strong_buy * 5 + buy * 4 + hold * 3 + sell * 2 + strong_sell * 1) / total
        
        # Determine consensus label
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
        'total_analysts': total,
        'raw_rating': data.get('rating')
    }


def parse_price_target(response: Dict) -> Optional[Dict]:
    """Parse price target response."""
    if not response or response.get('status') == 'error':
        return None
    
    data = response.get('response', response)
    
    if 'price_target' not in data:
        return None
    
    pt = data.get('price_target', {})
    
    current_price = pt.get('current')
    average_target = pt.get('average')
    
    # Calculate upside/downside potential
    if current_price and average_target:
        try:
            upside_percent = ((average_target - current_price) / current_price) * 100
        except (TypeError, ZeroDivisionError):
            upside_percent = None
    else:
        upside_percent = None
    
    return {
        'high': pt.get('high'),
        'low': pt.get('low'),
        'average': average_target,
        'median': pt.get('median'),
        'current_price': current_price,
        'currency': pt.get('currency'),
        'upside_percent': round(upside_percent, 2) if upside_percent else None
    }


def build_sentiment_document(stock: Dict, sentiment_data: Dict) -> Dict:
    """
    Build the final sentiment document for Firestore.
    """
    return {
        # Identity
        'symbol': stock['symbol'],
        'name': stock['name'],
        'exchange': stock.get('exchange', '') or 'USA',
        'country': stock.get('country', ''),
        'sector': stock.get('sector', ''),
        
        # Sentiment data
        'analyst_ratings': sentiment_data.get('analyst_ratings'),
        'recommendations': sentiment_data.get('recommendations'),
        'price_target': sentiment_data.get('price_target'),
        
        # Flags
        'is_sector_representative': stock.get('is_representative', False),
        'has_full_data': all([
            sentiment_data.get('analyst_ratings'),
            sentiment_data.get('recommendations'),
            sentiment_data.get('price_target')
        ]),
        
        # Metadata
        'fetched_at': datetime.now(timezone.utc).isoformat(),
        'data_source': 'Twelve Data',
        'fetch_mode': stock.get('fetch_mode', 'full')
    }


def process_stock(stock: Dict, client: TwelveDataClient, mode: str) -> Tuple[Optional[Dict], int]:
    """
    Process a single stock and return sentiment document.
    
    Args:
        stock: Stock dictionary
        client: TwelveDataClient
        mode: "full" or "recommendations_only"
        
    Returns:
        Tuple of (sentiment_document, credits_used)
    """
    if mode == 'full':
        sentiment_data = fetch_sentiment_full(stock, client)
        credits_used = CREDITS['full']
    else:
        sentiment_data = fetch_sentiment_recommendations_only(stock, client)
        credits_used = CREDITS['recommendations_only']
    
    if sentiment_data is None:
        return None, credits_used
    
    # Check if we got any useful data
    has_any_data = any([
        sentiment_data.get('analyst_ratings'),
        sentiment_data.get('recommendations'),
        sentiment_data.get('price_target')
    ])
    
    if not has_any_data:
        return None, credits_used
    
    stock['fetch_mode'] = mode
    document = build_sentiment_document(stock, sentiment_data)
    
    return document, credits_used


def main():
    print("="*70)
    print("SENTIMENT BATCH JOB - TWELVE DATA")
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
        return
    
    # Determine mode and credits
    mode = config.sentiment_mode
    credits_per_stock = CREDITS.get(mode, CREDITS['recommendations_only'])
    
    print(f"\nSentiment Mode: {mode}")
    print(f"Credits per stock: {credits_per_stock}")
    
    # Load stocks
    logger.info(f"Loading stocks from: {config.sentiment_input_file}")
    all_stocks = load_stocks_from_csv(config.sentiment_input_file)
    
    if not all_stocks:
        logger.error("No stocks found in input file")
        print(f"\nERROR: No stocks found in {config.sentiment_input_file}")
        return
    
    # Auto-select or use all
    if config.sentiment_auto_select:
        stocks = select_representative_stocks(all_stocks)
        for s in stocks:
            s['is_representative'] = True
        print(f"Auto-selected {len(stocks)} representative stocks (1 per sector/country)")
    else:
        stocks = all_stocks
        print(f"Processing all {len(stocks)} stocks from input file")
    
    # Initialize
    client = TwelveDataClient(api_key, timeout=config.td_timeout)
    credit_tracker = CreditTracker(config.progress_dir, config.td_credits_per_minute)
    tracker = ProgressTracker("sentiment", config.progress_dir)
    tracker.set_total(len(stocks))
    
    # Filter already completed
    remaining = [s for s in stocks if not tracker.is_completed(s['symbol'])]
    
    print(f"\nProcessing Configuration:")
    print(f"  Total stocks: {len(stocks)}")
    print(f"  Already completed: {len(stocks) - len(remaining)}")
    print(f"  Remaining: {len(remaining)}")
    print(f"  Credits needed: ~{len(remaining) * credits_per_stock}")
    print(f"  Credit limit: {config.td_credits_per_minute}/minute")
    
    estimated_time = (len(remaining) * credits_per_stock / config.td_credits_per_minute)
    print(f"  Estimated time: ~{estimated_time:.1f} minutes")
    
    tracker.print_startup_summary()
    
    proceed = input("\nProceed with API calls? (yes/no): ")
    if proceed.lower() != 'yes':
        print("Aborted")
        return
    
    # Process stocks
    total_success = 0
    total_failed = 0
    
    for idx, stock in enumerate(remaining, 1):
        symbol = stock['symbol']
        
        logger.info(f"\n[{idx}/{len(remaining)}] Processing {symbol}")
        
        # Wait for credits
        credit_tracker.wait_for_credits(credits_per_stock)
        
        try:
            # Process stock
            document, credits_used = process_stock(stock, client, mode)
            
            # Record credit usage
            credit_tracker.use_credits(credits_used)
            
            if document is None:
                logger.warning(f"{symbol}: No sentiment data available")
                tracker.mark_failed(symbol, "No data available", "no_data")
                total_failed += 1
            else:
                # Save to file
                output_file = config.sentiment_dir / f"{symbol}.json"
                save_json(document, output_file)
                
                tracker.mark_completed(symbol)
                total_success += 1
                
                consensus = document.get('recommendations', {})
                if consensus:
                    consensus_label = consensus.get('consensus', 'N/A')
                    logger.info(f"{symbol}: Saved sentiment (Consensus: {consensus_label})")
                else:
                    logger.info(f"{symbol}: Saved sentiment (partial data)")
            
            # Progress update
            if idx % 5 == 0:
                print(f"\nProgress: {tracker.get_summary()}")
                print(credit_tracker.get_summary())
            
            # Small delay between requests
            if idx < len(remaining):
                time.sleep(1)
                
        except RateLimitExceeded as e:
            logger.error(f"Rate limit exceeded: {e}")
            tracker.mark_rate_limit_reached()
            print("\n" + "="*70)
            print("API RATE LIMIT REACHED")
            print("="*70)
            print("Progress saved. Run again to resume.")
            break
            
        except Exception as e:
            logger.error(f"Error processing {symbol}: {e}")
            tracker.mark_failed(symbol, str(e), "error")
            total_failed += 1
            continue
    
    # Final summary
    print("\n" + "="*70)
    print("SENTIMENT JOB COMPLETE")
    print("="*70)
    print(tracker.get_summary())
    print(credit_tracker.get_summary())
    print(f"\nOutput directory: {config.sentiment_dir}")
    print(f"Total successful: {total_success}")
    print(f"Total failed: {total_failed}")
    
    if tracker.progress['failed_items']:
        print(f"\nFailed items logged in: {tracker.progress_file}")
    
    print("\nNext step: Run upload_to_firestore.py to upload to Firestore")


if __name__ == "__main__":
    main()