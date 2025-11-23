"""
Anthropic Claude API service with error handling.
"""

from anthropic import Anthropic, APIError, APIConnectionError, RateLimitError
from typing import Dict, Any
import json
import logging
from config import config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AnthropicService:
    """Service for interacting with Anthropic Claude API."""
    
    def __init__(self):
        """Initialize Anthropic client with retry configuration."""
        self.client = Anthropic(
            api_key=config.anthropic_api_key,
            max_retries=config.max_retries,
            timeout=30.0
        )
        self.model = config.anthropic_model
        self.max_tokens = config.anthropic_max_tokens
        self.temperature = config.anthropic_temperature
    
    def generate_portfolio(
        self,
        risk_tolerance: str,
        investment_horizon_years: int,
        country: str,
        investment_amount: float,
        currency: str
    ) -> Dict[str, Any]:
        """
        Generate portfolio recommendations using Claude API.
        
        Args:
            risk_tolerance: Low, Medium, or High
            investment_horizon_years: Investment time horizon
            country: Country for stock selection
            investment_amount: Amount to invest
            currency: Currency code
            
        Returns:
            Portfolio recommendation dictionary
            
        Raises:
            APIError: If Claude API returns an error
            APIConnectionError: If connection to API fails
            RateLimitError: If rate limit is exceeded
        """
        try:
            logger.info(f"Generating portfolio with Claude for {risk_tolerance} risk, {investment_horizon_years}y horizon")
            
            # Construct prompt
            system_prompt = self._build_system_prompt()
            user_prompt = self._build_user_prompt(
                risk_tolerance,
                investment_horizon_years,
                country,
                investment_amount,
                currency
            )
            
            # Call Claude API (SDK handles retries automatically)
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ]
            )
            
            # Extract and parse response
            portfolio = self._parse_response(response, investment_amount, investment_horizon_years)
            
            logger.info(f"Successfully generated portfolio with {len(portfolio['recommendations'])} stocks")
            return portfolio
            
        except APIConnectionError as e:
            logger.error(f"Connection error calling Claude API: {e}")
            raise
        except RateLimitError as e:
            logger.error(f"Rate limit exceeded: {e}")
            raise
        except APIError as e:
            logger.error(f"Claude API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error generating portfolio: {e}")
            raise
    
    def _build_system_prompt(self) -> str:
        """Build system prompt for Claude."""
        return """You are an expert financial advisor and portfolio manager with deep knowledge of global stock markets, investment strategies, and risk management.

Your role is to:
1. Analyze the client's risk tolerance, investment horizon, and financial goals
2. Recommend a diversified portfolio of stocks tailored to their profile
3. Provide clear rationale for each recommendation
4. Calculate expected returns and risk metrics

Always provide responses in valid JSON format with no additional text."""
    
    def _build_user_prompt(
        self,
        risk_tolerance: str,
        investment_horizon_years: int,
        country: str,
        investment_amount: float,
        currency: str
    ) -> str:
        """Build user prompt with investment parameters."""
        return f"""Generate a personalized stock portfolio recommendation with the following parameters:

**Client Profile:**
- Risk Tolerance: {risk_tolerance}
- Investment Horizon: {investment_horizon_years} years
- Country/Market: {country}
- Investment Amount: {currency} {investment_amount:,.2f}

**Requirements:**
1. Recommend 4-6 stocks appropriate for this risk profile
2. Focus on stocks from or available in the {country} market
3. Provide proper diversification across sectors
4. Calculate allocation percentages (must sum to 100%)
5. Estimate expected annual returns for each stock
6. Calculate overall portfolio expected return
7. Provide a risk score (0-100, where 0 is lowest risk)

**Response Format (strict JSON only):**
{{
  "recommendations": [
    {{
      "symbol": "STOCK_SYMBOL",
      "companyName": "Full Company Name",
      "allocation": 25.0,
      "expectedReturn": 12.5,
      "sector": "Technology",
      "country": "{country}"
    }}
  ],
  "totalExpectedReturn": 10.5,
  "riskScore": 65.0
}}

Provide only the JSON object, no additional text or explanation."""
    
    def _parse_response(
        self,
        response: Any,
        investment_amount: float,
        investment_horizon_years: int
    ) -> Dict[str, Any]:
        """
        Parse Claude's response and add projected growth.
        
        Args:
            response: Claude API response
            investment_amount: Initial investment
            investment_horizon_years: Years to project
            
        Returns:
            Complete portfolio dictionary
        """
        # Extract text content from Claude response
        content = response.content[0].text

        # Strip markdown code fences if present
        content = content.strip()
        if content.startswith('```'):
            # Remove opening fence
            content = content.split('```', 1)[1]
            # Remove 'json' language identifier if present
            if content.startswith('json'):
                content = content[4:]
            # Remove closing fence
            if '```' in content:
                content = content.rsplit('```', 1)[0]
            content = content.strip()
        
        # Parse JSON from response
        try:
            portfolio_data = json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Claude response as JSON: {e}")
            logger.error(f"Response content: {content}")
            raise ValueError(f"Invalid JSON response from Claude: {e}")
        
        # Validate required fields
        required_fields = ['recommendations', 'totalExpectedReturn', 'riskScore']
        missing_fields = [field for field in required_fields if field not in portfolio_data]
        if missing_fields:
            raise ValueError(f"Missing required fields in Claude response: {missing_fields}")
        
        # Calculate projected growth
        annual_return = portfolio_data['totalExpectedReturn'] / 100
        projected_growth = []
        
        for year in range(investment_horizon_years + 1):
            projected_value = investment_amount * ((1 + annual_return) ** year)
            projected_growth.append({
                'year': year,
                'projectedValue': round(projected_value, 2)
            })
        
        # Add projected growth and timestamp
        portfolio_data['projectedGrowth'] = projected_growth
        portfolio_data['generatedAt'] = self._get_timestamp()
        portfolio_data['error'] = None
        
        return portfolio_data
    
    def _get_timestamp(self) -> str:
        """Get current UTC timestamp in ISO format."""
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat()