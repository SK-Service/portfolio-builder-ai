"""
Tools package for Portfolio Builder Agent.

Provides tools for:
- Macro economic data (FRED API)
- Stock universe lookup (Firestore)
- Stock fundamentals (Firestore, populated from Twelve Data)
- Market sentiment (Firestore + Twelve Data real-time)
"""

from .base import BaseTool, ToolError
from .macro_data_tool import MacroEconomicDataTool
from .stock_universe_tool import StockUniverseTool
from .stock_fundamentals_tool import StockFundamentalsTool
from .market_sentiment_tool import MarketSentimentTool
from .tool_registry import ToolRegistry
from .cache import FirestoreCache

__all__ = [
    'BaseTool',
    'ToolError',
    'MacroEconomicDataTool',
    'StockUniverseTool',
    'StockFundamentalsTool',
    'MarketSentimentTool',
    'ToolRegistry',
    'FirestoreCache'
]