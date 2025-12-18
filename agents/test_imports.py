"""Quick import verification."""
import sys
print("Testing imports...")

try:
    from config import config
    print(f"✓ Config loaded")
    print(f"  - Has alpha_vantage_api_key: {hasattr(config, 'alpha_vantage_api_key')}")
    print(f"  - Has fred_api_key: {hasattr(config, 'fred_api_key')}")
    
    from src.agent.tools import BaseTool, ToolError, MacroEconomicDataTool, ToolRegistry
    print(f"✓ Tools imported")
    
    from src.agent.prompts import get_system_prompt
    print(f"✓ Prompts imported")
    
    from src.agent.anthropic_service import AnthropicService
    print(f"✓ AnthropicService imported")
    
    print("\n✅ All imports successful!")
    
except Exception as e:
    print(f"\n❌ Import failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)