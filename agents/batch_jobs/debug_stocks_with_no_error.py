"""
Debug script to test parsing of Indian stocks.
Run this to see what's happening with the API responses.
"""

import requests
import json
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from parent directory
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

API_KEY = os.getenv('TWELVE_DATA_API_KEY')

if not API_KEY:
    print("ERROR: TWELVE_DATA_API_KEY not found in .env")
    exit(1)

print(f"API Key: {API_KEY[:4]}...{API_KEY[-4:]}")

# Test Indian stocks
test_stocks = [
    {"symbol": "MARUTI", "exchange": "XNSE"},
    {"symbol": "TATAMOTORS", "exchange": "XNSE"},
    {"symbol": "RELIANCE", "exchange": "XNSE"},
    {"symbol": "ITC", "exchange": "XNSE"},
    {"symbol": "HINDUNILVR", "exchange": "XNSE"},
    {"symbol": "BRITANNIA", "exchange": "XNSE"},
]

batch_uri = "https://api.twelvedata.com/batch"
headers = {
    "Content-Type": "application/json",
    "Authorization": f"apikey {API_KEY}"
}

# Build batch request
requests_dict = {}
for idx, stock in enumerate(test_stocks, 1):
    req_id = f"req_{idx}"
    url = f"/statistics?symbol={stock['symbol']}&mic_code={stock['exchange']}&apikey={API_KEY}"
    requests_dict[req_id] = {"url": url}

print(f"\nSending batch request for {len(test_stocks)} Indian stocks...")
print(f"Request IDs: {list(requests_dict.keys())}")

response = requests.post(batch_uri, headers=headers, json=requests_dict, timeout=60)
response.encoding = 'utf-8'

print(f"\nStatus: {response.status_code}")
print(f"Response length: {len(response.text)} characters")

# Save raw response
with open("debug_india_response.txt", "w", encoding="utf-8") as f:
    f.write(response.text)
print("Raw response saved to debug_india_response.txt")

# Try parsing
try:
    data = json.loads(response.text)
    print("\nJSON parsing: SUCCESS")
    print(f"Top-level keys: {list(data.keys())}")
    
    # Check structure
    if 'data' in data:
        batch_data = data['data']
        print(f"data keys: {list(batch_data.keys())}")
    else:
        batch_data = data
        print("No 'data' wrapper, using response directly")
    
    # Process each request
    for req_id in sorted(batch_data.keys()):
        if not req_id.startswith('req_'):
            continue
            
        req_response = batch_data[req_id]
        stock_idx = int(req_id.split('_')[1]) - 1
        symbol = test_stocks[stock_idx]['symbol']
        
        print(f"\n{'='*50}")
        print(f"Stock: {symbol} ({req_id})")
        print(f"{'='*50}")
        
        if not isinstance(req_response, dict):
            print(f"  ERROR: Response is not a dict, type: {type(req_response)}")
            continue
        
        print(f"  Response keys: {list(req_response.keys())}")
        print(f"  Status: {req_response.get('status', 'N/A')}")
        
        if req_response.get('status') == 'error':
            print(f"  Error: {req_response.get('message', 'Unknown')}")
            continue
        
        # Navigate to response
        if 'response' in req_response:
            inner = req_response['response']
            print(f"  Inner response keys: {list(inner.keys())}")
            
            if 'statistics' in inner:
                stats = inner['statistics']
                print(f"  Statistics keys: {list(stats.keys())}")
                
                if 'valuations_metrics' in stats:
                    valuations = stats['valuations_metrics']
                    print(f"  Valuations keys: {list(valuations.keys())}")
                    print(f"  PE: {valuations.get('trailing_pe')}")
                    print(f"  Market Cap: {valuations.get('market_capitalization')}")
                else:
                    print("  NO valuations_metrics!")
            else:
                print("  NO statistics key!")
        else:
            print("  NO response key!")
            print(f"  Available: {list(req_response.keys())}")

except json.JSONDecodeError as e:
    print(f"\nJSON parsing: FAILED at position {e.pos}")
    print(f"Error: {e.msg}")
    
    # Show context
    raw = response.text
    start = max(0, e.pos - 100)
    end = min(len(raw), e.pos + 100)
    print(f"\nContext around error:")
    print(f"...{raw[start:e.pos]}<<<ERROR>>>{raw[e.pos:end]}...")