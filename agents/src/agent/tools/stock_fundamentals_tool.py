"""
Stock Fundamentals Tool - Reads from Firestore cache.
Data populated by batch_load_fundamentals.py from Twelve Data API.
"""

from typing import Dict, Any, List
from firebase_admin import firestore
from .base import BaseTool, ToolError
import logging

logger = logging.getLogger(__name__)


class StockFundamentalsTool(BaseTool):
    """
    Retrieves detailed fundamental metrics for specific stocks.
    """
    
    def __init__(self):
        """Initialize with Firestore client."""
        try:
            self.db = firestore.client()
            self.collection = self.db.collection('stock_fundamentals')
            logger.info("StockFundamentalsTool initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Firestore: {e}")
            self.db = None
            self.collection = None
    
    @property
    def name(self) -> str:
        return "get_stock_fundamentals"
    
    @property
    def description(self) -> str:
        return """Retrieves detailed fundamental analysis data for specific stocks.

Returns comprehensive metrics including:
- Valuation: P/E ratio (trailing & forward), PEG ratio, Price-to-Book, Price-to-Sales, EV/Revenue, EV/EBITDA
- Profitability: Profit margin, operating margin, gross margin, ROA, ROE
- Growth: Quarterly revenue growth, quarterly earnings growth
- Financial Health: Current ratio, debt-to-equity, total cash, total debt
- Dividends: Forward & trailing dividend yield, payout ratio, ex-dividend date
- Technical: Beta, 52-week high/low, 50-day & 200-day moving averages
- Size: Market cap, enterprise value, shares outstanding

Use this tool for your FINALIST stocks (10-20 candidates) after initial sector filtering.
Do NOT call for all 50-100 stocks - focus on serious candidates only.

Data source: Twelve Data API (refreshed periodically)"""
    
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "symbols": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of stock symbols to retrieve (limit to 10-20 finalists)"
                }
            },
            "required": ["symbols"]
        }
    
    def execute(self, symbols: List[str]) -> Dict[str, Any]:
        """
        Retrieve fundamentals from Firestore.
        
        Args:
            symbols: List of stock ticker symbols
            
        Returns:
            Dictionary with fundamentals for each stock
        """
        if not self.collection:
            return ToolError.create(
                code=ToolError.API_UNAVAILABLE,
                message="Firestore not available",
                user_message="Fundamental data temporarily unavailable"
            )
        
        if len(symbols) > 30:
            return ToolError.create(
                code=ToolError.INVALID_PARAMETERS,
                message=f"Too many symbols requested: {len(symbols)}",
                user_message="Please limit to 30 stocks maximum per request"
            )
        
        try:
            fundamentals = {}
            missing_symbols = []
            
            for symbol in symbols:
                # Normalize symbol to uppercase
                symbol_upper = symbol.upper()
                doc_ref = self.collection.document(symbol_upper)
                doc = doc_ref.get()
                
                if doc.exists:
                    fundamentals[symbol_upper] = doc.to_dict()
                else:
                    missing_symbols.append(symbol_upper)
                    logger.warning(f"No fundamentals found for: {symbol_upper}")
            
            if not fundamentals:
                return ToolError.create(
                    code=ToolError.DATA_PARSE_ERROR,
                    message="No fundamental data found for requested symbols",
                    user_message="Fundamental data not available for these stocks"
                )
            
            result = {
                "success": True,
                "data": {
                    "symbols_requested": len(symbols),
                    "symbols_found": len(fundamentals),
                    "fundamentals": fundamentals
                }
            }
            
            if missing_symbols:
                result["warning"] = {
                    "message": f"Some symbols not found: {', '.join(missing_symbols)}",
                    "missing_count": len(missing_symbols)
                }
            
            return result
            
        except Exception as e:
            logger.error(f"Error querying fundamentals: {e}")
            return ToolError.create(
                code=ToolError.UNKNOWN_ERROR,
                message=str(e),
                user_message="Failed to retrieve fundamental data"
            )