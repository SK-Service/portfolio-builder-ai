"""
Test macro data tool for all countries.
Quick validation without full portfolio generation.
"""

from config import config
from src.agent.tools import ToolRegistry

print("="*70)
print("MACRO DATA TOOL TEST - ALL COUNTRIES")
print("="*70)

# Initialize tool registry
print("\nInitializing tools...")
registry = ToolRegistry(
    alpha_vantage_key=config.alpha_vantage_api_key,
    fred_key=config.fred_api_key
)
print("Tools initialized")

# Test each country
countries = ["USA", "Canada", "EU", "India"]

for country in countries:
    print(f"\n{'='*70}")
    print(f"TESTING: {country}")
    print(f"{'='*70}")
    
    try:
        result = registry.execute_tool("get_macro_economic_data", country=country)
        
        if result.get('success'):
            print("SUCCESS")
            
            data = result.get('data', {})
            print(f"Country: {data.get('country')}")
            print(f"Data source: {data.get('data_source')}")
            print(f"From cache: {result.get('from_cache', False)}")
            
            indicators = data.get('indicators', {})
            print(f"\nIndicators retrieved: {len(indicators)}")
            
            for ind_name, ind_data in indicators.items():
                print(f"  {ind_name}:")
                print(f"    Value: {ind_data.get('value')}%")
                print(f"    Period: {ind_data.get('period')}")
                print(f"    Description: {ind_data.get('description')}")
            
            context = data.get('economic_context', 'N/A')
            print(f"\nEconomic context: {context}")
            
            # Validation checks
            print(f"\nVALIDATION:")
            checks = []
            
            if 'gdp_growth' in indicators:
                gdp = indicators['gdp_growth']['value']
                if -5 < gdp < 15:
                    checks.append(("GDP growth reasonable (-5% to 15%)", True))
                else:
                    checks.append((f"GDP growth suspicious: {gdp}%", False))
            else:
                checks.append(("GDP data missing", False))
            
            if 'inflation' in indicators:
                inf = indicators['inflation']['value']
                if -2 < inf < 20:
                    checks.append(("Inflation reasonable (-2% to 20%)", True))
                else:
                    checks.append((f"Inflation suspicious: {inf}%", False))
            else:
                checks.append(("Inflation data missing", False))
            
            if 'unemployment' in indicators:
                unemp = indicators['unemployment']['value']
                if 0 < unemp < 30:
                    checks.append(("Unemployment reasonable (0% to 30%)", True))
                else:
                    checks.append((f"Unemployment suspicious: {unemp}%", False))
            else:
                checks.append(("Unemployment data missing", False))
            
            # Check dates are recent (within last 2 years)
            from datetime import datetime
            current_year = datetime.now().year
            
            for ind_name, ind_data in indicators.items():
                period = ind_data.get('period', '')
                if period:
                    try:
                        year = int(period.split('-')[0])
                        if current_year - year <= 2:
                            checks.append((f"{ind_name} date recent ({year})", True))
                        else:
                            checks.append((f"{ind_name} date old ({year})", False))
                    except:
                        checks.append((f"{ind_name} date parse failed", False))
            
            all_passed = True
            for check_msg, passed in checks:
                status = "PASS" if passed else "FAIL"
                print(f"  [{status}] {check_msg}")
                if not passed:
                    all_passed = False
            
            if all_passed:
                print(f"\nOVERALL: PASS")
            else:
                print(f"\nOVERALL: FAIL - Review issues above")
        
        else:
            print("FAILED")
            print(f"Error: {result.get('error')}")
            print(f"Error code: {result.get('error_code')}")
            print(f"User message: {result.get('user_message')}")
            
            # Check for stale cache warning
            if 'warning' in result:
                warning = result['warning']
                print(f"\nWarning: {warning.get('user_message')}")
                print("Using stale cached data as fallback")
        
    except Exception as e:
        print(f"EXCEPTION: {e}")
        import traceback
        traceback.print_exc()
    
    # Pause between countries to avoid rate limits
    if country != countries[-1]:
        import time
        print("\nWaiting 15 seconds before next country (rate limit)...")
        time.sleep(15)

print("\n" + "="*70)
print("MACRO DATA TEST COMPLETE")
print("="*70)