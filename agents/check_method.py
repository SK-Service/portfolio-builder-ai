# Create check_method.py
from src.agent.tools.macro_data_tool import MacroEconomicDataTool

tool = MacroEconomicDataTool("dummy_key", "dummy_key")
print("Methods available:")
for attr in dir(tool):
    if attr.startswith('_fetch'):
        print(f"  - {attr}")

# Should print:
#   - _fetch_usa_data
#   - _fetch_canada_data
#   - _fetch_eu_data
#   - _fetch_india_data