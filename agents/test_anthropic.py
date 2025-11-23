"""
Test script to verify Anthropic API connectivity.
Run: python test_anthropic.py
"""

from src.agent.anthropic_service import AnthropicService
from config import config
import json


def test_connection():
    """Test basic Anthropic API connection."""
    print("Testing Anthropic Claude API connection...")
    print(f"Model: {config.anthropic_model}")
    print(f"Max Tokens: {config.anthropic_max_tokens}")
    print("-" * 50)
    
    try:
        service = AnthropicService()
        
        # Test with sample parameters
        portfolio = service.generate_portfolio(
            risk_tolerance="Medium",
            investment_horizon_years=10,
            country="USA",
            investment_amount=10000.0,
            currency="USD"
        )
        
        print("\n✅ SUCCESS! Claude API connection working.")
        print("\nGenerated Portfolio:")
        print(json.dumps(portfolio, indent=2))
        
    except Exception as e:
        print(f"\n❌ FAILED: {type(e).__name__}: {e}")
        return False
    
    return True


if __name__ == "__main__":
    success = test_connection()
    exit(0 if success else 1)