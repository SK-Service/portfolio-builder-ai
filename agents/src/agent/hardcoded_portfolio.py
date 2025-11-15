from datetime import datetime, timezone
from ..models.dto import (
    PortfolioRecommendationDto,
    StockRecommendationDto,
    ProjectedGrowthDto,
    GeneratePortfolioRequestDto,
    RiskTolerance,
    Country
)


def generate_hardcoded_portfolio(request_data: GeneratePortfolioRequestDto) -> PortfolioRecommendationDto:
    """
    Generate a hardcoded portfolio based on user input.
    This is Phase 1 skeleton - will be replaced with real agent logic later.
    
    Args:
        request_data: User's portfolio requirements
        
    Returns:
        Complete portfolio recommendation
    """
    
    # Select stocks based on country and risk profile
    stocks = _get_stocks_for_profile(request_data.country, request_data.riskTolerance)
    
    # Calculate total expected return based on risk
    total_return = _calculate_expected_return(request_data.riskTolerance)
    
    # Calculate risk score
    risk_score = _calculate_risk_score(request_data.riskTolerance)
    
    # Generate projected growth
    projected_growth = _calculate_projected_growth(
        request_data.investmentAmount,
        total_return,
        request_data.investmentHorizonYears
    )
    
    # Create portfolio recommendation
    portfolio = PortfolioRecommendationDto(
        recommendations=stocks,
        totalExpectedReturn=total_return,
        riskScore=risk_score,
        projectedGrowth=projected_growth,
        generatedAt=datetime.now(timezone.utc).isoformat(),
        error=None
    )
    
    return portfolio


