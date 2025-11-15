from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from enum import Enum


class RiskTolerance(str, Enum):
    """User's risk tolerance levels"""
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


class Country(str, Enum):
    """Supported countries for investment"""
    USA = "USA"
    EU = "EU"
    CANADA = "Canada"
    INDIA = "India"


class Currency(str, Enum):
    """Supported currencies"""
    USD = "USD"
    EUR = "EUR"
    CAD = "CAD"
    INR = "INR"


class GeneratePortfolioRequestDto(BaseModel):
    """Input DTO from BFF matching TypeScript interface"""
    riskTolerance: RiskTolerance
    investmentHorizonYears: int = Field(ge=1, le=50)
    country: Country
    investmentAmount: float = Field(ge=100)
    currency: Optional[Currency] = None

    @field_validator('investmentAmount')
    def validate_investment_amount(cls, v):
        """Ensure investment amount is reasonable"""
        if v < 100:
            raise ValueError('Investment amount must be at least $100')
        return v


class StockRecommendationDto(BaseModel):
    """Individual stock recommendation"""
    symbol: str
    companyName: str
    allocation: float  # Percentage as decimal (e.g., 29.7 for 29.7%)
    expectedReturn: float  # Expected annual return percentage
    sector: str
    country: str


class ProjectedGrowthDto(BaseModel):
    """Projected portfolio value for a given year"""
    year: int
    projectedValue: float


class PortfolioRecommendationDto(BaseModel):
    """Complete portfolio recommendation response"""
    recommendations: List[StockRecommendationDto]
    totalExpectedReturn: float
    riskScore: float  # 0-100 scale
    projectedGrowth: List[ProjectedGrowthDto]
    generatedAt: str  # ISO timestamp
    error: Optional[str] = None