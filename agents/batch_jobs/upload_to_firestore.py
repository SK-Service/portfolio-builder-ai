"""
Upload batch job output (JSON files) to Firestore.
Reads JSON files from batch_output/ and writes to Firestore collections.

Prerequisites:
1. Add to .env file:
   GOOGLE_APPLICATION_CREDENTIALS=path/to/firebase-service-account.json

2. Install firebase-admin:
   pip install firebase-admin
"""

import os
import json
import logging
from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv

# Load environment variables from .env file (parent directory)
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

from firebase_admin import credentials, initialize_app, firestore
from batch_utils import BatchConfig, setup_logging, load_json

logger = logging.getLogger(__name__)


def validate_credentials():
    """Validate that Firebase credentials are configured."""
    cred_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    
    if not cred_path:
        print("\nERROR: GOOGLE_APPLICATION_CREDENTIALS not set")
        print("\nAdd this to your .env file (in agents/ folder):")
       
        return None
    
    cred_path = Path(cred_path)
    if not cred_path.exists():
        print(f"\nERROR: Credentials file not found: {cred_path}")
        print("\nMake sure the path in GOOGLE_APPLICATION_CREDENTIALS is correct")
        return None
    
    print(f"Using credentials: {cred_path}")
    return str(cred_path)


def upload_stock_universe(config: BatchConfig, db):
    """Upload stock universe documents to Firestore."""
    collection_name = config.firestore_collections['stock_universe']
    collection_ref = db.collection(collection_name)
    
    logger.info(f"Uploading to collection: {collection_name}")
    print(f"  Collection: {collection_name}")
    
    uploaded = 0
    for json_file in config.universe_dir.glob("*.json"):
        data = load_json(json_file)
        if not data:
            logger.warning(f"Skipping empty file: {json_file}")
            continue
        
        # Convert any datetime strings to proper format
        data['uploaded_at'] = datetime.now(timezone.utc).isoformat()
        
        # Document ID: country_sector (e.g., USA_technology)
        doc_id = json_file.stem
        
        # Upload
        collection_ref.document(doc_id).set(data)
        logger.info(f"Uploaded: {doc_id} ({data.get('stock_count', 'N/A')} stocks)")
        uploaded += 1
    
    return uploaded


def upload_fundamentals(config: BatchConfig, db):
    """Upload stock fundamentals documents to Firestore."""
    collection_name = config.firestore_collections['fundamentals']
    collection_ref = db.collection(collection_name)
    
    logger.info(f"Uploading to collection: {collection_name}")
    print(f"  Collection: {collection_name}")
    
    uploaded = 0
    errors = []
    
    for json_file in config.fundamentals_dir.glob("*.json"):
        try:
            data = load_json(json_file)
            if not data:
                logger.warning(f"Skipping empty file: {json_file}")
                continue
            
            # Document ID: stock symbol
            # Handle sanitized filenames (e.g., _PRN.json -> PRN)
            doc_id = data.get('symbol', json_file.stem)
            if doc_id.startswith('_'):
                doc_id = doc_id[1:]  # Remove leading underscore if present
            
            # Upload
            collection_ref.document(doc_id).set(data)
            logger.debug(f"Uploaded: {doc_id}")
            uploaded += 1
            
            # Progress indicator
            if uploaded % 100 == 0:
                print(f"  Progress: {uploaded} stocks uploaded...")
                
        except Exception as e:
            error_msg = f"{json_file.name}: {str(e)}"
            errors.append(error_msg)
            logger.error(f"Failed to upload {json_file}: {e}")
    
    if errors:
        print(f"  Errors: {len(errors)} files failed")
        for err in errors[:5]:
            print(f"    - {err}")
        if len(errors) > 5:
            print(f"    ... and {len(errors) - 5} more")
    
    return uploaded


def upload_sentiment(config: BatchConfig, db):
    """Upload market sentiment documents to Firestore."""
    collection_name = config.firestore_collections['sentiment']
    collection_ref = db.collection(collection_name)
    
    logger.info(f"Uploading to collection: {collection_name}")
    print(f"  Collection: {collection_name}")
    
    uploaded = 0
    for json_file in config.sentiment_dir.glob("*.json"):
        data = load_json(json_file)
        if not data:
            continue
        
        # Document ID: from filename
        doc_id = json_file.stem
        
        # Upload
        collection_ref.document(doc_id).set(data)
        logger.info(f"Uploaded: {doc_id}")
        uploaded += 1
    
    return uploaded


