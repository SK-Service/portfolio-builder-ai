"""
Test Script: Full Agent Flow
Tests the complete agent workflow: Claude API + Tools + Firestore

"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

# Verify required environment variables
required_vars = ['GOOGLE_APPLICATION_CREDENTIALS', 'ANTHROPIC_API_KEY']
missing = [v for v in required_vars if not os.getenv(v)]
if missing:
    print(f"ERROR: Missing environment variables: {missing}")
    print("Add them to your .env file")
    sys.exit(1)

cred_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
if not Path(cred_path).exists():
    print(f"ERROR: Credentials file not found: {cred_path}")
    sys.exit(1)

print("Environment variables loaded")
print(f"  GOOGLE_APPLICATION_CREDENTIALS: {cred_path}")
print(f"  ANTHROPIC_API_KEY: {os.getenv('ANTHROPIC_API_KEY')[:10]}...")

# Initialize Firebase BEFORE importing agent
from firebase_admin import credentials, initialize_app

try:
    cred = credentials.Certificate(cred_path)
    initialize_app(cred)
    print("  Firebase: Initialized")
except ValueError as e:
    # Already initialized (from previous run)
    if "already exists" in str(e):
        print("  Firebase: Already initialized")
    else:
        raise

# Now import agent
from src.agent.anthropic_service import AnthropicService


def test_portfolio_generation(
    risk_tolerance: str = "Medium",
    country: str = "USA",
    investment_amount: float = 10000.0,
    investment_horizon_years: int = 5,
    currency: str = "USD"
):
    """Test full portfolio generation."""
    
    print("\n" + "=" * 70)
    print("FULL AGENT TEST: Portfolio Generation")
    print("=" * 70)
    
    print(f"\nTest Parameters:")
    print(f"  Risk Tolerance: {risk_tolerance}")
    print(f"  Country: {country}")
    print(f"  Investment Amount: {currency} {investment_amount:,.2f}")
    print(f"  Investment Horizon: {investment_horizon_years} years")
    
    # Initialize service
    # Note: alpha_vantage_key and fred_key are for macro tool, 
    # Firestore tools don't need API keys
    print("\nInitializing AnthropicService...")
    
    alpha_vantage_key = os.getenv('ALPHA_VANTAGE_API_KEY', '')
    fred_key = os.getenv('FRED_API_KEY', '')
    
    service = AnthropicService(
        alpha_vantage_key=alpha_vantage_key,
        fred_key=fred_key
    )
    print(f"  Registered tools: {[t['name'] for t in service.tool_registry.get_anthropic_tools()]}")
    
    # Generate portfolio
    print("\nCalling Claude API with tools...")
    print("(This may take 30-60 seconds as Claude analyzes data)\n")
    
    start_time = datetime.now()
    
    try:
        portfolio = service.generate_portfolio(
            risk_tolerance=risk_tolerance,
            investment_horizon_years=investment_horizon_years,
            country=country,
            investment_amount=investment_amount,
            currency=currency
        )
        
        elapsed = (datetime.now() - start_time).total_seconds()
        
        print("=" * 70)
        print("PORTFOLIO GENERATED SUCCESSFULLY")
        print("=" * 70)
        print(f"Time elapsed: {elapsed:.1f} seconds\n")
        
        # Display results
        print("RECOMMENDATIONS:")
        print("-" * 50)
        total_allocation = 0
        for rec in portfolio['recommendations']:
            print(f"  {rec['symbol']:8} | {rec['companyName'][:30]:30} | {rec['allocation']:5.1f}% | {rec['sector']}")
            total_allocation += rec['allocation']
        
        print("-" * 50)
        print(f"  Total Allocation: {total_allocation:.1f}%")
        print(f"  Expected Return: {portfolio['totalExpectedReturn']:.1f}%")
        print(f"  Risk Score: {portfolio['riskScore']:.0f}/100")
        
        # Projected growth
        print(f"\nPROJECTED GROWTH:")
        growth = portfolio['projectedGrowth']
        print(f"  Year 0: {currency} {growth[0]['projectedValue']:,.2f}")
        if len(growth) > 1:
            mid = len(growth) // 2
            print(f"  Year {growth[mid]['year']}: {currency} {growth[mid]['projectedValue']:,.2f}")
        print(f"  Year {growth[-1]['year']}: {currency} {growth[-1]['projectedValue']:,.2f}")
        
        # Validation
        print(f"\nVALIDATION:")
        issues = []
        
        if abs(total_allocation - 100.0) > 0.5:
            issues.append(f"Allocation sum is {total_allocation:.1f}%, should be 100%")
        
        if len(portfolio['recommendations']) < 4:
            issues.append(f"Only {len(portfolio['recommendations'])} stocks, expected 4-6")
        
        if portfolio['riskScore'] < 0 or portfolio['riskScore'] > 100:
            issues.append(f"Risk score {portfolio['riskScore']} out of range 0-100")
        
        if issues:
            print("  Issues found:")
            for issue in issues:
                print(f"    - {issue}")
        else:
            print("  ✓ All validations passed")
        
        # Save result
        output_file = Path(__file__).parent / "test_portfolio_result.json"
        with open(output_file, 'w') as f:
            json.dump(portfolio, f, indent=2)
        print(f"\nFull result saved to: {output_file}")
        
        return True
        
    except Exception as e:
        elapsed = (datetime.now() - start_time).total_seconds()
        print(f"\nERROR after {elapsed:.1f} seconds: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("=" * 70)
    print("AGENT FULL FLOW TEST")
    print("=" * 70)
    print()
    
    proceed = input("Run test? (yes/no): ")
    if proceed.lower() != 'yes':
        print("Aborted")
        return
    
    # Test with Medium risk, USA
    success = test_portfolio_generation(
        risk_tolerance="Medium",
        country="USA",
        investment_amount=10000.0,
        investment_horizon_years=5,
        currency="USD"
    )
    
    print("\n" + "=" * 70)
    if success:
        print("TEST PASSED ✓")
        print("=" * 70)
    else:
        print("TEST FAILED ✗")
        print("=" * 70)


if __name__ == "__main__":
    main()