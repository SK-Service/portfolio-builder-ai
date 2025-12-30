"""
Tool registry for managing available agent tools.

Registers all tools that the portfolio agent can use:
- MacroEconomicDataTool: Fetches macro data from FRED
- StockUniverseTool: Gets available stocks by country/sector
- StockFundamentalsTool: Gets stock fundamental metrics
- MarketSentimentTool: Gets analyst ratings, recommendations, price targets
"""

from typing import Dict, List
from .base import BaseTool, ToolError
from .macro_data_tool import MacroEconomicDataTool
from .stock_universe_tool import StockUniverseTool
from .stock_fundamentals_tool import StockFundamentalsTool
from .market_sentiment_tool import MarketSentimentTool
import logging

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Registry for managing available agent tools."""
    
    def __init__(self, alpha_vantage_key: str = None, fred_key: str = None):
        """
        Initialize registry.
        
        Args:
            fred_key: FRED API key for macro data tool
        """
        self._tools: Dict[str, BaseTool] = {}
        self._register_tools(alpha_vantage_key,fred_key)
    
    def _register_tools(self, alpha_vantage_key: str = None, fred_key: str = None):
        """Register all available tools."""
        
        # Macro economic data tool
        macro_tool = MacroEconomicDataTool()
        self.register(macro_tool)
  
        # Stock universe tool (reads from Firestore)
        stock_universe_tool = StockUniverseTool()
        self.register(stock_universe_tool)
        
        # Stock fundamentals tool (reads from Firestore)
        fundamentals_tool = StockFundamentalsTool()
        self.register(fundamentals_tool)
        
        # Market sentiment tool (reads from Firestore with real-time API fallback)
        # sentiment_tool = MarketSentimentTool()
        # self.register(sentiment_tool)
        
        logger.info(f"Registered {len(self._tools)} tools: {list(self._tools.keys())}")
    
    def register(self, tool: BaseTool):
        """Register a tool."""
        self._tools[tool.name] = tool
        logger.info(f"Registered tool: {tool.name}")
    
    def get_tool(self, name: str) -> BaseTool:
        """Get tool by name."""
        if name not in self._tools:
            raise ValueError(f"Tool '{name}' not found. Available: {list(self._tools.keys())}")
        return self._tools[name]
    
    def get_all_tools(self) -> List[BaseTool]:
        """Get all registered tools."""
        return list(self._tools.values())
    
    def get_anthropic_tools(self) -> List[Dict]:
        """Get tools in Anthropic API format."""
        return [tool.to_anthropic_format() for tool in self._tools.values()]
    
    def execute_tool(self, tool_name: str, **kwargs) -> Dict:
        """
        Execute tool with error handling.
        
        Args:
            tool_name: Name of tool to execute
            **kwargs: Arguments to pass to tool
            
        Returns:
            Tool result dictionary
        """
        try:
            tool = self.get_tool(tool_name)
            return tool.safe_execute(**kwargs)
        except ValueError as e:
            logger.error(f"Tool execution error: {e}")
            return ToolError.create(
                code=ToolError.UNKNOWN_ERROR,
                message=str(e),
                user_message="Requested tool not available"
            )
    
    def list_tools(self) -> List[str]:
        """Get list of registered tool names."""
        return list(self._tools.keys())
    
    def get_tool_descriptions(self) -> Dict[str, str]:
        """Get dictionary of tool names to descriptions."""
        return {name: tool.description for name, tool in self._tools.items()}