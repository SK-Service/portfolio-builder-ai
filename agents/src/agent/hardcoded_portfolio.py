"""
Hardcoded portfolio generator for testing and fallback.
"""

from typing import Dict, Any, List
from datetime import datetime, timezone


def generate_hardcoded_portfolio(
    risk_tolerance: str,
    investment_horizon_years: int,
    country: str,
    investment_amount: float
) -> Dict[str, Any]:
    """Generate a hardcoded portfolio for testing/fallback."""
    
    portfolios_by_risk = {
        'Low': {
            'recommendations': [
                {'symbol': 'JNJ', 'companyName': 'Johnson & Johnson', 'allocation': 25.0, 'expectedReturn': 7.5, 'sector': 'Healthcare', 'country': country},
                {'symbol': 'PG', 'companyName': 'Procter & Gamble', 'allocation': 25.0, 'expectedReturn': 8.0, 'sector': 'Consumer Goods', 'country': country},
                {'symbol': 'KO', 'companyName': 'Coca-Cola', 'allocation': 25.0, 'expectedReturn': 7.8, 'sector': 'Consumer Goods', 'country': country},
                {'symbol': 'WMT', 'companyName': 'Walmart', 'allocation': 25.0, 'expectedReturn': 7.2, 'sector': 'Retail', 'country': country}
            ],
            'totalExpectedReturn': 7.6,
            'riskScore': 32.0
        },
        'Medium': {
            'recommendations': [
                {'symbol': 'AAPL', 'companyName': 'Apple Inc.', 'allocation': 30.0, 'expectedReturn': 12.5, 'sector': 'Technology', 'country': country},
                {'symbol': 'MSFT', 'companyName': 'Microsoft', 'allocation': 25.0, 'expectedReturn': 11.8, 'sector': 'Technology', 'country': country},
                {'symbol': 'JPM', 'companyName': 'JPMorgan Chase', 'allocation': 25.0, 'expectedReturn': 9.2, 'sector': 'Financial', 'country': country},
                {'symbol': 'JNJ', 'companyName': 'Johnson & Johnson', 'allocation': 20.0, 'expectedReturn': 7.5, 'sector': 'Healthcare', 'country': country}
            ],
            'totalExpectedReturn': 10.5,
            'riskScore': 58.0
        },
        'High': {
            'recommendations': [
                {'symbol': 'TSLA', 'companyName': 'Tesla', 'allocation': 35.0, 'expectedReturn': 18.5, 'sector': 'Automotive', 'country': country},
                {'symbol': 'NVDA', 'companyName': 'NVIDIA', 'allocation': 30.0, 'expectedReturn': 22.0, 'sector': 'Technology', 'country': country},
                {'symbol': 'AMZN', 'companyName': 'Amazon', 'allocation': 20.0, 'expectedReturn': 14.1, 'sector': 'E-commerce', 'country': country},
                {'symbol': 'META', 'companyName': 'Meta Platforms', 'allocation': 15.0, 'expectedReturn': 15.8, 'sector': 'Technology', 'country': country}
            ],
            'totalExpectedReturn': 18.2,
            'riskScore': 81.0
        }
    }
    
    portfolio_template = portfolios_by_risk.get(risk_tolerance, portfolios_by_risk['Medium'])
    
    # Calculate projected growth
    projected_growth = []
    annual_return = portfolio_template['totalExpectedReturn'] / 100
    
    for year in range(investment_horizon_years + 1):
        projected_value = investment_amount * ((1 + annual_return) ** year)
        projected_growth.append({
            'year': year,
            'projectedValue': round(projected_value, 2)
        })
    
    return {
        'recommendations': portfolio_template['recommendations'],
        'totalExpectedReturn': portfolio_template['totalExpectedReturn'],
        'riskScore': portfolio_template['riskScore'],
        'projectedGrowth': projected_growth,
        'generatedAt': datetime.now(timezone.utc).isoformat(),
        'error': None
    }