import os
import json
import traceback
from dotenv import load_dotenv
from firebase_functions import https_fn, options
from pydantic import ValidationError

from src.models.dto import GeneratePortfolioRequestDto, PortfolioRecommendationDto
from src.utils.security import validate_request_headers, get_cors_headers
from src.agent.hardcoded_portfolio import generate_hardcoded_portfolio


# Load environment variables from .env file for local development
load_dotenv()


# Configure function options
@https_fn.on_request(
    timeout_sec=540,
    memory=options.MemoryOption.GB_1,
    region="us-central1"
)
def generatePortfolio(request: https_fn.Request) -> https_fn.Response:
    """
    HTTP Cloud Function to generate investment portfolio recommendations.
    
    This function:
    1. Validates security headers
    2. Parses and validates request body
    3. Generates portfolio recommendation
    4. Returns structured response
    
    Args:
        request: HTTP request from BFF
        
    Returns:
        JSON response with portfolio or error
    """
    
    # Get CORS headers
    cors_headers = get_cors_headers(request)
    
    # Handle preflight OPTIONS request
    if request.method == 'OPTIONS':
        return https_fn.Response(
            status=204,
            headers=cors_headers
        )
    
    # Only allow POST requests
    if request.method != 'POST':
        return https_fn.Response(
            json.dumps({
                "error": "Method not allowed. Use POST."
            }),
            status=405,
            headers={**cors_headers, 'Content-Type': 'application/json'}
        )
    
    # Validate security headers
    is_valid, error_message = validate_request_headers(request)
    if not is_valid:
        return https_fn.Response(
            json.dumps({
                "error": error_message
            }),
            status=403,
            headers={**cors_headers, 'Content-Type': 'application/json'}
        )
    
    try:
        # Parse request body
        request_json = request.get_json(silent=True)
        
        if not request_json:
            return https_fn.Response(
                json.dumps({
                    "error": "Invalid JSON in request body"
                }),
                status=400,
                headers={**cors_headers, 'Content-Type': 'application/json'}
            )
        
        # Validate request data against DTO schema
        try:
            request_data = GeneratePortfolioRequestDto(**request_json)
        except ValidationError as e:
            return https_fn.Response(
                json.dumps({
                    "error": f"Invalid request data: {str(e)}"
                }),
                status=400,
                headers={**cors_headers, 'Content-Type': 'application/json'}
            )
        
        # Generate portfolio using hardcoded data for Phase 1
        portfolio = generate_hardcoded_portfolio(request_data)
        
        # Convert response to dict for JSON serialization
        response_dict = portfolio.model_dump()
        
        # Return successful response
        return https_fn.Response(
            json.dumps(response_dict),
            status=200,
            headers={**cors_headers, 'Content-Type': 'application/json'}
        )
        
    except Exception as e:
        # Log the full error for debugging
        error_traceback = traceback.format_exc()
        print(f"Error generating portfolio: {error_traceback}")
        
        # Return error response
        return https_fn.Response(
            json.dumps({
                "error": f"Internal server error: {str(e)}",
                "recommendations": [],
                "totalExpectedReturn": 0,
                "riskScore": 0,
                "projectedGrowth": [],
                "generatedAt": "",
            }),
            status=500,
            headers={**cors_headers, 'Content-Type': 'application/json'}
        )