def _get_stocks_for_profile(country: Country, risk: RiskTolerance) -> list[StockRecommendationDto]:
    """
    Return hardcoded stock recommendations based on country and risk profile.
    """
    
    # Define stock pools by country
    usa_stocks = {
        'conservative': [
            StockRecommendationDto(symbol="JNJ", companyName="Johnson & Johnson", allocation=30.0, expectedReturn=8.5, sector="Healthcare", country="USA"),
            StockRecommendationDto(symbol="PG", companyName="Procter & Gamble", allocation=25.0, expectedReturn=7.8, sector="Consumer Staples", country="USA"),
            StockRecommendationDto(symbol="KO", companyName="Coca-Cola", allocation=25.0, expectedReturn=7.2, sector="Consumer Staples", country="USA"),
            StockRecommendationDto(symbol="VZ", companyName="Verizon", allocation=20.0, expectedReturn=6.5, sector="Utilities", country="USA"),
        ],
        'moderate': [
            StockRecommendationDto(symbol="AAPL", companyName="Apple Inc.", allocation=28.0, expectedReturn=12.5, sector="Technology", country="USA"),
            StockRecommendationDto(symbol="MSFT", companyName="Microsoft Corporation", allocation=27.0, expectedReturn=11.8, sector="Technology", country="USA"),
            StockRecommendationDto(symbol="JPM", companyName="JPMorgan Chase & Co.", allocation=25.0, expectedReturn=9.2, sector="Financial Services", country="USA"),
            StockRecommendationDto(symbol="JNJ", companyName="Johnson & Johnson", allocation=20.0, expectedReturn=8.5, sector="Healthcare", country="USA"),
        ],
        'aggressive': [
            StockRecommendationDto(symbol="TSLA", companyName="Tesla Inc.", allocation=35.0, expectedReturn=21.3, sector="Automotive", country="USA"),
            StockRecommendationDto(symbol="NVDA", companyName="NVIDIA Corporation", allocation=30.0, expectedReturn=24.5, sector="Technology", country="USA"),
            StockRecommendationDto(symbol="GOOGL", companyName="Alphabet Inc.", allocation=20.0, expectedReturn=15.2, sector="Technology", country="USA"),
            StockRecommendationDto(symbol="AMZN", companyName="Amazon.com Inc.", allocation=15.0, expectedReturn=16.8, sector="Consumer Discretionary", country="USA"),
        ]
    }
    
    canada_stocks = {
        'conservative': [
            StockRecommendationDto(symbol="RY.TO", companyName="Royal Bank of Canada", allocation=30.0, expectedReturn=8.0, sector="Financial Services", country="Canada"),
            StockRecommendationDto(symbol="ENB.TO", companyName="Enbridge Inc.", allocation=28.0, expectedReturn=7.5, sector="Energy", country="Canada"),
            StockRecommendationDto(symbol="FTS.TO", companyName="Fortis Inc.", allocation=22.0, expectedReturn=6.8, sector="Utilities", country="Canada"),
            StockRecommendationDto(symbol="BCE.TO", companyName="BCE Inc.", allocation=20.0, expectedReturn=6.5, sector="Telecommunications", country="Canada"),
        ],
        'moderate': [
            StockRecommendationDto(symbol="SHOP.TO", companyName="Shopify Inc.", allocation=30.0, expectedReturn=14.2, sector="Technology", country="Canada"),
            StockRecommendationDto(symbol="RY.TO", companyName="Royal Bank of Canada", allocation=25.0, expectedReturn=8.0, sector="Financial Services", country="Canada"),
            StockRecommendationDto(symbol="CNR.TO", companyName="Canadian National Railway", allocation=25.0, expectedReturn=9.5, sector="Industrials", country="Canada"),
            StockRecommendationDto(symbol="ENB.TO", companyName="Enbridge Inc.", allocation=20.0, expectedReturn=7.5, sector="Energy", country="Canada"),
        ],
        'aggressive': [
            StockRecommendationDto(symbol="SHOP.TO", companyName="Shopify Inc.", allocation=40.0, expectedReturn=18.5, sector="Technology", country="Canada"),
            StockRecommendationDto(symbol="LSPD.TO", companyName="Lightspeed Commerce", allocation=30.0, expectedReturn=22.0, sector="Technology", country="Canada"),
            StockRecommendationDto(symbol="SU.TO", companyName="Suncor Energy", allocation=18.0, expectedReturn=12.5, sector="Energy", country="Canada"),
            StockRecommendationDto(symbol="AC.TO", companyName="Air Canada", allocation=12.0, expectedReturn=15.8, sector="Consumer Discretionary", country="Canada"),
        ]
    }
    
    eu_stocks = {
        'conservative': [
            StockRecommendationDto(symbol="NVS", companyName="Novartis AG", allocation=28.0, expectedReturn=7.8, sector="Healthcare", country="EU"),
            StockRecommendationDto(symbol="NESN.SW", companyName="Nestle SA", allocation=27.0, expectedReturn=7.2, sector="Consumer Staples", country="EU"),
            StockRecommendationDto(symbol="OR.PA", companyName="L'Oreal SA", allocation=25.0, expectedReturn=8.5, sector="Consumer Staples", country="EU"),
            StockRecommendationDto(symbol="SAN.MC", companyName="Banco Santander", allocation=20.0, expectedReturn=6.5, sector="Financial Services", country="EU"),
        ],
        'moderate': [
            StockRecommendationDto(symbol="ASML", companyName="ASML Holding", allocation=30.0, expectedReturn=13.5, sector="Technology", country="EU"),
            StockRecommendationDto(symbol="SAP", companyName="SAP SE", allocation=25.0, expectedReturn=11.2, sector="Technology", country="EU"),
            StockRecommendationDto(symbol="SIE.DE", companyName="Siemens AG", allocation=25.0, expectedReturn=10.5, sector="Industrials", country="EU"),
            StockRecommendationDto(symbol="NVS", companyName="Novartis AG", allocation=20.0, expectedReturn=7.8, sector="Healthcare", country="EU"),
        ],
        'aggressive': [
            StockRecommendationDto(symbol="ASML", companyName="ASML Holding", allocation=35.0, expectedReturn=18.5, sector="Technology", country="EU"),
            StockRecommendationDto(symbol="MC.PA", companyName="LVMH", allocation=30.0, expectedReturn=16.8, sector="Consumer Discretionary", country="EU"),
            StockRecommendationDto(symbol="ADS.DE", companyName="Adidas AG", allocation=20.0, expectedReturn=14.2, sector="Consumer Discretionary", country="EU"),
            StockRecommendationDto(symbol="AIR.PA", companyName="Airbus SE", allocation=15.0, expectedReturn=13.5, sector="Industrials", country="EU"),
        ]
    }
    
    india_stocks = {
        'conservative': [
            StockRecommendationDto(symbol="RELIANCE.NS", companyName="Reliance Industries", allocation=28.0, expectedReturn=9.5, sector="Energy", country="India"),
            StockRecommendationDto(symbol="HDFCBANK.NS", companyName="HDFC Bank", allocation=27.0, expectedReturn=10.2, sector="Financial Services", country="India"),
            StockRecommendationDto(symbol="ITC.NS", companyName="ITC Limited", allocation=25.0, expectedReturn=8.5, sector="Consumer Staples", country="India"),
            StockRecommendationDto(symbol="INFY.NS", companyName="Infosys Limited", allocation=20.0, expectedReturn=11.0, sector="Technology", country="India"),
        ],
        'moderate': [
            StockRecommendationDto(symbol="TCS.NS", companyName="Tata Consultancy Services", allocation=28.0, expectedReturn=13.5, sector="Technology", country="India"),
            StockRecommendationDto(symbol="RELIANCE.NS", companyName="Reliance Industries", allocation=27.0, expectedReturn=12.8, sector="Energy", country="India"),
            StockRecommendationDto(symbol="HDFCBANK.NS", companyName="HDFC Bank", allocation=25.0, expectedReturn=11.5, sector="Financial Services", country="India"),
            StockRecommendationDto(symbol="BHARTIARTL.NS", companyName="Bharti Airtel", allocation=20.0, expectedReturn=10.8, sector="Telecommunications", country="India"),
        ],
        'aggressive': [
            StockRecommendationDto(symbol="ADANIENT.NS", companyName="Adani Enterprises", allocation=32.0, expectedReturn=22.5, sector="Conglomerate", country="India"),
            StockRecommendationDto(symbol="TCS.NS", companyName="Tata Consultancy Services", allocation=28.0, expectedReturn=16.8, sector="Technology", country="India"),
            StockRecommendationDto(symbol="TATAMOTORS.NS", companyName="Tata Motors", allocation=24.0, expectedReturn=19.5, sector="Automotive", country="India"),
            StockRecommendationDto(symbol="ZOMATO.NS", companyName="Zomato Limited", allocation=16.0, expectedReturn=24.0, sector="Consumer Discretionary", country="India"),
        ]
    }
    
    # Map country to stock pool
    country_stock_map = {
        Country.USA: usa_stocks,
        Country.CANADA: canada_stocks,
        Country.EU: eu_stocks,
        Country.INDIA: india_stocks,
    }
    
    # Map risk tolerance to stock category
    risk_category_map = {
        RiskTolerance.LOW: 'conservative',
        RiskTolerance.MEDIUM: 'moderate',
        RiskTolerance.HIGH: 'aggressive',
    }
    
    # Get appropriate stocks
    stock_pool = country_stock_map.get(country, usa_stocks)
    category = risk_category_map.get(risk, 'moderate')
    
    return stock_pool.get(category, stock_pool['moderate'])


