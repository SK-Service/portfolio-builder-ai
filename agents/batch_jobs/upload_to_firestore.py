"""
Upload batch job output (JSON files) to Firestore.
Reads JSON files from batch_output/ and writes to Firestore collections.

Collections:
- stock_universe: Stock lists by country/sector
- stock_fundamentals: Individual stock fundamental data
- market_sentiment: Individual stock sentiment data

Also sets up initial configuration documents:
- config/api_keys: API key storage
- config/settings: Runtime settings
"""

import os
import logging
from pathlib import Path
from datetime import datetime, timezone
from firebase_admin import initialize_app, firestore, credentials
from batch_utils import BatchConfig, setup_logging, load_json

logger = logging.getLogger(__name__)


def upload_stock_universe(config: BatchConfig, db) -> int:
    """Upload stock universe documents to Firestore."""
    collection_name = config.firestore_collections['stock_universe']
    collection_ref = db.collection(collection_name)
    
    logger.info(f"Uploading to collection: {collection_name}")
    
    uploaded = 0
    for json_file in config.universe_dir.glob("*.json"):
        data = load_json(json_file)
        if not data:
            logger.warning(f"Skipping empty file: {json_file}")
            continue
        
        data['last_updated'] = datetime.now(timezone.utc)
        doc_id = json_file.stem
        
        collection_ref.document(doc_id).set(data)
        logger.info(f"Uploaded universe: {doc_id} ({data.get('stock_count', 0)} stocks)")
        uploaded += 1
    
    return uploaded


def upload_fundamentals(config: BatchConfig, db) -> int:
    """Upload stock fundamentals documents to Firestore."""
    collection_name = config.firestore_collections['fundamentals']
    collection_ref = db.collection(collection_name)
    
    logger.info(f"Uploading to collection: {collection_name}")
    
    uploaded = 0
    for json_file in config.fundamentals_dir.glob("*.json"):
        data = load_json(json_file)
        if not data:
            continue
        
        doc_id = data.get('symbol', json_file.stem)
        
        if isinstance(data.get('last_updated'), str):
            try:
                data['last_updated'] = datetime.fromisoformat(
                    data['last_updated'].replace('Z', '+00:00')
                )
            except Exception:
                data['last_updated'] = datetime.now(timezone.utc)
        
        collection_ref.document(doc_id).set(data)
        uploaded += 1
        
        if uploaded % 50 == 0:
            print(f"  Progress: {uploaded} fundamentals uploaded...")
    
    logger.info(f"Uploaded {uploaded} fundamental documents")
    return uploaded


def upload_sentiment(config: BatchConfig, db) -> int:
    """Upload market sentiment documents to Firestore."""
    collection_name = config.firestore_collections['sentiment']
    collection_ref = db.collection(collection_name)
    
    logger.info(f"Uploading to collection: {collection_name}")
    
    uploaded = 0
    for json_file in config.sentiment_dir.glob("*.json"):
        data = load_json(json_file)
        if not data:
            continue
        
        doc_id = data.get('symbol', json_file.stem)
        
        if isinstance(data.get('fetched_at'), str):
            try:
                data['fetched_at'] = datetime.fromisoformat(
                    data['fetched_at'].replace('Z', '+00:00')
                )
            except Exception:
                data['fetched_at'] = datetime.now(timezone.utc)
        
        collection_ref.document(doc_id).set(data)
        uploaded += 1
        
        consensus = 'N/A'
        if data.get('recommendations'):
            consensus = data['recommendations'].get('consensus', 'N/A')
        
        logger.info(f"Uploaded sentiment: {doc_id} (Consensus: {consensus})")
    
    return uploaded


def setup_config_documents(db, api_key: str = None):
    """Set up configuration documents in Firestore."""
    config_collection = db.collection('config')
    
    # API Keys document
    api_keys_doc = config_collection.document('api_keys')
    existing = api_keys_doc.get()
    
    if not existing.exists:
        api_keys_data = {
            'twelve_data_api_key': api_key or os.getenv('TWELVE_DATA_API_KEY', ''),
            'created_at': datetime.now(timezone.utc),
            'note': 'Store API keys here for runtime access by tools'
        }
        api_keys_doc.set(api_keys_data)
        logger.info("Created config/api_keys document")
    else:
        logger.info("config/api_keys document already exists")
    
    # Settings document
    settings_doc = config_collection.document('settings')
    existing = settings_doc.get()
    
    if not existing.exists:
        settings_data = {
            'enable_realtime_api_calls': False,
            'sentiment_cache_ttl_days': 30,
            'sentiment_use_fallback': True,
            'credits_per_minute_limit': 500,
            'created_at': datetime.now(timezone.utc),
            'note': 'Runtime settings for tools and batch jobs'
        }
        settings_doc.set(settings_data)
        logger.info("Created config/settings document")
    else:
        logger.info("config/settings document already exists")


