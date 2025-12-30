"""
Upload macro economic data (JSON files) to Firestore.
Reads calculated JSON files from batch_output/macro/ and writes to Firestore.

Prerequisites:
1. Add to .env file:
   GOOGLE_APPLICATION_CREDENTIALS=path/to/firebase-service-account.json

2. Install firebase-admin:
   pip install firebase-admin

3. Run batch_load_macro.py first to generate the calculated JSON files.

Usage:
    python upload_macro_to_firestore.py
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

logger = logging.getLogger(__name__)

# Configuration
FIRESTORE_COLLECTION = "macro_economic_data"
COUNTRIES = ["usa", "canada", "eu", "india"]


def setup_logging():
    """Configure logging."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )


def validate_credentials():
    """Validate that Firebase credentials are configured."""
    cred_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    
    if not cred_path:
        print("\nERROR: GOOGLE_APPLICATION_CREDENTIALS not set")
        print("\nAdd this to your .env file (in agents/ folder):")
        print("  GOOGLE_APPLICATION_CREDENTIALS=path/to/firebase-service-account.json")
        return None
    
    cred_path = Path(cred_path)
    if not cred_path.exists():
        print(f"\nERROR: Credentials file not found: {cred_path}")
        print("\nMake sure the path in GOOGLE_APPLICATION_CREDENTIALS is correct")
        return None
    
    print(f"  Using credentials: {cred_path}")
    return str(cred_path)


def get_macro_output_dir() -> Path:
    """Get the macro output directory path."""
    script_dir = Path(__file__).parent.resolve()
    
    # Handle both running from batch_jobs and other locations
    if script_dir.name == "batch_jobs":
        return script_dir / "batch_output" / "macro"
    else:
        # Try to find it relative to agents directory
        agents_dir = script_dir
        while agents_dir.name != "agents" and agents_dir.parent != agents_dir:
            agents_dir = agents_dir.parent
        if agents_dir.name == "agents":
            return agents_dir / "batch_jobs" / "batch_output" / "macro"
        else:
            # Fallback to script directory
            return script_dir / "batch_output" / "macro"


def load_json(filepath: Path) -> dict:
    """Load and parse a JSON file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load {filepath}: {e}")
        return None


def upload_macro_data(db, macro_dir: Path) -> dict:
    """
    Upload macro economic data documents to Firestore.
    
    Args:
        db: Firestore client
        macro_dir: Path to macro output directory
        
    Returns:
        Dictionary with upload statistics
    """
    collection_ref = db.collection(FIRESTORE_COLLECTION)
    
    logger.info(f"Uploading to collection: {FIRESTORE_COLLECTION}")
    print(f"\n  Collection: {FIRESTORE_COLLECTION}")
    
    stats = {
        "uploaded": 0,
        "failed": 0,
        "skipped": 0,
        "details": []
    }
    
    for country in COUNTRIES:
        filename = f"{country}_calculated.json"
        filepath = macro_dir / filename
        
        if not filepath.exists():
            print(f"  - {country}: SKIPPED (file not found)")
            stats["skipped"] += 1
            stats["details"].append(f"{country}: file not found")
            continue
        
        data = load_json(filepath)
        if not data:
            print(f"  - {country}: FAILED (could not parse JSON)")
            stats["failed"] += 1
            stats["details"].append(f"{country}: JSON parse error")
            continue
        
        try:
            # Add upload metadata
            data['uploaded_at'] = datetime.now(timezone.utc).isoformat()
            
            # Document ID is lowercase country code (usa, canada, eu, india)
            doc_id = country.lower()
            
            # Upload to Firestore
            collection_ref.document(doc_id).set(data)
            
            # Get indicator count for logging
            indicator_count = len(data.get('indicators', {}))
            
            print(f"  - {country}: ✓ ({indicator_count} indicators)")
            logger.info(f"Uploaded: {doc_id} with {indicator_count} indicators")
            
            stats["uploaded"] += 1
            stats["details"].append(f"{country}: {indicator_count} indicators")
            
        except Exception as e:
            print(f"  - {country}: FAILED ({str(e)[:50]})")
            logger.error(f"Failed to upload {country}: {e}")
            stats["failed"] += 1
            stats["details"].append(f"{country}: {str(e)}")
    
    return stats


def verify_upload(db) -> dict:
    """Verify data was uploaded correctly."""
    print("\n" + "=" * 60)
    print("VERIFICATION")
    print("=" * 60)
    
    collection_ref = db.collection(FIRESTORE_COLLECTION)
    
    verification = {}
    
    for country in COUNTRIES:
        doc_ref = collection_ref.document(country)
        doc = doc_ref.get()
        
        if doc.exists:
            data = doc.to_dict()
            indicators = data.get('indicators', {})
            
            print(f"\n  {country.upper()}:")
            print(f"    Data source: {data.get('data_source', 'N/A')}")
            print(f"    Timestamp: {data.get('timestamp', 'N/A')}")
            print(f"    Indicators: {len(indicators)}")
            
            for name, ind in indicators.items():
                print(f"      - {name}: {ind.get('value')}% ({ind.get('period')})")
            
            print(f"    Context: {data.get('economic_context', 'N/A')}")
            
            verification[country] = {
                "exists": True,
                "indicator_count": len(indicators)
            }
        else:
            print(f"\n  {country.upper()}: NOT FOUND")
            verification[country] = {
                "exists": False,
                "indicator_count": 0
            }
    
    return verification


def main():
    print("=" * 60)
    print("MACRO ECONOMIC DATA - FIRESTORE UPLOAD")
    print("=" * 60)
    
    setup_logging()
    
    # Validate credentials
    print("\nConfiguration:")
    cred_path = validate_credentials()
    if not cred_path:
        return
    
    # Get macro output directory
    macro_dir = get_macro_output_dir()
    print(f"  Macro data dir: {macro_dir}")
    
    if not macro_dir.exists():
        print(f"\nERROR: Macro output directory not found: {macro_dir}")
        print("Run batch_load_macro.py first to generate the data files.")
        return
    
    # Check for calculated JSON files
    print(f"\nFiles to upload:")
    files_found = []
    for country in COUNTRIES:
        filepath = macro_dir / f"{country}_calculated.json"
        if filepath.exists():
            data = load_json(filepath)
            if data:
                indicator_count = len(data.get('indicators', {}))
                print(f"  - {country}_calculated.json: {indicator_count} indicators")
                files_found.append(country)
            else:
                print(f"  - {country}_calculated.json: INVALID")
        else:
            print(f"  - {country}_calculated.json: NOT FOUND")
    
    if not files_found:
        print("\nERROR: No valid calculated JSON files found")
        print("Run batch_load_macro.py first to generate the data files.")
        return
    
    print(f"\nFirestore collection: {FIRESTORE_COLLECTION}")
    print(f"Documents to create: {', '.join(files_found)}")
    
    # Confirm
    proceed = input("\nProceed with upload? (yes/no): ").strip().lower()
    if proceed != 'yes':
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
    
    # Upload
    try:
        print("\nUploading macro economic data...")
        stats = upload_macro_data(db, macro_dir)
        
        print(f"\n  Uploaded: {stats['uploaded']}")
        print(f"  Failed: {stats['failed']}")
        print(f"  Skipped: {stats['skipped']}")
        
        # Verify
        verify_upload(db)
        
        print("\n" + "=" * 60)
        print("UPLOAD COMPLETE")
        print("=" * 60)
        
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()