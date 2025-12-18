"""
Base class for all agent tools.
Defines interface and error handling patterns.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class ToolError:
    """Structured error for tool failures."""
    
    # Error codes
    API_RATE_LIMIT = "API_RATE_LIMIT"
    API_UNAVAILABLE = "API_UNAVAILABLE"
    API_TIMEOUT = "API_TIMEOUT"
    INVALID_PARAMETERS = "INVALID_PARAMETERS"
    DATA_PARSE_ERROR = "DATA_PARSE_ERROR"
    CACHE_STALE = "CACHE_STALE"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"
    
    # Severity levels
    WARNING = "warning"
    ERROR = "error"
    
    @staticmethod
    def create(
        code: str,
        message: str,
        severity: str = ERROR,
        user_message: str = None,
        technical_details: str = None
    ) -> Dict[str, Any]:
        """
        Create structured error dictionary.
        
        Returns dict that can be parsed by UI layer for display.
        """
        return {
            "error": message,
            "error_code": code,
            "severity": severity,
            "user_message": user_message or message,
            "technical_details": technical_details,
            "success": False
        }


class BaseTool(ABC):
    """Abstract base class for all agent tools."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique tool name."""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Tool description for Claude."""
        pass
    
    @property
    @abstractmethod
    def input_schema(self) -> Dict[str, Any]:
        """JSON schema for input parameters."""
        pass
    
    @abstractmethod
    def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Execute tool logic.
        
        Should return dict with:
        - success: bool
        - data: result data if success=True
        - error info if success=False
        """
        pass
    
    def to_anthropic_format(self) -> Dict[str, Any]:
        """Convert to Anthropic tools API format."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema
        }
    
    def safe_execute(self, **kwargs) -> Dict[str, Any]:
        """
        Execute with comprehensive error handling.
        Never raises exceptions - always returns dict.
        """
        try:
            logger.info(f"[{self.name}] Executing with params: {kwargs}")
            result = self.execute(**kwargs)
            
            if result.get('success', True):
                logger.info(f"[{self.name}] Success")
            else:
                logger.warning(f"[{self.name}] Returned error: {result.get('error_code')}")
            
            return result
            
        except Exception as e:
            logger.error(f"[{self.name}] Unexpected error: {e}")
            return ToolError.create(
                code=ToolError.UNKNOWN_ERROR,
                message=str(e),
                user_message="An unexpected error occurred while retrieving data",
                technical_details=f"{type(e).__name__}: {e}"
            )