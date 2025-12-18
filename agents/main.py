"""
Firebase Cloud Function: Portfolio Generator
Phase 3: AI-powered portfolio generation using Anthropic Claude API
"""

print("=" * 60)
print("LOADING main.py module...")
print("=" * 60)

from firebase_functions import https_fn, options
from firebase_admin import initialize_app
import json
from typing import Dict, Any, Optional
import logging

print("Standard imports OK")

from config import config
print(f"Config loaded - API key present: {bool(config.agent_api_key)}")

from src.utils.security import verify_security_key
print("Security utils loaded")

from src.agent.anthropic_service import AnthropicService
print("Anthropic service loaded")

from src.agent.hardcoded_portfolio import generate_hardcoded_portfolio
print("Hardcoded portfolio loaded")

# Initialize Firebase Admin SDK (required at module level)
initialize_app()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Lazy-loaded service
_anthropic_service: Optional[AnthropicService] = None

# Helper function for creating responses
def create_response(data: Any, status: int = 200) -> https_fn.Response:
    """Helper to create JSON responses with proper headers"""
    return https_fn.Response(
        json.dumps(data),
        status=status,
        headers={"Content-Type": "application/json"}
    )

print("About to define generatePortfolio function...")


def get_anthropic_service() -> AnthropicService:
    """Get or create Anthropic service instance (lazy initialization)."""
    global _anthropic_service
    if _anthropic_service is None:
        logger.info("Initializing Anthropic service...")
        _anthropic_service = AnthropicService(
            alpha_vantage_key=config.alpha_vantage_api_key,
            fred_key=config.fred_api_key
        )
    return _anthropic_service


@https_fn.on_request(
    cors=options.CorsOptions(
        cors_origins="*",
        cors_methods=["POST", "OPTIONS"]
    )
)
def generatePortfolio(request: https_fn.Request) -> https_fn.Response:
    """
    HTTP Cloud Function to generate AI-powered portfolio recommendations.
    
    Phase 2: Uses Anthropic Claude API with fallback to hardcoded portfolios.
    """
    
    #DEBUG: Print received headers
    print(f"DEBUG: Received headers: {dict(request.headers)}")
    print(f"DEBUG: Looking for x-api-key: {request.headers.get('x-api-key')}")
    print(f"DEBUG: Config API key: {config.agent_api_key}")

    # Security check
    if not verify_security_key(request, config.agent_api_key):
        logger.warning("Unauthorized request - invalid API key")
        return create_response({'error': 'Unauthorized'}, status=403)
    
    # Only accept POST
    if request.method != 'POST':
        return create_response({'error': 'Method not allowed'}, status=405)
    
    # Parse and validate request
    try:
        request_json = request.get_json(silent=True)
        if not request_json:
            return create_response({'error': 'Invalid JSON'}, status=400)
        
        risk_tolerance = request_json.get('riskTolerance')
        investment_horizon = request_json.get('investmentHorizonYears')
        country = request_json.get('country')
        investment_amount = request_json.get('investmentAmount')
        currency = request_json.get('currency', 'USD')
        
        # Validate required fields
        if not all([risk_tolerance, investment_horizon, country, investment_amount]):
            return create_response({'error': 'Missing required fields'}, status=400)
            
    except Exception as e:
        logger.error(f"Error parsing request: {e}")
        return create_response({'error': f'Invalid request: {str(e)}'}, status=400)
    
    # Generate portfolio using Claude API
    try:
        logger.info(f"Generating AI portfolio: {risk_tolerance} risk, {investment_horizon}y, {country}, {currency}{investment_amount}")
        
        # Get service (lazy init)
        anthropic_service = get_anthropic_service()
        
        portfolio = anthropic_service.generate_portfolio(
            risk_tolerance=risk_tolerance,
            investment_horizon_years=investment_horizon,
            country=country,
            investment_amount=investment_amount,
            currency=currency
        )
        
        logger.info(f"Successfully generated AI portfolio with {len(portfolio['recommendations'])} stocks")
        
    except Exception as e:
        logger.error(f"Claude API failed: {type(e).__name__}: {e}")
        logger.info("Falling back to hardcoded portfolio")
        
        # Fallback to hardcoded portfolio if Claude fails
        try:
            portfolio = generate_hardcoded_portfolio(
                risk_tolerance=risk_tolerance,
                investment_horizon_years=investment_horizon,
                country=country,
                investment_amount=investment_amount
            )
            portfolio['error'] = f'AI generation unavailable, using fallback portfolio'
            logger.info(f"Fallback portfolio generated with {len(portfolio['recommendations'])} stocks")
            
        except Exception as fallback_error:
            logger.error(f"Fallback also failed: {fallback_error}")
            return create_response({
                'error': 'Portfolio generation failed',
                'details': str(e)
            }, status=500)
    
    # Return with CORS headers
    return create_response(portfolio)