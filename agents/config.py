"""
Configuration management for Portfolio Builder Agent.
Uses Pydantic for validation and type safety.
"""

from pydantic import Field, ValidationError
from pydantic_settings import BaseSettings
from typing import Optional
import sys


class AgentConfig(BaseSettings):
    """Agent configuration with validation."""
    
    # Security
    agent_api_key: str = Field(..., min_length=32, description="Agent API authentication key")
    
    # Anthropic API
    anthropic_api_key: str = Field(..., min_length=20, description="Anthropic API key")
    anthropic_model: str = Field(default="claude-sonnet-4-20250514", description="Claude model to use")
    anthropic_max_tokens: int = Field(default=4096, ge=1, le=8192, description="Max tokens for Claude response")
    anthropic_temperature: float = Field(default=0.7, ge=0.0, le=1.0, description="Temperature for Claude creativity")

    # External API Keys
    alpha_vantage_api_key: str = Field(..., min_length=10, description="Alpha Vantage API key")
    fred_api_key: str = Field(..., min_length=10, description="FRED API key")
    
    # Retry Configuration
    max_retries: int = Field(default=3, ge=1, le=5, description="Max retry attempts for API calls")
    retry_min_wait: int = Field(default=1, ge=1, description="Min wait seconds between retries")
    retry_max_wait: int = Field(default=10, ge=1, description="Max wait seconds between retries")
    
    # Environment
    environment: str = Field(default="development", description="Runtime environment")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"  # Ignore extra env vars


def load_config() -> AgentConfig:
    """
    Load and validate configuration.
    Exits with error message if validation fails.
    """
    try:
        config = AgentConfig()
        return config
    except ValidationError as e:
        print(f"Configuration Error: {e}", file=sys.stderr)
        sys.exit(1)


# Global config instance
config = load_config()