def _calculate_expected_return(risk: RiskTolerance) -> float:
    """Calculate portfolio expected return based on risk profile"""
    risk_return_map = {
        RiskTolerance.LOW: 7.5,
        RiskTolerance.MEDIUM: 10.8,
        RiskTolerance.HIGH: 18.2,
    }
    return risk_return_map.get(risk, 10.0)


def _calculate_risk_score(risk: RiskTolerance) -> float:
    """Calculate portfolio risk score (0-100)"""
    risk_score_map = {
        RiskTolerance.LOW: 22.0,
        RiskTolerance.MEDIUM: 48.0,
        RiskTolerance.HIGH: 75.0,
    }
    return risk_score_map.get(risk, 50.0)


def _calculate_projected_growth(initial_amount: float, annual_return: float, years: int) -> list[ProjectedGrowthDto]:
    """
    Calculate year-by-year projected portfolio growth using compound interest.
    
    Args:
        initial_amount: Starting investment amount
        annual_return: Expected annual return as percentage (e.g., 10.8 for 10.8%)
        years: Investment horizon in years
        
    Returns:
        List of projected values for each year
    """
    
    projected_growth = []
    
    # Year 0 is the starting amount
    projected_growth.append(ProjectedGrowthDto(year=0, projectedValue=round(initial_amount, 2)))
    
    # Calculate compound growth for each year
    for year in range(1, years + 1):
        # Compound interest formula: A = P(1 + r)^t
        projected_value = initial_amount * ((1 + annual_return / 100) ** year)
        projected_growth.append(ProjectedGrowthDto(year=year, projectedValue=round(projected_value, 2)))
    
    return projected_growth