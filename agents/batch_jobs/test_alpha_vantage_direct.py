"""Test Alpha Vantage API directly to see actual responses."""
import os
import requests
import json

api_key = os.getenv('ALPHA_VANTAGE_API_KEY')

symbols = ['AMZN', 'TSLA', 'AAPL', 'MSFT']

for symbol in symbols:
    print(f"\n{'='*70}")
    print(f"Testing: {symbol}")
    print('='*70)
    
    response = requests.get(
        "https://www.alphavantage.co/query",
        params={
            "function": "OVERVIEW",
            "symbol": symbol,
            "apikey": api_key
        },
        timeout=10
    )
    
    data = response.json()
    
    print(f"Status Code: {response.status_code}")
    print(f"Response keys: {list(data.keys())}")
    
    if "Note" in data:
        print(f"RATE LIMIT: {data['Note']}")
    elif "Error Message" in data:
        print(f"ERROR: {data['Error Message']}")
    elif "Symbol" in data:
        print(f"SUCCESS: {data['Symbol']} - {data.get('Name')}")
    else:
        print("UNEXPECTED RESPONSE:")
        print(json.dumps(data, indent=2)[:500])