def setup_api_usage_document(db):
    """Initialize API usage tracking document."""
    usage_collection = db.collection('api_usage')
    usage_doc = usage_collection.document('twelve_data')
    
    existing = usage_doc.get()
    if not existing.exists:
        usage_data = {
            'current_minute_start': None,
            'current_minute_credits': 0,
            'total_credits_used': 0,
            'credits_per_minute_limit': 500,
            'last_updated': datetime.now(timezone.utc),
            'note': 'Tracks Twelve Data API credit usage'
        }
        usage_doc.set(usage_data)
        logger.info("Created api_usage/twelve_data document")


def verify_upload(config: BatchConfig, db):
    """Verify data was uploaded correctly."""
    print("\n" + "="*70)
    print("VERIFICATION")
    print("="*70)
    
    # Check stock universe
    universe_col = db.collection(config.firestore_collections['stock_universe'])
    universe_docs = list(universe_col.stream())
    print(f"Stock Universe: {len(universe_docs)} documents")
    
    # Check fundamentals
    fundamentals_col = db.collection(config.firestore_collections['fundamentals'])
    fundamentals_docs = list(fundamentals_col.stream())
    print(f"Fundamentals: {len(fundamentals_docs)} documents")
    
    # Check sentiment
    sentiment_col = db.collection(config.firestore_collections['sentiment'])
    sentiment_docs = list(sentiment_col.stream())
    print(f"Sentiment: {len(sentiment_docs)} documents")
    
    # Check config
    config_col = db.collection('config')
    config_docs = list(config_col.stream())
    print(f"Config: {len(config_docs)} documents")
    
    # Check api_usage
    usage_col = db.collection('api_usage')
    usage_docs = list(usage_col.stream())
    print(f"API Usage: {len(usage_docs)} documents")
    
    return len(universe_docs), len(fundamentals_docs), len(sentiment_docs)


def main():
    print("="*70)
    print("FIRESTORE UPLOAD SCRIPT")
    print("="*70)
    print("\nThis will upload batch job output to Firestore.")
    
    # Load configuration
    config = BatchConfig()
    setup_logging(config)
    
    # Check if output files exist
    universe_files = list(config.universe_dir.glob("*.json"))
    fundamentals_files = list(config.fundamentals_dir.glob("*.json"))
    sentiment_files = list(config.sentiment_dir.glob("*.json"))
    
    print(f"\nFiles to upload:")
    print(f"  Stock Universe: {len(universe_files)} files")
    print(f"  Fundamentals: {len(fundamentals_files)} files")
    print(f"  Sentiment: {len(sentiment_files)} files")
    
    if not universe_files and not fundamentals_files and not sentiment_files:
        print("\nWARNING: No data files found to upload")
        print("Run batch jobs first:")
        print("  1. python batch_load_stock_universe.py")
        print("  2. python batch_load_fundamentals.py")
        print("  3. python batch_load_sentiment.py")
    
    print("\nThis script will also set up configuration documents.")
    
    proceed = input("\nProceed with upload? (yes/no): ")
    if proceed.lower() != 'yes':
        print("Aborted")
        return
    
    # Initialize Firebase
    try:
        initialize_app()
        db = firestore.client()
        logger.info("Firebase Admin SDK initialized")
    except ValueError:
        # Already initialized
        db = firestore.client()
        logger.info("Firebase Admin SDK already initialized")
    except Exception as e:
        logger.error(f"Firebase initialization failed: {e}")
        print("\nERROR: Cannot connect to Firebase")
        print("Make sure you have set GOOGLE_APPLICATION_CREDENTIALS")
        print("or are running in a Firebase environment")
        return
    
    try:
        # Set up config documents first
        print("\nSetting up configuration documents...")
        setup_config_documents(db)
        setup_api_usage_document(db)
        
        # Upload each collection
        if universe_files:
            print("\nUploading stock universe...")
            count = upload_stock_universe(config, db)
            print(f"Uploaded {count} stock universe documents")
        
        if fundamentals_files:
            print("\nUploading fundamentals...")
            count = upload_fundamentals(config, db)
            print(f"Uploaded {count} fundamental documents")
        
        if sentiment_files:
            print("\nUploading sentiment...")
            count = upload_sentiment(config, db)
            print(f"Uploaded {count} sentiment documents")
        
        # Verify
        verify_upload(config, db)
        
        print("\n" + "="*70)
        print("UPLOAD COMPLETE")
        print("="*70)
        print("\nCheck Firebase Console to verify:")
        print("https://console.firebase.google.com/")
        print("\nIMPORTANT: Update config/settings to enable real-time API calls:")
        print("  1. Go to Firestore > config > settings")
        print("  2. Set enable_realtime_api_calls to true")
        print("\nNext step: Test the agent tools with the uploaded data")
        
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()