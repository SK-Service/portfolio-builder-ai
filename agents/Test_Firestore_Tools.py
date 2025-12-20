"""
Test Script: Verify Firestore Tools
Run this to confirm stock_fundamentals_tool and stock_universe_tool 
can read from production Firestore.

Prerequisites:
1. GOOGLE_APPLICATION_CREDENTIALS set in .env
2. Fundamentals uploaded to Firestore
3. firebase-admin installed

Usage:
    python test_firestore_tools.py
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

# Verify credentials
cred_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
if not cred_path:
    print("ERROR: GOOGLE_APPLICATION_CREDENTIALS not set in .env")
    sys.exit(1)

if not Path(cred_path).exists():
    print(f"ERROR: Credentials file not found: {cred_path}")
    sys.exit(1)

print(f"Using credentials: {cred_path}")

# Initialize Firebase BEFORE importing tools
from firebase_admin import credentials, initialize_app

try:
    cred = credentials.Certificate(cred_path)
    initialize_app(cred)
    print("Firebase initialized successfully\n")
except Exception as e:
    print(f"Firebase initialization error: {e}")
    sys.exit(1)

# Now import tools (they expect Firebase to be initialized)
from src.agent.tools.stock_fundamentals_tool import StockFundamentalsTool
from src.agent.tools.stock_universe_tool import StockUniverseTool


def test_stock_universe_tool():
    """Test StockUniverseTool reads from Firestore."""
    print("=" * 60)
    print("TEST 1: StockUniverseTool")
    print("=" * 60)
    
    tool = StockUniverseTool()
    print(f"Tool name: {tool.name}")
    print(f"Collection: stock_universe")
    
    # Test 1a: Get all sectors for USA
    print("\n[1a] Getting all stocks for USA...")
    result = tool.execute(country="USA")
    
    if result.get('success'):
        data = result['data']
        print(f"  Country: {data['country']}")
        print(f"  Sectors returned: {len(data['sectors_returned'])}")
        print(f"  Total stocks: {data['total_stocks']}")
        print(f"  Sectors: {', '.join(data['sectors_returned'])}")
        
        # Show sample from first sector
        first_sector = data['sectors_returned'][0]
        stocks = data['stocks_by_sector'].get(first_sector, [])
        print(f"\n  Sample from {first_sector}: {[s['symbol'] for s in stocks[:3]]}")
    else:
        print(f"  ERROR: {result}")
        return False
    
    # Test 1b: Get specific sectors for India
    print("\n[1b] Getting technology + finance for India...")
    result = tool.execute(country="India", sectors=["technology", "finance"])
    
    if result.get('success'):
        data = result['data']
        print(f"  Sectors: {data['sectors_returned']}")
        print(f"  Total stocks: {data['total_stocks']}")
    else:
        print(f"  ERROR: {result}")
    
    print("\n✓ StockUniverseTool working!")
    return True


def test_stock_fundamentals_tool():
    """Test StockFundamentalsTool reads from Firestore."""
    print("\n" + "=" * 60)
    print("TEST 2: StockFundamentalsTool")
    print("=" * 60)
    
    tool = StockFundamentalsTool()
    print(f"Tool name: {tool.name}")
    print(f"Collection: stock_fundamentals")
    
    # Test with known symbols (adjust based on what you uploaded)
    test_symbols = ['AAPL', 'MSFT', 'GOOGL', 'RELIANCE', 'HDFCBANK']
    
    print(f"\n[2a] Fetching fundamentals for: {test_symbols}")
    result = tool.execute(symbols=test_symbols)
    
    if result.get('success'):
        data = result['data']
        print(f"  Symbols requested: {data['symbols_requested']}")
        print(f"  Symbols found: {data['symbols_found']}")
        
        # Show details for first found stock
        fundamentals = data['fundamentals']
        for symbol, details in list(fundamentals.items())[:2]:
            print(f"\n  {symbol}:")
            print(f"    Name: {details.get('name', 'N/A')}")
            print(f"    Country: {details.get('country', 'N/A')}")
            print(f"    Sector: {details.get('sector', 'N/A')}")
            print(f"    Currency: {details.get('currency', 'N/A')}")
            print(f"    PE Ratio: {details.get('pe_ratio', 'N/A')}")
            print(f"    Market Cap: {details.get('market_cap', 'N/A')}")
            print(f"    ROE: {details.get('return_on_equity', 'N/A')}")
            print(f"    Dividend Yield: {details.get('dividend_yield', 'N/A')}")
        
        if result.get('warning'):
            print(f"\n  Warning: {result['warning']['message']}")
    else:
        print(f"  ERROR: {result}")
        return False
    
    print("\n✓ StockFundamentalsTool working!")
    return True


def main():
    print("=" * 60)
    print("FIRESTORE TOOLS TEST")
    print("=" * 60)
    print("Testing tools against production Firestore...\n")
    
    success = True
    
    try:
        if not test_stock_universe_tool():
            success = False
    except Exception as e:
        print(f"StockUniverseTool test failed: {e}")
        import traceback
        traceback.print_exc()
        success = False
    
    try:
        if not test_stock_fundamentals_tool():
            success = False
    except Exception as e:
        print(f"StockFundamentalsTool test failed: {e}")
        import traceback
        traceback.print_exc()
        success = False
    
    print("\n" + "=" * 60)
    if success:
        print("ALL TESTS PASSED ✓")
        print("=" * 60)
    else:
        print("SOME TESTS FAILED ✗")
        print("=" * 60)
        print("\nCheck the errors above and verify:")
        print("1. Firestore data was uploaded correctly")
        print("2. Collection names match (stock_universe, stock_fundamentals)")
        print("3. Firebase credentials are valid")


if __name__ == "__main__":
    main()