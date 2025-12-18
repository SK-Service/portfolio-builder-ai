"""
Stock Universe Tool - Reads from Firestore cache.
"""

from typing import Dict, Any, List, Optional
from firebase_admin import firestore
from .base import BaseTool, ToolError
import logging

logger = logging.getLogger(__name__)


class StockUniverseTool(BaseTool):
    """
    Retrieves available stocks for a country, optionally filtered by sector.
    """
    
    def __init__(self):
        """Initialize with Firestore client."""
        try:
            self.db = firestore.client()
            self.collection = self.db.collection('stock_universe')
            logger.info("StockUniverseTool initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Firestore: {e}")
            self.db = None
            self.collection = None
    
    @property
    def name(self) -> str:
        return "get_stocks_by_country"
    
    @property
    def description(self) -> str:
        return """Retrieves list of tradeable stocks for a given country.

Returns stocks with basic information: symbol, company name, market cap tier.
Can be filtered by specific sectors.

Use this tool AFTER analyzing macro data to get available stocks in sectors you've identified as attractive.

Countries supported: USA, Canada, EU, India
Sectors available: technology, healthcare, finance, energy, consumer_staples, consumer_discretionary, industrials, utilities, real_estate, materials"""
    
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "country": {
                    "type": "string",
                    "enum": ["USA", "Canada", "EU", "India"],
                    "description": "Target country"
                },
                "sectors": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional: Filter by specific sectors. If omitted, returns all sectors."
                }
            },
            "required": ["country"]
        }
    
    def execute(self, country: str, sectors: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Retrieve stocks from Firestore.
        
        Args:
            country: Target country
            sectors: Optional list of sectors to filter
            
        Returns:
            Dictionary with stocks grouped by sector
        """
        if not self.collection:
            return ToolError.create(
                code=ToolError.API_UNAVAILABLE,
                message="Firestore not available",
                user_message="Stock data temporarily unavailable"
            )
        
        try:
            # Query Firestore for this country
            query = self.collection.where('country', '==', country)
            
            if sectors:
                # Filter by sectors
                query = query.where('sector', 'in', sectors)
            
            docs = query.stream()
            
            # Organize results
            stocks_by_sector = {}
            total_stocks = 0
            
            for doc in docs:
                data = doc.to_dict()
                sector = data.get('sector')
                stocks = data.get('stocks', [])
                
                stocks_by_sector[sector] = stocks
                total_stocks += len(stocks)
            
            if not stocks_by_sector:
                return ToolError.create(
                    code=ToolError.INVALID_PARAMETERS,
                    message=f"No stocks found for {country} with specified filters",
                    user_message=f"No stocks available for {country}"
                )
            
            return {
                "success": True,
                "data": {
                    "country": country,
                    "sectors_returned": list(stocks_by_sector.keys()),
                    "total_stocks": total_stocks,
                    "stocks_by_sector": stocks_by_sector
                }
            }
            
        except Exception as e:
            logger.error(f"Error querying stock universe: {e}")
            return ToolError.create(
                code=ToolError.UNKNOWN_ERROR,
                message=str(e),
                user_message="Failed to retrieve stock data"
            )