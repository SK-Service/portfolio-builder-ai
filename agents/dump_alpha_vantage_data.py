"""
Dump raw Alpha Vantage API responses to files for review.
"""

import requests
import json
from config import config

print("Fetching Alpha Vantage data...")
print(f"API Key: {config.alpha_vantage_api_key[:5]}...{config.alpha_vantage_api_key[-3:]}")

base_url = "https://www.alphavantage.co/query"

# Function to fetch and save
def fetch_and_save(function_name, filename):
    print(f"\nFetching {function_name}...")
    try:
        response = requests.get(
            base_url,
            params={
                "function": function_name,
                "apikey": config.alpha_vantage_api_key
            },
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        
        # Save to file
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"Saved to {filename}")
        
        # Print first few data points
        if "data" in data:
            print(f"Total data points: {len(data['data'])}")
            print("First 3 entries (index 0, 1, 2):")
            for i in range(min(3, len(data['data']))):
                item = data['data'][i]
                print(f"  [{i}] date: {item.get('date')}, value: {item.get('value')}")
            print("Last 3 entries:")
            for i in range(max(0, len(data['data'])-3), len(data['data'])):
                item = data['data'][i]
                print(f"  [{i}] date: {item.get('date')}, value: {item.get('value')}")
        else:
            print(f"Response keys: {list(data.keys())}")
            print(f"Full response: {data}")
        
        import time
        time.sleep(12)  # Rate limit
        
    except Exception as e:
        print(f"Error fetching {function_name}: {e}")

# Fetch all three indicators
fetch_and_save("REAL_GDP", "alpha_vantage_gdp.json")
fetch_and_save("INFLATION", "alpha_vantage_inflation.json")
fetch_and_save("UNEMPLOYMENT", "alpha_vantage_unemployment.json")

print("\nDone! Review the generated JSON files:")
print("  - alpha_vantage_gdp.json")
print("  - alpha_vantage_inflation.json")
print("  - alpha_vantage_unemployment.json")