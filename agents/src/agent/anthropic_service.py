"""
Anthropic Claude API service with tool calling support.
Phase 3: Implements agent loop with function calling and real APIs.
"""

from anthropic import Anthropic, APIError, APIConnectionError, RateLimitError
from typing import Dict, Any, List
import json
import logging
from config import config
from .tools.tool_registry import ToolRegistry
from .prompts.system_prompt import get_system_prompt

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AnthropicService:
    """Service for interacting with Anthropic Claude API with tool support."""
    
    def __init__(self, alpha_vantage_key: str, fred_key: str):
        """
        Initialize Anthropic client with tool support.
        
        Args:
            alpha_vantage_key: Alpha Vantage API key for macro data
            fred_key: FRED API key for Canada/EU macro data
        """
        self.client = Anthropic(
            api_key=config.anthropic_api_key,
            max_retries=config.max_retries,
            timeout=30.0
        )
        self.model = config.anthropic_model
        self.max_tokens = config.anthropic_max_tokens
        self.temperature = config.anthropic_temperature
        
        # Initialize tool registry with API keys
        self.tool_registry = ToolRegistry(alpha_vantage_key, fred_key)
        logger.info(f"Initialized AnthropicService with {len(self.tool_registry.get_all_tools())} tools")
    
    def generate_portfolio(
        self,
        risk_tolerance: str,
        investment_horizon_years: int,
        country: str,
        investment_amount: float,
        currency: str
    ) -> Dict[str, Any]:
        """
        Generate portfolio recommendations using Claude API with tools.
        
        Args:
            risk_tolerance: Low, Medium, or High
            investment_horizon_years: Investment time horizon
            country: Country for stock selection (USA, Canada, EU, India)
            investment_amount: Amount to invest
            currency: Currency code
            
        Returns:
            Portfolio recommendation dictionary matching PortfolioRecommendationDto
            
        Raises:
            APIError: If Claude API returns an error
            APIConnectionError: If connection to API fails
            RateLimitError: If rate limit is exceeded
        """
        try:
            logger.info(f"Generating portfolio: {risk_tolerance} risk, {investment_horizon_years}y, {country}, {currency}{investment_amount}")
            
            # Build system prompt and user message
            system_prompt = get_system_prompt()
            user_prompt = self._build_user_prompt(
                risk_tolerance,
                investment_horizon_years,
                country,
                investment_amount,
                currency
            )
            
            # Initialize conversation
            messages = [{"role": "user", "content": user_prompt}]
            
            # Execute agent loop with tools
            portfolio = self._agent_loop(
                messages=messages,
                system_prompt=system_prompt,
                investment_amount=investment_amount,
                investment_horizon_years=investment_horizon_years
            )
            
            logger.info(f"Successfully generated portfolio with {len(portfolio['recommendations'])} stocks")
            return portfolio
            
        except APIConnectionError as e:
            logger.error(f"Connection error calling Claude API: {e}")
            raise
        except RateLimitError as e:
            logger.error(f"Rate limit exceeded: {e}")
            raise
        except APIError as e:
            logger.error(f"Claude API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error generating portfolio: {e}")
            raise
    
    def _agent_loop(
        self,
        messages: List[Dict],
        system_prompt: str,
        investment_amount: float,
        investment_horizon_years: int,
        max_iterations: int = 5
    ) -> Dict[str, Any]:
        """
        Execute the agent loop: send message → check tools → execute → repeat.
        
        This is the core agentic pattern:
        1. Send messages to Claude with available tools
        2. Claude responds with either:
           - Final answer (stop_reason: "end_turn")
           - Tool use request (stop_reason: "tool_use")
        3. If tool use, execute tools and add results to conversation
        4. Repeat until Claude provides final answer or max iterations reached
        
        Args:
            messages: Conversation messages (list of dicts)
            system_prompt: System instructions for Claude
            investment_amount: Initial investment amount
            investment_horizon_years: Investment time horizon
            max_iterations: Maximum loop iterations (prevents infinite loops)
            
        Returns:
            Final portfolio dictionary
            
        Raises:
            RuntimeError: If max iterations exceeded without completion
        """
        iteration = 0
        
        while iteration < max_iterations:
            iteration += 1
            logger.info(f"Agent loop iteration {iteration}/{max_iterations}")
            
            # Call Claude API with tools
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system=system_prompt,
                messages=messages,
                tools=self.tool_registry.get_anthropic_tools()
            )
            
            logger.info(f"Claude response - Stop reason: {response.stop_reason}, Content blocks: {len(response.content)}")
            
            # Check stop reason
            if response.stop_reason == "end_turn":
                # Claude finished without requesting tools - extract final portfolio
                logger.info("Claude finished with final answer")
                return self._extract_final_portfolio(response, investment_amount, investment_horizon_years)
            
            elif response.stop_reason == "tool_use":
                # Claude wants to use tools
                logger.info("Claude requested tool usage")
                
                # Add Claude's response (including tool_use blocks) to conversation
                messages.append({
                    "role": "assistant",
                    "content": response.content
                })
                
                # Execute all requested tools
                tool_results = self._execute_tool_requests(response.content)
                
                # Add tool results to conversation
                messages.append({
                    "role": "user",
                    "content": tool_results
                })
                
                # Continue loop - Claude will process tool results and decide next action
                continue
            
            else:
                # Unexpected stop reason - try to extract answer anyway
                logger.warning(f"Unexpected stop reason: {response.stop_reason}")
                return self._extract_final_portfolio(response, investment_amount, investment_horizon_years)
        
        # Max iterations reached without completion
        logger.error(f"Agent loop exceeded maximum iterations ({max_iterations})")
        raise RuntimeError(f"Portfolio generation did not complete within {max_iterations} iterations")
    
    def _execute_tool_requests(self, content_blocks: List) -> List[Dict]:
        """
        Execute all tool use requests from Claude's response.
        
        Claude can request multiple tools in a single response.
        Each tool_use block has: id, name, input
        We execute each tool and return results with matching tool_use_id.
        
        Args:
            content_blocks: List of content blocks from Claude response
            
        Returns:
            List of tool_result blocks to send back to Claude
        """
        tool_results = []
        
        for block in content_blocks:
            if block.type == "tool_use":
                tool_name = block.name
                tool_input = block.input
                tool_use_id = block.id
                
                logger.info(f"Executing tool: {tool_name}")
                logger.debug(f"Tool input: {json.dumps(tool_input, indent=2)}")
                
                # Execute tool (safe_execute handles all errors)
                try:
                    result = self.tool_registry.execute_tool(tool_name, **tool_input)
                    
                    # Check if tool execution had errors
                    if result.get('success', True):
                        logger.info(f"Tool {tool_name} executed successfully")
                    else:
                        logger.warning(f"Tool {tool_name} returned error: {result.get('error_code')}")
                    
                    # Add tool result to conversation
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_use_id,
                        "content": json.dumps(result, indent=2)
                    })
                    
                except Exception as e:
                    # This should rarely happen since safe_execute catches everything
                    logger.error(f"Unexpected error executing tool {tool_name}: {e}")
                    
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_use_id,
                        "content": json.dumps({
                            "error": str(e),
                            "error_code": "UNKNOWN_ERROR",
                            "success": False
                        }),
                        "is_error": True
                    })
        
        logger.info(f"Executed {len(tool_results)} tool(s)")
        return tool_results
    
    def _extract_final_portfolio(
        self,
        response: Any,
        investment_amount: float,
        investment_horizon_years: int
    ) -> Dict[str, Any]:
        """
        Extract and validate portfolio from Claude's final response.
        
        Handles:
        - Extracting text from response content blocks
        - Stripping markdown code fences if present
        - Parsing JSON
        - Validating required fields
        - Adding projected growth calculations
        - Adding metadata (timestamp, error field)
        
        Args:
            response: Claude API response object
            investment_amount: Initial investment amount
            investment_horizon_years: Years to project growth
            
        Returns:
            Complete portfolio dictionary matching PortfolioRecommendationDto schema
            
        Raises:
            ValueError: If response cannot be parsed or is invalid
        """
        # Find text content block in response
        text_content = None
        for block in response.content:
            if block.type == "text":
                text_content = block.text
                break
        
        if not text_content:
            logger.error("No text content in Claude response")
            raise ValueError("Claude response contains no text content")
        
        # Strip markdown code fences if present
        content = text_content.strip()
        if content.startswith('```'):
            # Remove opening fence
            content = content.split('```', 1)[1]
            # Remove 'json' language identifier if present
            if content.startswith('json'):
                content = content[4:]
            # Remove closing fence
            if '```' in content:
                content = content.rsplit('```', 1)[0]
            content = content.strip()
        
        # Parse JSON from response
        try:
            portfolio_data = json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Claude response as JSON: {e}")
            logger.error(f"Response content: {content[:500]}...")
            raise ValueError(f"Invalid JSON response from Claude: {e}")
        
        # Validate required fields
        required_fields = ['recommendations', 'totalExpectedReturn', 'riskScore']
        missing_fields = [field for field in required_fields if field not in portfolio_data]
        if missing_fields:
            logger.error(f"Missing required fields: {missing_fields}")
            raise ValueError(f"Claude response missing required fields: {missing_fields}")
        
        # Validate recommendations structure
        if not isinstance(portfolio_data['recommendations'], list):
            raise ValueError("recommendations must be a list")
        
        if len(portfolio_data['recommendations']) == 0:
            raise ValueError("recommendations list is empty")
        
        # Calculate projected growth
        portfolio_data['projectedGrowth'] = self._calculate_projected_growth(
            investment_amount,
            portfolio_data['totalExpectedReturn'],
            investment_horizon_years
        )
        
        # Add metadata
        portfolio_data['generatedAt'] = self._get_timestamp()
        portfolio_data['error'] = None
        
        # Log portfolio summary
        logger.info(f"Portfolio validated: {len(portfolio_data['recommendations'])} stocks, "
                   f"{portfolio_data['totalExpectedReturn']:.1f}% expected return, "
                   f"risk score {portfolio_data['riskScore']}")
        
        return portfolio_data
    
    def _calculate_projected_growth(
        self,
        initial_amount: float,
        annual_return_pct: float,
        years: int
    ) -> List[Dict]:
        """
        Calculate year-by-year projected portfolio values using compound growth.
        
        Formula: FV = PV * (1 + r)^n
        Where:
        - FV = Future Value
        - PV = Present Value (initial_amount)
        - r = annual return rate (as decimal)
        - n = number of years
        
        Args:
            initial_amount: Starting investment amount
            annual_return_pct: Expected annual return percentage (e.g., 12.5 for 12.5%)
            years: Number of years to project
            
        Returns:
            List of {year, projectedValue} dictionaries
        """
        annual_return = annual_return_pct / 100
        projected_growth = []
        
        for year in range(years + 1):
            projected_value = initial_amount * ((1 + annual_return) ** year)
            projected_growth.append({
                'year': year,
                'projectedValue': round(projected_value, 2)
            })
        
        logger.debug(f"Projected growth calculated: {initial_amount} -> {projected_growth[-1]['projectedValue']} over {years} years")
        return projected_growth
    
    def _build_user_prompt(
        self,
        risk_tolerance: str,
        investment_horizon_years: int,
        country: str,
        investment_amount: float,
        currency: str
    ) -> str:
        """
        Build user prompt with investment parameters.
        
        This prompt tells Claude:
        1. What the client wants
        2. What tools to use
        3. What workflow to follow
        4. What output format to produce
        """
        return f"""Generate a personalized stock portfolio recommendation:

**Client Profile:**
- Risk Tolerance: {risk_tolerance}
- Investment Horizon: {investment_horizon_years} years
- Country/Market: {country}
- Investment Amount: {currency} {investment_amount:,.2f}

**Your Task:**
1. Use the get_macro_economic_data tool to retrieve current economic conditions for {country}
2. Analyze how GDP growth, inflation, unemployment, and interest rates affect sector attractiveness
3. Select 4-6 appropriate stocks based on:
   - Client's {risk_tolerance} risk profile
   - Current macro environment
   - {investment_horizon_years}-year investment horizon
4. Ensure proper diversification across sectors
5. Calculate realistic expected returns
6. Verify allocations sum to exactly 100%
7. Provide final portfolio as JSON

Begin your analysis by calling the macro data tool."""
    
    def _get_timestamp(self) -> str:
        """Get current UTC timestamp in ISO 8601 format."""
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat()