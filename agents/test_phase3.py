"""
Phase 3 Integration Test Script
Tests tool infrastructure and macro data retrieval.
"""

import json
import sys
from datetime import datetime

print("="*70)
print("PHASE 3 INTEGRATION TEST")
print("="*70)

# Test 1: Imports
print("\n[TEST 1] Verifying imports...")
try:
    from config import config
    from src.agent.anthropic_service import AnthropicService
    from src.agent.tools import ToolRegistry
    print("All imports successful")
except Exception as e:
    print(f"Import failed: {e}")
    sys.exit(1)

# Test 2: Configuration
print("\n[TEST 2] Verifying configuration...")
try:
    assert hasattr(config, 'alpha_vantage_api_key'), "Missing alpha_vantage_api_key"
    assert hasattr(config, 'fred_api_key'), "Missing fred_api_key"
    assert len(config.alpha_vantage_api_key) > 5, "Alpha Vantage key too short"
    assert len(config.fred_api_key) > 5, "FRED key too short"
    print(f"Configuration valid")
    print(f"   - Alpha Vantage key: {config.alpha_vantage_api_key[:5]}...{config.alpha_vantage_api_key[-3:]}")
    print(f"   - FRED key: {config.fred_api_key[:5]}...{config.fred_api_key[-3:]}")
except AssertionError as e:
    print(f"Configuration error: {e}")
    sys.exit(1)

# Test 3: Tool Registry Initialization
print("\n[TEST 3] Initializing tool registry...")
try:
    registry = ToolRegistry(
        alpha_vantage_key=config.alpha_vantage_api_key,
        fred_key=config.fred_api_key
    )
    tools = registry.get_all_tools()
    print(f"Tool registry initialized")
    print(f"   - Available tools: {len(tools)}")
    for tool in tools:
        print(f"     • {tool.name}")
except Exception as e:
    print(f"Tool registry initialization failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 4: Direct Tool Execution (Macro Data)
print("\n[TEST 4] Testing macro data tool directly...")
try:
    result = registry.execute_tool("get_macro_economic_data", country="USA")
    print(f"Tool executed")
    print(f"   - Success: {result.get('success')}")
    print(f"   - From cache: {result.get('from_cache', False)}")
    
    if result.get('success'):
        data = result.get('data', {})
        print(f"   - Country: {data.get('country')}")
        print(f"   - Data source: {data.get('data_source')}")
        indicators = data.get('indicators', {})
        print(f"   - Indicators retrieved: {len(indicators)}")
        for ind_name, ind_data in indicators.items():
            print(f"     • {ind_name}: {ind_data.get('value')}% ({ind_data.get('period')})")
    else:
        print(f"   - Error: {result.get('error')}")
        print(f"   - Error code: {result.get('error_code')}")
        
except Exception as e:
    print(f"Tool execution failed: {e}")
    import traceback
    traceback.print_exc()

# Test 5: AnthropicService Initialization
print("\n[TEST 5] Initializing AnthropicService...")
try:
    service = AnthropicService(
        alpha_vantage_key=config.alpha_vantage_api_key,
        fred_key=config.fred_api_key
    )
    print(f"AnthropicService initialized")
    print(f"   - Model: {service.model}")
    print(f"   - Max tokens: {service.max_tokens}")
    print(f"   - Tools available: {len(service.tool_registry.get_all_tools())}")
except Exception as e:
    print(f"AnthropicService initialization failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 6: End-to-End Portfolio Generation
print("\n[TEST 6] Testing end-to-end portfolio generation...")
print("This will call Claude API (costs ~$0.15) and external APIs")
print("May take 20-40 seconds due to API rate limiting")

user_input = input("\nProceed with full test? (y/N): ")
if user_input.lower() != 'y':
    print("Skipped full test")
    print("\n" + "="*70)
    print("INTEGRATION TEST COMPLETE - Partial")
    print("="*70)
    sys.exit(0)

try:
    print("\nGenerating portfolio...")
    start_time = datetime.now()
    
    portfolio = service.generate_portfolio(
        risk_tolerance="Medium",
        investment_horizon_years=10,
        country="USA",
        investment_amount=50000,
        currency="USD"
    )
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    print(f"Portfolio generated in {duration:.1f} seconds")
    print(f"\n{'-'*70}")
    print("PORTFOLIO SUMMARY")
    print(f"{'-'*70}")
    print(f"Stocks: {len(portfolio['recommendations'])}")
    print(f"Expected Return: {portfolio['totalExpectedReturn']:.1f}%")
    print(f"Risk Score: {portfolio['riskScore']}")
    print(f"\nRecommendations:")
    
    total_allocation = 0
    for rec in portfolio['recommendations']:
        print(f"  • {rec['symbol']:6s} - {rec['companyName']:30s}")
        print(f"    Allocation: {rec['allocation']:5.1f}%  |  Sector: {rec['sector']:20s}  |  Expected: {rec['expectedReturn']:5.1f}%")
        total_allocation += rec['allocation']
    
    print(f"\n{'─'*70}")
    print(f"Total Allocation: {total_allocation:.1f}% (should be 100.0%)")
    
    # Validation checks
    print(f"\n{'-'*70}")
    print("VALIDATION CHECKS")
    print(f"{'-'*70}")
    
    checks = {
        "Allocation sums to 100%": abs(total_allocation - 100.0) < 0.1,
        "Has 4-6 stocks": 4 <= len(portfolio['recommendations']) <= 6,
        "Risk score in range": 0 <= portfolio['riskScore'] <= 100,
        "Expected return reasonable": 5 <= portfolio['totalExpectedReturn'] <= 25,
        "Projected growth present": 'projectedGrowth' in portfolio and len(portfolio['projectedGrowth']) > 0
    }
    
    all_passed = True
    for check_name, passed in checks.items():
        status = "PASSED" if passed else "FAILED"
        print(f"{status} {check_name}")
        if not passed:
            all_passed = False
    
    if all_passed:
        print(f"\nALL VALIDATION CHECKS PASSED")
    else:
        print(f"\n  SOME CHECKS FAILED")
    
    # Save to file
    output_file = f"test_portfolio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(portfolio, f, indent=2)
    print(f"\n Full portfolio saved to: {output_file}")
    
except Exception as e:
    print(f" Portfolio generation failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "="*70)
print("PHASE 3 INTEGRATION TEST COMPLETE - FULL SUCCESS ")