def verify_upload(config: BatchConfig, db):
    """Verify data was uploaded correctly by sampling."""
    print("\n" + "="*70)
    print("VERIFICATION")
    print("="*70)
    
    # Check stock universe
    universe_col = db.collection(config.firestore_collections['stock_universe'])
    universe_docs = list(universe_col.limit(100).stream())
    print(f"Stock Universe: {len(universe_docs)} documents (sampled)")
    
    # Check fundamentals
    fundamentals_col = db.collection(config.firestore_collections['fundamentals'])
    fundamentals_docs = list(fundamentals_col.limit(100).stream())
    print(f"Fundamentals: {len(fundamentals_docs)}+ documents (sampled first 100)")
    
    # Show a sample document
    if fundamentals_docs:
        sample = fundamentals_docs[0].to_dict()
        print(f"\nSample document ({fundamentals_docs[0].id}):")
        print(f"  Symbol: {sample.get('symbol')}")
        print(f"  Name: {sample.get('name')}")
        print(f"  Country: {sample.get('country')}")
        print(f"  Sector: {sample.get('sector')}")
        print(f"  Currency: {sample.get('currency')}")
        print(f"  PE Ratio: {sample.get('pe_ratio')}")
        print(f"  Market Cap: {sample.get('market_cap')}")
    
    # Check sentiment
    sentiment_col = db.collection(config.firestore_collections['sentiment'])
    sentiment_docs = list(sentiment_col.limit(10).stream())
    print(f"Sentiment: {len(sentiment_docs)} documents")
    
    return len(universe_docs), len(fundamentals_docs), len(sentiment_docs)


def main():
    print("="*70)
    print("FIRESTORE UPLOAD SCRIPT")
    print("="*70)
    
    # Validate credentials first
    cred_path = validate_credentials()
    if not cred_path:
        return
    
    # Load configuration
    config = BatchConfig()
    setup_logging(config)
    
    # Check if output files exist
    universe_files = list(config.universe_dir.glob("*.json"))
    fundamentals_files = list(config.fundamentals_dir.glob("*.json"))
    sentiment_files = list(config.sentiment_dir.glob("*.json")) if config.sentiment_dir.exists() else []
    
    print(f"\nFiles to upload:")
    print(f"  Stock Universe: {len(universe_files)} files")
    print(f"  Fundamentals: {len(fundamentals_files)} files")
    print(f"  Sentiment: {len(sentiment_files)} files")
    
    if not universe_files and not fundamentals_files and not sentiment_files:
        print("\nERROR: No files found to upload")
        print("Run batch jobs first:")
        print("  1. python batch_load_stock_universe.py")
        print("  2. python batch_load_fundamentals.py")
        return
    
    print(f"\nFirestore collections:")
    print(f"  Stock Universe -> {config.firestore_collections['stock_universe']}")
    print(f"  Fundamentals -> {config.firestore_collections['fundamentals']}")
    print(f"  Sentiment -> {config.firestore_collections['sentiment']}")
    
    proceed = input("\nProceed with upload? (yes/no): ")
    if proceed.lower() != 'yes':
        print("Aborted")
        return
    
    # Initialize Firebase
    try:
        cred = credentials.Certificate(cred_path)
        initialize_app(cred)
        db = firestore.client()
        logger.info("Firebase Admin SDK initialized successfully")
        print("\nFirebase connected successfully")
    except Exception as e:
        logger.error(f"Firebase initialization failed: {e}")
        print(f"\nERROR: Cannot connect to Firebase: {e}")
        return
    
    # Upload each collection
    try:
        # Stock universe
        if universe_files:
            print("\nUploading stock universe...")
            count = upload_stock_universe(config, db)
            print(f"  Uploaded {count} stock universe documents")
        
        # Fundamentals
        if fundamentals_files:
            print("\nUploading fundamentals...")
            count = upload_fundamentals(config, db)
            print(f"  Uploaded {count} fundamental documents")
        
        # Sentiment
        if sentiment_files:
            print("\nUploading sentiment...")
            count = upload_sentiment(config, db)
            print(f"  Uploaded {count} sentiment documents")
        
        # Verify
        verify_upload(config, db)
        
        print("\n" + "="*70)
        print("UPLOAD COMPLETE")
        print("="*70)
        
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()