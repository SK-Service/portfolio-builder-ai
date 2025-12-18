"""
Batch job to load stock universe from CSV seeds.
Reads stock_universe_seeds.csv and creates JSON files per sector per country.
No API calls - just data organization.
"""

import csv
import logging
from collections import defaultdict
from batch_utils import BatchConfig, ProgressTracker, save_json, setup_logging

logger = logging.getLogger(__name__)


def load_seeds_from_csv(csv_path: str = "./stock_universe_seeds.csv"):
    """Load stock seeds from CSV file."""
    stocks_by_country_sector = defaultdict(list)
    
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            key = (row['country'], row['sector'])
            stocks_by_country_sector[key].append({
                'symbol': row['symbol'],
                'name': row['name'],
                'market_cap_tier': row['market_cap_tier'],
                'exchange': row['exchange']  # Added exchange field
            })
    
    return stocks_by_country_sector


def main():
    print("="*70)
    print("STOCK UNIVERSE BATCH JOB")
    print("="*70)
    
    # Load configuration
    config = BatchConfig()
    setup_logging(config)
    
    logger.info(f"Mode: {config.mode}")
    logger.info(f"Stocks per sector: {config.stocks_per_sector}")
    
    # Load seeds
    logger.info("Loading stock seeds from CSV...")
    stocks_by_country_sector = load_seeds_from_csv()
    
    # Progress tracking
    total_combinations = len(config.countries) * len(config.sectors)
    tracker = ProgressTracker("stock_universe", config.progress_dir)
    tracker.set_total(total_combinations)
    
    # Process each country-sector combination
    processed_count = 0
    
    for country in config.countries:
        for sector in config.sectors:
            item_id = f"{country}_{sector}"
            
            # Skip if already processed
            if tracker.is_completed(item_id):
                logger.info(f"Skipping {item_id} (already processed)")
                continue
            
            # Get stocks for this combination
            key = (country, sector)
            stocks = stocks_by_country_sector.get(key, [])
            
            # Limit to configured count
            stocks = stocks[:config.stocks_per_sector]
            
            if not stocks:
                logger.warning(f"No stocks found for {country}/{sector}")
                tracker.mark_failed(item_id, "No stocks in seeds CSV")
                continue
            
            # Create output document
            document = {
                'country': country,
                'sector': sector,
                'stocks': stocks,
                'stock_count': len(stocks),
                'last_updated': None  # Will be set during Firestore upload
            }
            
            # Save to JSON
            output_file = config.universe_dir / f"{country}_{sector}.json"
            save_json(document, output_file)
            
            logger.info(f"Created {item_id}: {len(stocks)} stocks")
            tracker.mark_completed(item_id)
            processed_count += 1
    
    # Summary
    print("\n" + "="*70)
    print("STOCK UNIVERSE JOB COMPLETE")
    print("="*70)
    print(tracker.get_summary())
    print(f"\nOutput directory: {config.universe_dir}")
    print(f"Files created: {processed_count}")
    print("\nNext step: Run batch_load_fundamentals.py")


if __name__ == "__main__":
    main()