import os
from typing import Tuple, Optional
from firebase_functions import https_fn


def validate_request_headers(request: https_fn.Request) -> Tuple[bool, Optional[str]]:
    """
    Validate that the request has proper authentication headers.
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    
    # Get expected API key from environment
    expected_key = os.getenv('AGENT_API_KEY')
    
    if not expected_key:
        # Configuration error - this should never happen in production
        return False, "Server configuration error: API key not set"
    
    # Check for required headers
    api_key = request.headers.get('X-Portfolio-App-Key')
    requested_with = request.headers.get('X-Requested-With')
    
    # Validate X-Portfolio-App-Key
    if not api_key:
        return False, "Missing authentication header: X-Portfolio-App-Key"
    
    if api_key != expected_key:
        return False, "Invalid authentication credentials"
    
    # Validate X-Requested-With
    if not requested_with:
        return False, "Missing required header: X-Requested-With"
    
    if requested_with != "XMLHttpRequest":
        return False, "Invalid X-Requested-With header value"
    
    # All validations passed
    return True, None


def get_cors_headers(request: https_fn.Request) -> dict:
    """
    Generate CORS headers based on request origin.
    
    Returns:
        Dictionary of CORS headers
    """
    
    # Get allowed origins from environment
    allowed_origins_str = os.getenv('ALLOWED_ORIGINS', 'http://localhost:4200')
    allowed_origins = [origin.strip() for origin in allowed_origins_str.split(',')]
    
    # Get request origin
    request_origin = request.headers.get('Origin', '')
    
    # Determine if origin is allowed
    if request_origin in allowed_origins:
        allowed_origin = request_origin
    else:
        # Default to first allowed origin if request origin not in list
        allowed_origin = allowed_origins[0] if allowed_origins else '*'
    
    return {
        'Access-Control-Allow-Origin': allowed_origin,
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, X-Portfolio-App-Key, X-Requested-With',
        'Access-Control-Max-Age': '3600',
    }