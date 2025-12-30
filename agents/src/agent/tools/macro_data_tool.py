"""
Macro Economic Data Tool - Reads from Firestore cache.
Data populated by batch_load_macro.py from FRED and World Bank APIs.
"""

from typing import Dict, Any
from firebase_admin import firestore
from .base import BaseTool, ToolError
import logging

logger = logging.getLogger(__name__)


class MacroEconomicDataTool(BaseTool):
    """
    Retrieves macroeconomic indicators from Firestore cache.
    Data is pre-fetched by batch_load_macro.py from FRED and World Bank.
    """
    
    def __init__(self):
        """Initialize with Firestore client."""
        try:
            self.db = firestore.client()
            self.collection = self.db.collection('macro_economic_data')
            logger.info("MacroEconomicDataTool initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Firestore: {e}")
            self.db = None
            self.collection = None
    
    @property
    def name(self) -> str:
        return "get_macro_economic_data"
    
    @property
    def description(self) -> str:
        return """Retrieves current macroeconomic indicators for the specified country.

Returns economic data including:
- GDP growth rate (annual %)
- Inflation rate (annual %)  
- Unemployment rate (%)
- Interest rates (where available)
- Economic context summary

Supported countries:
- USA: GDP, Inflation, Unemployment, Interest Rate
- Canada: GDP, Inflation, Unemployment, Interest Rate
- EU (Eurozone): GDP, Inflation, Unemployment
- India: GDP Growth, Inflation, Unemployment

Data sources: FRED (Federal Reserve Economic Data), World Bank
Data is refreshed periodically via batch jobs.

Use this tool FIRST to understand the current economic environment before making portfolio decisions."""
    
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "country": {
                    "type": "string",
                    "enum": ["USA", "Canada", "EU", "India"],
                    "description": "Target country for economic data"
                }
            },
            "required": ["country"]
        }
    
    def execute(self, country: str) -> Dict[str, Any]:
        """
        Retrieve macro data from Firestore.
        
        Args:
            country: One of USA, Canada, EU, India
            
        Returns:
            Dictionary with economic indicators and context
        """
        if not self.collection:
            return ToolError.create(
                code=ToolError.API_UNAVAILABLE,
                message="Firestore not available",
                user_message="Economic data temporarily unavailable"
            )
        
        # Validate country
        valid_countries = ["USA", "Canada", "EU", "India"]
        if country not in valid_countries:
            return ToolError.create(
                code=ToolError.INVALID_PARAMETERS,
                message=f"Unsupported country: {country}",
                user_message=f"Economic data not available for {country}. Supported: {', '.join(valid_countries)}"
            )
        
        try:
            # Document IDs are lowercase (usa, canada, eu, india)
            doc_id = country.lower()
            doc_ref = self.collection.document(doc_id)
            doc = doc_ref.get()
            
            if not doc.exists:
                logger.warning(f"No macro data found for: {country}")
                return ToolError.create(
                    code=ToolError.DATA_PARSE_ERROR,
                    message=f"No macro data found for {country}",
                    user_message=f"Economic data not available for {country}"
                )
            
            data = doc.to_dict()
            
            # Remove upload metadata from response (not needed by agent)
            data.pop('uploaded_at', None)
            
            logger.info(f"Retrieved macro data for {country}: {len(data.get('indicators', {}))} indicators")
            
            return {
                "success": True,
                "data": data,
                "from_cache": True
            }
            
        except Exception as e:
            logger.error(f"Error querying macro data for {country}: {e}")
            return ToolError.create(
                code=ToolError.UNKNOWN_ERROR,
                message=str(e),
                user_message="Failed to retrieve economic data"
            )